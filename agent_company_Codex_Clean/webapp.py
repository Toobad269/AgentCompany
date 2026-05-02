#!/usr/bin/env python3
"""
webapp.py — Web-Dashboard für AgentCompany
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Starten:  python webapp.py
URL:      http://localhost:7842

Bietet vollen Funktionsumfang parallel zum Terminal:
  - CEO-Chat schreiben & lesen
  - Chats anlegen / wechseln / Vault setzen
  - Terminal-Befehle approve / deny
  - Tool- und Access-Modi ändern
  - Status, Costs, Requests, Uploads ansehen
  - Dateien in den aktuellen Chat hochladen

Schreibende Aktionen, die main.py-Runtime betreffen, werden als Eintrag in
`web_actions` abgelegt und vom main.py-Poller asynchron ausgeführt.
"""

from __future__ import annotations

import os, sys, json, sqlite3, glob, shutil, time
from datetime import datetime, timezone

from flask import Flask, jsonify, request, abort, Response

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import settings
try:
    from core.cost import TRACKER as COST_TRACKER  # type: ignore
except Exception:
    COST_TRACKER = None  # type: ignore

app = Flask(__name__, static_folder="web", static_url_path="")
app.config["JSON_SORT_KEYS"] = False
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024 * 1024  # 64 MB Upload-Limit


# ─── Schema-Bootstrap (damit Webapp auch ohne main.py initialisieren kann) ───

_BOOTSTRAP_SCHEMA = """
CREATE TABLE IF NOT EXISTS chat_sessions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    name       TEXT NOT NULL,
    vault_path TEXT
);
CREATE TABLE IF NOT EXISTS user_messages (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    session_id INTEGER,
    direction  TEXT NOT NULL,
    content    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS web_actions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at  TEXT NOT NULL,
    action      TEXT NOT NULL,
    payload     TEXT,
    status      TEXT NOT NULL DEFAULT 'pending',
    result      TEXT,
    finished_at TEXT
);
CREATE TABLE IF NOT EXISTS threads (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at  TEXT NOT NULL,
    session_id  INTEGER,
    author      TEXT NOT NULL,
    topic       TEXT,
    content     TEXT NOT NULL,
    parent_id   INTEGER
);
"""

def _bootstrap_db() -> None:
    """Stellt sicher, dass die für die Webapp wichtigsten Tabellen existieren.
    main.py legt darüber hinaus weitere Tabellen an — diese werden hier nur
    minimal vorbereitet, damit das Dashboard nicht 500 wirft."""
    os.makedirs(settings.DB_DIR, exist_ok=True)
    path = os.path.join(settings.DB_DIR, "managers_shared.db")
    con = sqlite3.connect(path, timeout=5.0)
    try:
        con.executescript(_BOOTSTRAP_SCHEMA)
        con.commit()
    finally:
        con.close()


# ─── DB-Helpers ───────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def _q(path: str, sql: str, params=()):
    if not os.path.exists(path):
        return []
    try:
        con = sqlite3.connect(path, timeout=2.0, check_same_thread=False)
        con.row_factory = sqlite3.Row
        rows = [dict(r) for r in con.execute(sql, params)]
        con.close()
        return rows
    except Exception:
        return []

def _exec(path: str, sql: str, params=()):
    con = sqlite3.connect(path, timeout=5.0, check_same_thread=False)
    try:
        cur = con.execute(sql, params)
        con.commit()
        return cur.lastrowid
    finally:
        con.close()

def _mgr() -> str:
    return os.path.join(settings.DB_DIR, "managers_shared.db")

def _team_path(tid: int) -> str:
    return os.path.join(settings.DB_DIR, f"team_{tid}_chat.db")

def _all_team_paths():
    return sorted(glob.glob(os.path.join(settings.DB_DIR, "team_*_chat.db")))

def _team_id(path: str) -> int:
    return int(os.path.basename(path).split("_")[1])

def _queue_action(action: str, payload: dict | None = None) -> int:
    """Legt eine pending Aktion in `web_actions` ab. main.py poller führt sie aus."""
    try:
        return int(_exec(
            _mgr(),
            "INSERT INTO web_actions (created_at, action, payload, status) VALUES (?, ?, ?, 'pending')",
            (_now(), action, json.dumps(payload or {})),
        ) or 0)
    except sqlite3.OperationalError:
        # Tabelle existiert evtl. noch nicht (main.py wurde nie gestartet)
        abort(503, "main.py ist nicht aktiv (web_actions-Tabelle fehlt)")


def _wait_action(action_id: int, timeout: float = 6.0) -> dict:
    """Wartet kurz auf Abschluss der Aktion und gibt Status/Result zurück."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        rows = _q(_mgr(), "SELECT status, result FROM web_actions WHERE id = ?", (action_id,))
        if rows and rows[0]["status"] != "pending":
            return rows[0]
        time.sleep(0.15)
    return {"status": "pending", "result": "timeout"}


def _current_session_id() -> int | None:
    rows = _q(_mgr(), "SELECT id FROM chat_sessions ORDER BY id DESC LIMIT 1")
    return int(rows[0]["id"]) if rows else None


# ─── READ-API ────────────────────────────────────────────────────────────────

@app.route("/api/overview")
def api_overview():
    m = _mgr()
    return jsonify({
        "sessions":         _q(m, "SELECT * FROM chat_sessions ORDER BY id DESC LIMIT 50"),
        "team_count":       len(_q(m, "SELECT id FROM teams")),
        "pending_commands": (_q(m, "SELECT COUNT(*) n FROM terminal_commands WHERE status='pending'") or [{"n":0}])[0]["n"],
        "pending_software": (_q(m, "SELECT COUNT(*) n FROM software_requests WHERE status='pending'") or [{"n":0}])[0]["n"],
        "pending_access":   (_q(m, "SELECT COUNT(*) n FROM access_requests WHERE status='pending'") or [{"n":0}])[0]["n"],
        "db_exists":        os.path.exists(m),
    })

@app.route("/api/chat")
def api_chat():
    m = _mgr()
    return jsonify({
        "sessions": _q(m, "SELECT * FROM chat_sessions ORDER BY id DESC LIMIT 50"),
        "messages": _q(m, "SELECT * FROM user_messages ORDER BY id DESC LIMIT 600"),
    })

@app.route("/api/feed")
def api_feed():
    m = _mgr()
    events = []

    for r in _q(m, "SELECT id,created_at,direction,content,session_id FROM user_messages ORDER BY id DESC LIMIT 40"):
        events.append({**r, "etype": "chat", "agent": "user" if r["direction"] == "in" else "ceo"})

    for r in _q(m, "SELECT id,created_at,author,topic,content,parent_id FROM threads ORDER BY id DESC LIMIT 40"):
        events.append({**r, "etype": "thread"})

    for r in _q(m, "SELECT id,created_at,author,status,message FROM status_updates ORDER BY id DESC LIMIT 30"):
        events.append({**r, "etype": "status", "content": r.get("message") or r.get("status", "")})

    for r in _q(m, "SELECT id,created_at,author,content FROM reports ORDER BY id DESC LIMIT 15"):
        events.append({**r, "etype": "report"})

    for r in _q(m, "SELECT id,created_at,requester as author,command,status,reason FROM terminal_commands ORDER BY id DESC LIMIT 20"):
        events.append({**r, "etype": "command", "content": r["command"]})

    for r in _q(m, "SELECT id,created_at,user_request as content FROM master_plans ORDER BY id DESC LIMIT 10"):
        events.append({**r, "etype": "plan", "agent": "ceo"})

    for tp in _all_team_paths():
        tid = _team_id(tp)
        for r in _q(tp, "SELECT id,created_at,author,content FROM chat ORDER BY id DESC LIMIT 25"):
            events.append({**r, "etype": "team_chat", "team_id": tid})
        for r in _q(tp, "SELECT id,created_at,worker_id as author,content FROM results ORDER BY id DESC LIMIT 15"):
            events.append({**r, "etype": "result", "team_id": tid})
        for r in _q(tp, "SELECT id,created_at,assigner as author,worker_id,description as content,status FROM tasks ORDER BY id DESC LIMIT 15"):
            events.append({**r, "etype": "task", "team_id": tid})

    events.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    return jsonify(events[:200])

@app.route("/api/org")
def api_org():
    m = _mgr()
    teams = _q(m, "SELECT * FROM teams ORDER BY id")
    st_map = {r["team_id"]: r for r in _q(m, """
        SELECT su.* FROM status_updates su
        WHERE su.id = (SELECT MAX(id) FROM status_updates WHERE team_id = su.team_id)
    """)}
    out = []
    for t in teams:
        tid = t["id"]
        tp = _team_path(tid)
        out.append({
            **t,
            "task_stats":    {r["status"]: r["n"] for r in _q(tp, "SELECT status, COUNT(*) n FROM tasks GROUP BY status")},
            "results_count": len(_q(tp, "SELECT id FROM results LIMIT 9999")),
            "chat_count":    len(_q(tp, "SELECT id FROM chat LIMIT 9999")),
            "latest_status": st_map.get(tid),
        })
    return jsonify(out)

@app.route("/api/team/<int:tid>")
def api_team(tid):
    tp = _team_path(tid)
    m = _mgr()
    briefing = _q(m, "SELECT * FROM briefings WHERE target_team_id=? ORDER BY id DESC LIMIT 1", (tid,))
    return jsonify({
        "tasks":    _q(tp, "SELECT * FROM tasks ORDER BY id DESC"),
        "chat":     _q(tp, "SELECT * FROM chat ORDER BY id ASC LIMIT 200"),
        "results":  _q(tp, """SELECT r.*, t.description as task_desc
                               FROM results r LEFT JOIN tasks t ON t.id=r.task_id
                               ORDER BY r.id DESC LIMIT 100"""),
        "briefing": briefing[0] if briefing else None,
    })

@app.route("/api/commands")
def api_commands():
    return jsonify(_q(_mgr(), "SELECT * FROM terminal_commands ORDER BY id DESC LIMIT 100"))

@app.route("/api/threads")
def api_threads():
    return jsonify(_q(_mgr(), "SELECT * FROM threads ORDER BY id DESC LIMIT 100"))

@app.route("/api/requests")
def api_requests():
    m = _mgr()
    return jsonify({
        "software": _q(m, "SELECT * FROM software_requests WHERE status='pending' ORDER BY id ASC"),
        "access":   _q(m, "SELECT * FROM access_requests WHERE status='pending' ORDER BY id ASC"),
        "terminal": _q(m, "SELECT * FROM terminal_commands WHERE status='pending' ORDER BY id ASC"),
    })

@app.route("/api/system")
def api_system():
    """Status, Provider, Modelle, Access, Tools, Costs."""
    snap = COST_TRACKER.snapshot() if COST_TRACKER else {"total_calls": 0, "total_usd": 0.0, "by_agent": {}}
    return jsonify({
        "provider":          settings.PROVIDER,
        "model_ceo":         settings.MODEL_CEO,
        "model_manager":     settings.MODEL_MANAGER,
        "model_worker":      settings.MODEL_WORKER,
        "file_access_mode":  settings.FILE_ACCESS_MODE,
        "shell_access_mode": settings.SHELL_ACCESS_MODE,
        "access_modes":      sorted(settings.ACCESS_MODES),
        "tools":             settings.tool_toggle_snapshot(),
        "costs":             snap,
        "project_root":      settings.PROJECT_ROOT,
    })

@app.route("/api/uploads")
def api_uploads():
    sid = request.args.get("session_id", type=int)
    if sid is None:
        sid = _current_session_id()
    if sid is None:
        return jsonify({"path": None, "files": []})
    root = os.path.join(settings.INBOX_DIR, f"session_{sid}")
    files: list[dict] = []
    if os.path.isdir(root):
        for name in sorted(os.listdir(root)):
            full = os.path.join(root, name)
            try:
                st = os.stat(full)
                files.append({
                    "name":  name,
                    "size":  st.st_size,
                    "is_dir": os.path.isdir(full),
                    "mtime": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(timespec="seconds"),
                })
            except OSError:
                pass
    return jsonify({"path": root, "files": files})


# ─── WRITE-API ───────────────────────────────────────────────────────────────

@app.route("/api/chat/send", methods=["POST"])
def api_chat_send():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    sid = data.get("session_id")
    if not text:
        return jsonify({"error": "Leere Nachricht"}), 400
    if sid is None:
        sid = _current_session_id()
    if sid is None:
        return jsonify({"error": "Kein Chat aktiv"}), 400

    # Auf passende Session umschalten, falls nötig (ans main.py-RUNTIME)
    cur = _q(_mgr(), "SELECT id FROM chat_sessions ORDER BY id DESC LIMIT 1")
    cur_id = int(cur[0]["id"]) if cur else None
    # Wenn Web-Session != neueste Session, fragen wir den main.py-RUNTIME nicht direkt –
    # aber wir setzen die Session aktiv per Action, damit der CEO darauf antwortet.
    aid = _queue_action("switch_session", {"session_id": int(sid)})
    _wait_action(aid, timeout=2.0)

    msg_id = _exec(
        _mgr(),
        "INSERT INTO user_messages (created_at, session_id, direction, content) VALUES (?, ?, 'in', ?)",
        (_now(), int(sid), text),
    )
    return jsonify({"id": msg_id, "session_id": int(sid)})


@app.route("/api/chat/new", methods=["POST"])
def api_chat_new():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip() or f"Chat {datetime.now().strftime('%H:%M')}"
    sid = _exec(
        _mgr(),
        "INSERT INTO chat_sessions (created_at, name, vault_path) VALUES (?, ?, '')",
        (_now(), name),
    )
    aid = _queue_action("switch_session", {"session_id": int(sid)})
    _wait_action(aid, timeout=2.0)
    return jsonify({"id": sid, "name": name})


@app.route("/api/chat/<int:sid>", methods=["DELETE"])
def api_chat_delete(sid):
    rows = _q(_mgr(), "SELECT id, name FROM chat_sessions WHERE id = ?", (sid,))
    if not rows:
        return jsonify({"error": "Chat nicht gefunden"}), 404
    name = rows[0]["name"]

    # Zugehörige Nachrichten + Threads + Anfragen entfernen
    for table in (
        "user_messages", "threads", "status_updates", "reports",
        "software_requests", "access_requests", "terminal_commands",
        "master_plans", "briefings",
    ):
        try:
            _exec(_mgr(), f"DELETE FROM {table} WHERE session_id = ?", (sid,))
        except sqlite3.OperationalError:
            pass  # Tabelle fehlt evtl. — kein Drama
    _exec(_mgr(), "DELETE FROM chat_sessions WHERE id = ?", (sid,))

    # Upload-Ordner aufräumen
    up_dir = os.path.join(settings.INBOX_DIR, f"session_{sid}")
    if os.path.isdir(up_dir):
        try:
            shutil.rmtree(up_dir)
        except OSError:
            pass

    # Falls main.py gerade auf dieser Session war, auf neueste umschalten
    remaining = _q(_mgr(), "SELECT id FROM chat_sessions ORDER BY id DESC LIMIT 1")
    if remaining:
        aid = _queue_action("switch_session", {"session_id": int(remaining[0]["id"])})
        _wait_action(aid, timeout=2.0)

    return jsonify({"deleted": sid, "name": name})


@app.route("/api/chat/switch", methods=["POST"])
def api_chat_switch():
    data = request.get_json(silent=True) or {}
    sid = data.get("session_id")
    if sid is None:
        return jsonify({"error": "session_id fehlt"}), 400
    aid = _queue_action("switch_session", {"session_id": int(sid)})
    res = _wait_action(aid)
    return jsonify(res)


@app.route("/api/chat/vault", methods=["POST"])
def api_chat_vault():
    data = request.get_json(silent=True) or {}
    sid = data.get("session_id")
    vault = (data.get("vault_path") or "").strip()
    if sid is None:
        return jsonify({"error": "session_id fehlt"}), 400
    if vault and not os.path.isdir(os.path.expanduser(vault)):
        return jsonify({"error": f"Ordner nicht gefunden: {vault}"}), 400
    aid = _queue_action("set_vault", {"session_id": int(sid), "vault_path": os.path.expanduser(vault)})
    res = _wait_action(aid)
    return jsonify(res)


@app.route("/api/commands/<int:cid>/approve", methods=["POST"])
def api_command_approve(cid):
    rows = _q(_mgr(), "SELECT * FROM terminal_commands WHERE id = ?", (cid,))
    if not rows:
        return jsonify({"error": "Befehl nicht gefunden"}), 404
    if rows[0]["status"] != "pending":
        return jsonify({"error": f"Befehl ist {rows[0]['status']}"}), 400
    aid = _queue_action("approve_command", {"command_id": cid})
    res = _wait_action(aid, timeout=15.0)
    return jsonify(res)


@app.route("/api/commands/<int:cid>/deny", methods=["POST"])
def api_command_deny(cid):
    rows = _q(_mgr(), "SELECT * FROM terminal_commands WHERE id = ?", (cid,))
    if not rows:
        return jsonify({"error": "Befehl nicht gefunden"}), 404
    if rows[0]["status"] != "pending":
        return jsonify({"error": f"Befehl ist {rows[0]['status']}"}), 400
    _exec(
        _mgr(),
        "UPDATE terminal_commands SET status='denied', decided_at=? WHERE id=?",
        (_now(), cid),
    )
    _exec(
        _mgr(),
        "INSERT INTO threads (created_at, session_id, author, topic, content) VALUES (?, ?, 'system_terminal', ?, ?)",
        (_now(), rows[0].get("session_id"),
         f"Terminal command #{cid} denied",
         f"User hat Terminal-Befehl #{cid} abgelehnt: {rows[0]['command']}"),
    )
    return jsonify({"status": "denied"})


@app.route("/api/tools/<name>", methods=["POST"])
def api_tools(name):
    data = request.get_json(silent=True) or {}
    enabled = bool(data.get("enabled"))
    try:
        settings.save_tool_toggle(name, enabled)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    aid = _queue_action("refresh_tools", {})
    _wait_action(aid, timeout=2.0)
    return jsonify({"name": name, "enabled": enabled})


@app.route("/api/access", methods=["POST"])
def api_access():
    data = request.get_json(silent=True) or {}
    file_mode = (data.get("file_mode") or "").strip().lower()
    shell_mode = (data.get("shell_mode") or "").strip().lower()
    if file_mode not in settings.ACCESS_MODES or shell_mode not in settings.ACCESS_MODES:
        return jsonify({"error": "Ungültiger Modus"}), 400
    try:
        settings.save_access_modes(file_mode, shell_mode)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    aid = _queue_action("refresh_tools", {})
    _wait_action(aid, timeout=2.0)
    return jsonify({"file_mode": file_mode, "shell_mode": shell_mode})


@app.route("/api/upload", methods=["POST"])
def api_upload():
    sid = request.form.get("session_id", type=int) or _current_session_id()
    if sid is None:
        return jsonify({"error": "Kein Chat aktiv"}), 400
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"error": "Keine Datei"}), 400

    safe_name = os.path.basename(f.filename)
    dest_root = os.path.join(settings.INBOX_DIR, f"session_{sid}")
    os.makedirs(dest_root, exist_ok=True)

    # Eindeutigen Namen finden
    candidate = os.path.join(dest_root, safe_name)
    stem, ext = os.path.splitext(safe_name)
    n = 2
    while os.path.exists(candidate):
        candidate = os.path.join(dest_root, f"{stem}_{n}{ext}")
        n += 1
    f.save(candidate)

    # Als User-Message in den Chat einhängen
    _exec(
        _mgr(),
        "INSERT INTO user_messages (created_at, session_id, direction, content) VALUES (?, ?, 'in', ?)",
        (_now(), int(sid),
         f"Datei hochgeladen.\nGespeichert unter: {candidate}\nNutze diese Datei als Kontext."),
    )
    return jsonify({"path": candidate, "name": os.path.basename(candidate)})


# ─── Error-Handler ───────────────────────────────────────────────────────────

@app.errorhandler(Exception)
def _on_error(e):
    from werkzeug.exceptions import HTTPException
    if isinstance(e, HTTPException):
        return jsonify({"error": e.description}), e.code
    import traceback
    traceback.print_exc()
    return jsonify({"error": f"{type(e).__name__}: {e}"}), 500


# ─── Static / Root ───────────────────────────────────────────────────────────

@app.route("/")
def root():
    return app.send_static_file("index.html")

@app.route("/favicon.ico")
def favicon():
    return Response(status=204)


# ─── Start ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    _bootstrap_db()
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 7842
    print(f"""
  ╔══════════════════════════════════════╗
  ║   ◈  AgentCompany Dashboard         ║
  ║   → http://localhost:{port}           ║
  ║   Strg+C zum Beenden                 ║
  ╚══════════════════════════════════════╝
""")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
