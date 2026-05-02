/* ═══════════════════════════════════════════════════════════════════════════
   AgentCompany Dashboard — app.js
   Voller Funktionsumfang (Chat, Approve, Tools, Access, Vault, Upload, …)
═══════════════════════════════════════════════════════════════════════════ */

const S = {
  view: 'chat',
  sessions: [], activeSess: null, messages: [],
  feed: [], feedFilter: 'all',
  org: [], activeTeam: null, teamDetail: null,
  commands: [], pendingCmds: 0, pendingReqs: 0,
  requests: { software: [], access: [], terminal: [] },
  system: null,
  uploads: { path: null, files: [] },
  workspaces: [],
  dbLive: false,
};

/* ─── Utilities ──────────────────────────────────────────────────────────── */

function esc(s) {
  return String(s == null ? '' : s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
function trunc(s, n = 140) {
  s = String(s == null ? '' : s).replace(/\n/g, ' ').trim();
  return s.length > n ? s.slice(0, n) + '…' : s;
}
function fmtBytes(b) {
  if (b < 1024) return b + ' B';
  if (b < 1024 * 1024) return (b / 1024).toFixed(1) + ' KB';
  if (b < 1024 * 1024 * 1024) return (b / 1024 / 1024).toFixed(1) + ' MB';
  return (b / 1024 / 1024 / 1024).toFixed(2) + ' GB';
}
function ago(ts) {
  if (!ts) return '?';
  const utc = ts.replace(' ', 'T') + (ts.includes('+') || ts.endsWith('Z') ? '' : 'Z');
  const s = Math.floor((Date.now() - new Date(utc)) / 1000);
  if (s < 5)     return 'jetzt';
  if (s < 60)    return s + 's';
  if (s < 3600)  return Math.floor(s / 60) + 'm';
  if (s < 86400) return Math.floor(s / 3600) + 'h';
  return Math.floor(s / 86400) + 'd';
}
function agentColor(n) {
  if (!n) return '#9290b0';
  const l = n.toLowerCase();
  if (l === 'ceo')              return '#8b5cf6';
  if (l === 'user')             return '#e6e3f5';
  if (l.startsWith('manager'))  return '#2dd4bf';
  if (l.startsWith('worker'))   return '#60a5fa';
  return '#9290b0';
}
function agentLabel(n) {
  if (!n) return '?';
  if (n === 'ceo')  return 'CEO';
  if (n === 'user') return 'Du';
  return n.replace(/_/g, ' ');
}
function tag(status) {
  const s = (status || 'pending').toLowerCase();
  return `<span class="tag tag-${s}">${s}</span>`;
}
function empty(icon, title, sub = '') {
  return `<div class="empty">
    <div class="empty-icon">${icon}</div>
    <div class="empty-title">${title}</div>
    ${sub ? `<div class="empty-sub">${esc(sub)}</div>` : ''}
  </div>`;
}

const EICONS = {
  chat: '💬', thread: '📋', status: '📊', report: '📄',
  command: '⚡', plan: '🗺️', team_chat: '👥', result: '✅', task: '📌',
};

/* ─── HTTP ───────────────────────────────────────────────────────────────── */

async function api(method, url, body) {
  const init = { method, headers: {} };
  if (body !== undefined) {
    init.headers['Content-Type'] = 'application/json';
    init.body = JSON.stringify(body);
  }
  const r = await fetch(url, init);
  let data = null;
  try { data = await r.json(); } catch (_) {}
  if (!r.ok) {
    const msg = (data && data.error) || `HTTP ${r.status}`;
    throw new Error(msg);
  }
  return data;
}

/* ─── Toast ──────────────────────────────────────────────────────────────── */

let toastTimer = null;
function toast(msg, kind = '') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = (kind ? kind + ' ' : '') + 'show';
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove('show'), 2400);
}

/* ─── Navigation ─────────────────────────────────────────────────────────── */

function setView(v) {
  S.view = v;
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
  document.getElementById('panel-' + v).classList.add('active');
  document.getElementById('nav-' + v).classList.add('active');
  render();
}

/* ─── Master Render ──────────────────────────────────────────────────────── */

function render() {
  // Header
  document.getElementById('live-dot').className = 'pulse-dot' + (S.dbLive ? ' live' : '');
  document.getElementById('h-teams').textContent = S.org.length + ' Teams';
  document.getElementById('h-time').textContent = new Date().toLocaleTimeString('de-DE');

  // System status pill (header)
  const hs = document.getElementById('h-status');
  if (S.system) {
    hs.innerHTML =
      `<span class="pill">${esc(S.system.provider)}</span>` +
      `<span class="pill">${esc(S.system.model_ceo)}</span>` +
      `<span class="pill" style="color:${(S.system.file_access_mode==='full'||S.system.shell_access_mode==='full')?'#fbbf24':'#9290b0'}">` +
        `files=${esc(S.system.file_access_mode)} · shell=${esc(S.system.shell_access_mode)}</span>`;
  } else {
    hs.innerHTML = '';
  }

  // Pending alerts
  const cmdBadge = document.getElementById('cmd-badge');
  const reqBadge = document.getElementById('req-badge');
  if (S.pendingCmds > 0) { cmdBadge.style.display = ''; cmdBadge.textContent = S.pendingCmds; }
  else                   { cmdBadge.style.display = 'none'; }
  if (S.pendingReqs > 0) { reqBadge.style.display = ''; reqBadge.textContent = S.pendingReqs; }
  else                   { reqBadge.style.display = 'none'; }

  const total = S.pendingCmds + S.pendingReqs;
  document.getElementById('h-alert').innerHTML = total
    ? `<div class="h-alert-inner" onclick="setView('${S.pendingCmds ? 'commands' : 'requests'}')">⚡ ${total} offen</div>`
    : '';

  switch (S.view) {
    case 'chat':     renderChat();     break;
    case 'feed':     renderFeed();     break;
    case 'org':      renderOrg();      break;
    case 'teams':    renderTeams();    break;
    case 'commands': renderCommands(); break;
    case 'requests': renderRequests(); break;
    case 'system':   renderSystem();   break;
    case 'uploads':  renderUploads();  break;
  }
}

/* ─── Chat ───────────────────────────────────────────────────────────────── */

function renderChat() {
  const slist = document.getElementById('sessions-list');
  const mscroll = document.getElementById('msg-scroll');
  const meta = document.getElementById('composer-meta');

  if (!S.dbLive) {
    slist.innerHTML = '';
    mscroll.innerHTML = empty('💤', 'AgentCompany is not running yet',
      'Start main.py — the dashboard will connect automatically');
    meta.textContent = 'No backend';
    return;
  }
  if (!S.sessions.length) {
    slist.innerHTML = `<button class="btn" style="width:100%" onclick="newChatPrompt()">＋ Create first chat</button>`;
    mscroll.innerHTML = empty('💬', 'No chats yet',
      'Click the ＋ button on the left to create your first chat');
    meta.textContent = 'No active chat';
    return;
  }

  const sid = S.activeSess || S.sessions[0].id;
  const active = S.sessions.find(s => s.id === sid) || S.sessions[0];

  // Sessions
  slist.innerHTML = S.sessions.map(s => `
    <div class="session-item ${s.id === sid ? 'active' : ''}" onclick="selectSess(${s.id})">
      <div class="session-body">
        <div class="session-name">${esc(s.name || 'Chat')}</div>
        <div class="session-date">#${s.id} · ${ago(s.created_at)}</div>
      </div>
      <button class="session-del" title="Delete chat" onclick="deleteChat(event, ${s.id})">✕</button>
    </div>`).join('');

  // Vault input synchronisieren
  const vi = document.getElementById('vault-input');
  if (vi && document.activeElement !== vi) vi.value = active.vault_path || '';
  document.getElementById('vault-current').textContent = 'Current: ' + (active.vault_path || '—');

  // Schnell-Download des Projekts (erste passende Workspace)
  const dl = document.getElementById('chat-download');
  if (dl) {
    const ws = (S.workspaces || []).find(w => w.session_id === sid && w.exists);
    if (ws) {
      dl.style.display = '';
      dl.innerHTML = `<a class="btn btn-sm btn-primary" style="width:100%;display:block;text-align:center" href="/api/workspaces/${ws.id}/download" download>⬇ Projekt als ZIP</a>
        <div class="muted-mini" style="margin-top:4px">${esc(ws.short_name || ('Workspace #' + ws.id))}</div>`;
    } else {
      dl.style.display = 'none';
    }
  }

  // Composer-Meta
  meta.textContent = `Active chat: ${active.name} (#${active.id})`;

  // Messages
  const wasAtBottom = mscroll.scrollHeight - mscroll.scrollTop - mscroll.clientHeight < 100;
  const msgs = S.messages.filter(m => m.session_id === sid).reverse();
  mscroll.innerHTML = msgs.length
    ? msgs.map(m => `
        <div class="bubble-row ${m.direction}">
          <div class="bubble">${esc(m.content)}</div>
          <div class="bubble-meta">${esc(m.author || (m.direction === 'in' ? 'You' : 'AgentCompany'))} · ${ago(m.created_at)}</div>
        </div>`).join('')
    : `<div class="empty"><div class="empty-icon">✨</div><div class="empty-title">Start a new task</div></div>`;

  if (wasAtBottom) mscroll.scrollTop = mscroll.scrollHeight;
}

function selectSess(id) {
  S.activeSess = id;
  api('POST', '/api/chat/switch', { session_id: id }).catch(e => toast(e.message, 'err'));
  renderChat();
}

async function sendChat() {
  const ta = document.getElementById('composer-text');
  const text = ta.value.trim();
  if (!text) return;
  const btn = document.getElementById('send-btn');
  btn.disabled = true;
  ta.disabled = true;
  try {
    await api('POST', '/api/chat/send', { text, session_id: S.activeSess });
    ta.value = '';
    autoResize(ta);
    poll();
  } catch (e) {
    toast(e.message, 'err');
  } finally {
    btn.disabled = false;
    ta.disabled = false;
    ta.focus();
  }
}

async function deleteChat(ev, id) {
  ev.stopPropagation();
  const sess = S.sessions.find(s => s.id === id);
  const name = sess ? (sess.name || 'Chat') : `#${id}`;
  if (!confirm(`Delete chat "${name}"?\nAll messages and uploads for this chat will be removed.`)) return;
  try {
    await api('DELETE', `/api/chat/${id}`);
    if (S.activeSess === id) S.activeSess = null;
    toast(`Chat "${name}" deleted`, 'ok');
    poll();
  } catch (e) { toast(e.message, 'err'); }
}

async function newChatPrompt() {
  const name = prompt('Name for the new chat:', '');
  if (name === null) return;
  try {
    const r = await api('POST', '/api/chat/new', { name });
    S.activeSess = r.id;
    toast(`Chat "${r.name}" created`, 'ok');
    poll();
  } catch (e) { toast(e.message, 'err'); }
}

async function setVault() {
  const v = document.getElementById('vault-input').value.trim();
  const sid = S.activeSess;
  if (!sid) { toast('No active chat', 'err'); return; }
  try {
    await api('POST', '/api/chat/vault', { session_id: sid, vault_path: v });
    toast('Vault updated', 'ok');
    poll();
  } catch (e) { toast(e.message, 'err'); }
}

async function uploadFile(input) {
  const f = input.files && input.files[0];
  if (!f) return;
  await uploadFileObj(f);
  input.value = '';
}

async function uploadFileObj(f) {
  if (!S.activeSess) { toast('No active chat', 'err'); return; }
  const fd = new FormData();
  fd.append('file', f);
  fd.append('session_id', S.activeSess);
  try {
    const r = await fetch('/api/upload', { method: 'POST', body: fd });
    const data = await r.json();
    if (!r.ok) throw new Error(data.error || 'Upload fehlgeschlagen');
    toast(`Uploaded: ${data.name}`, 'ok');
    poll();
  } catch (e) { toast(e.message, 'err'); }
}

function autoResize(ta) {
  ta.style.height = 'auto';
  ta.style.height = Math.min(ta.scrollHeight, 200) + 'px';
}

/* ─── Live Feed ──────────────────────────────────────────────────────────── */

const FEED_TYPES = ['all','chat','team_chat','thread','task','result','status','report','command','plan'];

function renderFeed() {
  document.getElementById('feed-filters').innerHTML = FEED_TYPES.map(t =>
    `<button class="filt-btn ${S.feedFilter === t ? 'active' : ''}" onclick="setFF('${t}')">` +
    `${t === 'all' ? 'Alle' : (EICONS[t] || '?') + ' ' + t}</button>`
  ).join('');

  const evs = S.feedFilter === 'all' ? S.feed : S.feed.filter(e => e.etype === S.feedFilter);
  if (!evs.length) {
    document.getElementById('ev-list').innerHTML = empty('📡', 'No events yet');
    return;
  }
  document.getElementById('ev-list').innerHTML = evs.map(e => {
    const agent = e.agent || e.author || '?';
    const col   = agentColor(agent);
    const tb    = e.team_id ? `<span class="ev-team">Team ${e.team_id}</span>` : '';
    const txt   = trunc(e.content || e.topic || e.command || e.description || '');
    return `<div class="ev">
      <span class="ev-icon">${EICONS[e.etype] || '•'}</span>
      <div class="ev-body">
        <div class="ev-row1">
          <span class="ev-agent" style="color:${col}">${esc(agentLabel(agent))}</span>
          ${tb}
          <span class="ev-time">${ago(e.created_at)}</span>
        </div>
        <div class="ev-text">${esc(txt)}</div>
      </div>
    </div>`;
  }).join('');
}
function setFF(f) { S.feedFilter = f; renderFeed(); }

/* ─── Organigramm ────────────────────────────────────────────────────────── */

function renderOrg() {
  const el = document.getElementById('org-content');
  if (!S.dbLive) { el.innerHTML = empty('🏢', 'AgentCompany is not running yet'); return; }

  const teamsHtml = S.org.length
    ? S.org.map(t => {
        const ts = t.task_stats || {};
        const done = ts.done || 0, prog = ts.in_progress || 0, pend = ts.pending || 0;
        let caps = []; try { caps = JSON.parse(t.capabilities || '[]'); } catch (_) {}
        const st = t.latest_status;
        const stColor = st
          ? (st.status === 'done' ? 'var(--green)' : st.status === 'blocked' ? 'var(--red)' : 'var(--amber)')
          : 'var(--dim)';
        return `<div class="org-team-card" onclick="openTeam(${t.id})">
          <div class="org-team-name">${esc(t.name)}</div>
          <div class="org-team-desc">${esc(trunc(t.description, 90))}</div>
          <div class="org-stats">
            ${caps.map(c => `<span class="org-stat">${esc(c)}</span>`).join('')}
            ${done ? `<span class="org-stat g">✓ ${done}</span>` : ''}
            ${prog ? `<span class="org-stat a">↻ ${prog}</span>` : ''}
            ${pend ? `<span class="org-stat">⏳ ${pend}</span>` : ''}
            <span class="org-stat b">${t.worker_count}W</span>
            ${t.results_count ? `<span class="org-stat g">${t.results_count} results</span>` : ''}
          </div>
          ${st ? `<div class="org-team-status" style="color:${stColor}">${esc(trunc(st.message || st.status, 70))}</div>` : ''}
        </div>`;
      }).join('')
    : `<div style="color:var(--muted);font-size:12px;text-align:center;padding:24px">
         The CEO creates teams automatically as soon as it receives a task.
       </div>`;

  el.innerHTML = `
    <div class="org-wrap">
      <div class="org-ceo-box">
        <div class="org-ceo-name">◈ CEO</div>
        <div class="org-ceo-sub">plans · delegates · replies</div>
      </div>
      <div class="org-vline"></div>
      <div class="org-shared">📋 managers_shared.db — Leadership Channel</div>
      <div class="org-vline"></div>
      <div class="org-teams">${teamsHtml}</div>
    </div>`;
}
function openTeam(id) { S.activeTeam = id; setView('teams'); loadTeam(id); }

/* ─── Teams ──────────────────────────────────────────────────────────────── */

function renderTeams() {
  document.getElementById('teams-tabs').innerHTML = S.org.map(t =>
    `<button class="team-tab ${S.activeTeam === t.id ? 'active' : ''}" onclick="loadTeam(${t.id})">${esc(t.name)}</button>`
  ).join('');

  if (!S.org.length)   { document.getElementById('team-detail').innerHTML = empty('👥', 'No teams yet'); return; }
  if (!S.activeTeam)   { document.getElementById('team-detail').innerHTML = `<div style="color:var(--muted);font-size:13px;padding:14px">← Select a team</div>`; return; }
  if (S.teamDetail)    renderTeamDetail(S.teamDetail);
}

function renderTeamDetail(d) {
  const briefingHtml = d.briefing
    ? `<div class="card"><div class="card-label">📋 CEO Briefing</div>
        <div style="font-size:12.5px;line-height:1.6;white-space:pre-wrap;color:var(--dim)">${esc(trunc(d.briefing.content, 500))}</div></div>`
    : '';

  const tasksHtml = (d.tasks || []).map(t => `
    <div class="task-item">
      <div class="task-w"><span style="color:var(--blue)">▸ ${esc(t.worker_id)}</span>${tag(t.status)}</div>
      <div class="task-d">${esc(trunc(t.description, 200))}</div>
    </div>`).join('') || `<div style="color:var(--muted);padding:8px;font-size:12px">No tasks</div>`;

  const chatHtml = (d.chat || []).slice(-80).map(m => {
    const isMgr = (m.author || '').startsWith('manager');
    return `<div class="tmsg ${isMgr ? 'mgr' : 'wkr'}">
      <div class="tmsg-author" style="color:${agentColor(m.author)}">${esc(agentLabel(m.author))}</div>
      <div class="tmsg-content">${esc(trunc(m.content, 300))}</div>
    </div>`;
  }).join('') || `<div style="color:var(--muted);padding:8px;font-size:12px">No chat yet</div>`;

  const resultsHtml = (d.results || []).map(r => `
    <div class="result-item">
      <div class="result-w">✓ ${esc(r.worker_id)}</div>
      ${r.task_desc ? `<div class="result-task">${esc(trunc(r.task_desc, 60))}</div>` : ''}
      <div class="result-c">${esc(trunc(r.content, 300))}</div>
    </div>`).join('') || `<div style="color:var(--muted);padding:8px;font-size:12px">No results yet</div>`;

  document.getElementById('team-detail').innerHTML = briefingHtml + `
    <div class="team-3col">
      <div class="tcol"><div class="tcol-head">📌 Tasks (${(d.tasks || []).length})</div><div class="tcol-body">${tasksHtml}</div></div>
      <div class="tcol"><div class="tcol-head">💬 Team Chat</div><div class="tcol-body" id="tchat">${chatHtml}</div></div>
      <div class="tcol"><div class="tcol-head">✅ Results (${(d.results || []).length})</div><div class="tcol-body">${resultsHtml}</div></div>
    </div>`;

  setTimeout(() => { const c = document.getElementById('tchat'); if (c) c.scrollTop = c.scrollHeight; }, 30);
}

async function loadTeam(id) {
  S.activeTeam = id;
  document.querySelectorAll('.team-tab').forEach((b, i) => {
    b.classList.toggle('active', S.org[i] && S.org[i].id === id);
  });
  try {
    S.teamDetail = await fetch('/api/team/' + id).then(r => r.json());
    renderTeamDetail(S.teamDetail);
  } catch (_) { S.teamDetail = null; }
}

/* ─── Terminal-Befehle ───────────────────────────────────────────────────── */

function renderCommands() {
  const el = document.getElementById('cmd-content');
  if (!S.commands.length) {
    el.innerHTML = empty('⚡', 'No terminal commands', 'Commands requested by the CEO will appear here');
    return;
  }
  const pending = S.commands.filter(c => c.status === 'pending');
  let html = '';
  if (pending.length) {
    html += `<div class="pending-banner">
      <div class="pending-title">⚡ ${pending.length} command${pending.length > 1 ? 's' : ''} waiting for your approval</div>
      <div class="pending-hint">Click <b>Approve</b> or <b>Deny</b> directly.</div>
    </div>`;
  }
  html += S.commands.map(c => {
    const out = ((c.stdout || '') + (c.stderr ? '\n[stderr]\n' + c.stderr : '')).trim();
    return `<div class="cmd-item ${c.status}">
      <div class="cmd-header">
        <span class="cmd-id">#${c.id}</span>
        ${tag(c.status)}
        ${c.exit_code != null ? `<span class="cmd-id">exit=${c.exit_code}</span>` : ''}
        <span class="cmd-time">${ago(c.created_at)}</span>
      </div>
      <div class="cmd-code">$ ${esc(c.command)}</div>
      <div class="cmd-reason">💭 ${esc(c.reason || '–')}</div>
      ${c.status === 'pending' ? `<div class="cmd-actions">
          <button class="btn btn-green btn-sm" onclick="approveCmd(${c.id}, this)">✓ Approve</button>
          <button class="btn btn-red btn-sm" onclick="denyCmd(${c.id}, this)">✕ Deny</button>
        </div>` : ''}
      ${out ? `<div class="cmd-out">${esc(trunc(out, 4000))}</div>` : ''}
    </div>`;
  }).join('');
  el.innerHTML = html;
}

async function approveCmd(id, btn) {
  btn.disabled = true; btn.textContent = '… running …';
  try {
    const r = await api('POST', `/api/commands/${id}/approve`);
    toast(r.result || 'Command executed', r.status === 'error' ? 'err' : 'ok');
    poll();
  } catch (e) { toast(e.message, 'err'); btn.disabled = false; btn.textContent = '✓ Approve'; }
}

async function denyCmd(id, btn) {
  btn.disabled = true;
  try {
    await api('POST', `/api/commands/${id}/deny`);
    toast('Command denied', 'ok');
    poll();
  } catch (e) { toast(e.message, 'err'); btn.disabled = false; }
}

/* ─── Anfragen ───────────────────────────────────────────────────────────── */

function renderRequests() {
  const r = S.requests;
  const sec = (title, items, render) => `
    <div class="req-section">
      <h3>${title} (${items.length})</h3>
      ${items.length ? items.map(render).join('') : `<div style="color:var(--muted);font-size:12px;padding:8px 4px">No open requests.</div>`}
    </div>`;

  const html =
    sec('⚡ Terminal Commands', r.terminal, x => `
      <div class="req-item">
        <div class="req-body">
          <div class="req-id">#${x.id} · ${ago(x.created_at)}</div>
          <div class="req-main"><code>$ ${esc(x.command)}</code></div>
          <div class="req-reason">${esc(x.reason || '–')}</div>
        </div>
        <div class="cmd-actions">
          <button class="btn btn-green btn-sm" onclick="approveCmd(${x.id}, this)">Approve</button>
          <button class="btn btn-red btn-sm" onclick="denyCmd(${x.id}, this)">Deny</button>
        </div>
      </div>`) +
    sec('🔐 Access', r.access, x => `
      <div class="req-item">
        <div class="req-body">
          <div class="req-id">#${x.id} · ${ago(x.created_at)}</div>
          <div class="req-main">${esc(x.resource_type || '')} ${esc(x.access_mode || '')} · <code>${esc(x.target_path || '')}</code></div>
          <div class="req-reason">${esc(x.reason || '–')}</div>
        </div>
      </div>`) +
    sec('📦 Software', r.software, x => `
      <div class="req-item">
        <div class="req-body">
          <div class="req-id">#${x.id} · ${ago(x.created_at)}</div>
          <div class="req-main">${esc(x.package || '')}</div>
          <div class="req-reason">${esc(x.reason || '–')}</div>
        </div>
      </div>`);

  document.getElementById('req-content').innerHTML = html;
}

/* ─── System / Settings ──────────────────────────────────────────────────── */

function renderSystem() {
  const el = document.getElementById('sys-content');
  if (!S.system) { el.innerHTML = empty('⚙️', 'Loading system…'); return; }
  const sy = S.system;

  const planP = sy.plan || {};
  const planTotalAgents = planP.max_teams ? 1 + planP.max_teams * (1 + planP.max_workers_per_team) : null;
  const planCard = `<div class="card">
    <div class="card-label">📦 Dein Paket</div>
    <div class="kv-row"><span class="kv-key">Plan</span><span class="kv-val">${esc(planP.label || '–')}${planP.tagline ? ` <span style="color:var(--purple)">· ${esc(planP.tagline)}</span>` : ''}</span></div>
    <div class="kv-row"><span class="kv-key">Preis</span><span class="kv-val">${fmtPrice(planP.price_monthly_eur)}</span></div>
    <div class="kv-row"><span class="kv-key">CEO</span><span class="kv-val" style="color:var(--purple)">◈ immer aktiv</span></div>
    <div class="kv-row"><span class="kv-key">Max. Teams</span><span class="kv-val">${planP.max_teams ?? '–'}</span></div>
    <div class="kv-row"><span class="kv-key">Max. Worker/Team</span><span class="kv-val">${planP.max_workers_per_team ?? '–'}</span></div>
    <div class="kv-row"><span class="kv-key">Agents gesamt</span><span class="kv-val">${planTotalAgents ?? '–'}</span></div>
    <div class="kv-row"><span class="kv-key">Tools im Plan</span><span class="kv-val" style="font-size:11px">${(planP.tools || []).join(', ')}</span></div>
    <div style="margin-top:12px">
      <button class="btn btn-primary" onclick="openPlan(true)">Plan wechseln</button>
    </div>
  </div>`;

  const statusCard = `<div class="card">
    <div class="card-label">📊 Status</div>
    <div class="kv-row"><span class="kv-key">Provider</span><span class="kv-val">${esc(sy.provider)}</span></div>
    <div class="kv-row"><span class="kv-key">Modell CEO</span><span class="kv-val">${esc(sy.model_ceo)}</span></div>
    <div class="kv-row"><span class="kv-key">Modell Manager</span><span class="kv-val">${esc(sy.model_manager)}</span></div>
    <div class="kv-row"><span class="kv-key">Modell Worker</span><span class="kv-val">${esc(sy.model_worker)}</span></div>
    <div class="kv-row"><span class="kv-key">Project Root</span><span class="kv-val" style="font-size:10px">${esc(sy.project_root)}</span></div>
    <div class="kv-row"><span class="kv-key">Teams aktiv</span><span class="kv-val">${S.org.length}</span></div>
    <div class="kv-row"><span class="kv-key">Chats</span><span class="kv-val">${S.sessions.length}</span></div>
  </div>`;

  const accessCard = `<div class="card">
    <div class="card-label">🔐 Access Modes</div>
    <div class="access-grid">
      <div class="access-key">Files</div>
      <div class="access-opts">
        ${sy.access_modes.map(m => `<button class="access-opt ${m === sy.file_access_mode ? 'active' : ''} ${m === 'full' ? 'warn' : ''}" onclick="setAccess('${m}','${sy.shell_access_mode}')">${m}</button>`).join('')}
      </div>
      <div class="access-key">Shell</div>
      <div class="access-opts">
        ${sy.access_modes.map(m => `<button class="access-opt ${m === sy.shell_access_mode ? 'active' : ''} ${m === 'full' ? 'warn' : ''}" onclick="setAccess('${sy.file_access_mode}','${m}')">${m}</button>`).join('')}
      </div>
    </div>
    ${(sy.file_access_mode === 'full' || sy.shell_access_mode === 'full') ?
      `<div class="muted-mini" style="color:var(--red);margin-top:6px">⚠️ Full access is active — agents may modify files and run shell commands directly.</div>` : ''}
  </div>`;

  const allowed = sy.tools_allowed || {};
  const planLabel = (sy.plan && sy.plan.label) || 'aktuellen Plan';
  const toolsRows = Object.keys(sy.tools).sort().map(name => {
    const isOn = sy.tools[name];
    const isAllowed = allowed[name] !== false;
    if (!isAllowed) {
      return `<div class="toggle-row locked" title="'${name}' ist im Plan ${esc(planLabel)} nicht enthalten — wechsle den Plan in den Einstellungen.">
        <span class="toggle-name">🔒 ${esc(name)} <span class="lock-hint">Plan</span></span>
        <div class="switch disabled"></div>
      </div>`;
    }
    return `<div class="toggle-row">
      <span class="toggle-name">${esc(name)}</span>
      <div class="switch ${isOn ? 'on' : ''}" onclick="toggleTool('${name}', ${!isOn})"></div>
    </div>`;
  }).join('');
  const toolsCard = `<div class="card">
    <div class="card-label">🧰 Tools <span style="color:var(--muted);font-weight:400;text-transform:none;letter-spacing:0">— ${esc(planLabel)}-Plan</span></div>
    ${toolsRows}
    <div class="muted-mini" style="margin-top:10px">🔒 = im aktuellen Plan nicht freigeschaltet. Wechsle oben unter „Plan wechseln".</div>
  </div>`;

  const cs = sy.costs || { total_calls: 0, total_usd: 0, by_agent: {} };
  const byAgentRows = Object.keys(cs.by_agent || {}).sort().map(k => {
    const r = cs.by_agent[k];
    return `<div class="cost-row"><span class="a">${esc(k)} (${esc(r.model)})</span><span class="b">${r.calls} · $${(r.usd||0).toFixed(6)}</span></div>`;
  }).join('') || `<div class="cost-row"><span class="a">noch keine API-Calls</span><span class="b">–</span></div>`;
  const costsCard = `<div class="card">
    <div class="card-label">💰 Costs</div>
    <div class="kv-row"><span class="kv-key">API-Calls gesamt</span><span class="kv-val">${cs.total_calls || 0}</span></div>
    <div class="kv-row"><span class="kv-key">Estimated cost</span><span class="kv-val">$${(cs.total_usd || 0).toFixed(6)}</span></div>
    <div style="margin-top:10px">${byAgentRows}</div>
  </div>`;

  el.innerHTML = `<div class="sys-grid">${planCard}${statusCard}${accessCard}${toolsCard}${costsCard}</div>`;
}

async function toggleTool(name, enabled) {
  try {
    await api('POST', `/api/tools/${encodeURIComponent(name)}`, { enabled });
    toast(`${name}: ${enabled ? 'an' : 'aus'}`, 'ok');
    pollSystem();
  } catch (e) { toast(e.message, 'err'); }
}

async function setAccess(file_mode, shell_mode) {
  try {
    await api('POST', '/api/access', { file_mode, shell_mode });
    toast(`Access: files=${file_mode} · shell=${shell_mode}`, 'ok');
    pollSystem();
  } catch (e) { toast(e.message, 'err'); }
}

/* ─── Uploads ────────────────────────────────────────────────────────────── */

function renderUploads() {
  const el = document.getElementById('up-content');
  const u = S.uploads || { path: null, files: [] };
  const sid = S.activeSess;

  const drop = `<div class="up-drop" id="up-drop"
      onclick="document.getElementById('upload-file2').click()"
      ondragover="event.preventDefault();this.classList.add('drag')"
      ondragleave="this.classList.remove('drag')"
      ondrop="dropUpload(event)">
      <div class="up-drop-icon">📥</div>
      <div class="up-drop-text">Datei hier ablegen oder klicken</div>
      <div class="up-drop-sub">${u.path ? esc(u.path) : 'kein Chat aktiv'}</div>
    </div>
    <input type="file" id="upload-file2" style="display:none" onchange="uploadFile(this)">`;

  // Workspaces (Projekte vom CEO/Teams)
  const ws = (S.workspaces || []).filter(w => !sid || w.session_id === sid || w.session_id == null);
  const wsHtml = `
    <div class="dl-section">
      <h3>📦 Projekte / Workspaces</h3>
      ${ws.length
        ? `<div class="up-list">
            ${ws.map(w => `
              <div class="up-item">
                <div class="up-name">📁 ${esc(w.short_name || ('Workspace #' + w.id))}</div>
                <div class="up-meta">${esc(w.status || '–')} · ${ago(w.created_at)}</div>
                ${w.user_request ? `<div class="up-meta" style="margin-top:4px;white-space:normal;line-height:1.4">${esc(trunc(w.user_request, 110))}</div>` : ''}
                <div style="margin-top:8px">
                  <a class="btn btn-sm btn-primary" href="/api/workspaces/${w.id}/download" download
                     ${w.exists ? '' : 'style="opacity:0.5;pointer-events:none" title="Ordner fehlt"'}>⬇ Projekt als ZIP</a>
                </div>
              </div>`).join('')}
          </div>`
        : `<div style="color:var(--dim);font-size:13px;line-height:1.6;background:var(--bg1);border:1px dashed var(--border2);border-radius:8px;padding:14px">
            Noch kein Projekt vorhanden.<br>
            <span class="muted-mini">Sobald du dem CEO eine Aufgabe gibst und er ein Workspace anlegt, erscheint hier ein Download-Button für das gesamte Projekt als ZIP.</span>
          </div>`}
    </div>`;

  // Uploads
  const upHeader = `
    <div class="dl-section">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
        <h3 style="margin:0">📎 Datei-Uploads</h3>
        ${u.files && u.files.length && sid
          ? `<a class="btn btn-sm" href="/api/uploads/download?session_id=${sid}" download>⬇ Alle als ZIP</a>`
          : ''}
      </div>`;

  const list = u.files && u.files.length
    ? `<div class="up-list">${u.files.map(f => `
        <div class="up-item">
          <div class="up-name">${f.is_dir ? '📁 ' : '📄 '}${esc(f.name)}</div>
          <div class="up-meta">${fmtBytes(f.size)} · ${ago(f.mtime)}</div>
          <div style="margin-top:8px">
            <a class="btn btn-sm" href="/api/uploads/download?session_id=${sid}&name=${encodeURIComponent(f.name)}" download>⬇ ${f.is_dir ? 'ZIP' : 'Download'}</a>
          </div>
        </div>`).join('')}</div></div>`
    : `<div style="color:var(--muted);font-size:12px;padding:8px 4px">Keine Uploads.</div></div>`;

  el.innerHTML = drop + wsHtml + upHeader + list;
}

function dropUpload(e) {
  e.preventDefault();
  e.currentTarget.classList.remove('drag');
  const f = e.dataTransfer.files && e.dataTransfer.files[0];
  if (f) uploadFileObj(f);
}

/* ─── Help Modal ─────────────────────────────────────────────────────────── */

function openHelp()  { document.getElementById('help-modal').classList.add('show'); }
function closeHelp() { document.getElementById('help-modal').classList.remove('show'); }

/* ─── Plan-Picker ────────────────────────────────────────────────────────── */

let _planAutoShown = false;

function fmtPrice(eur) {
  if (eur == null) return '';
  if (eur === 0) return 'kostenlos';
  return `${eur} €/Monat`;
}

async function openPlan(force) {
  let payload;
  try { payload = await fetch('/api/plans').then(r => r.json()); }
  catch (e) { toast('Plans konnten nicht geladen werden', 'err'); return; }

  const grid = document.getElementById('plan-grid');
  const closeBtn = document.getElementById('plan-close');
  const title = document.getElementById('plan-title');
  const sub = document.getElementById('plan-sub');

  if (payload.selected) {
    title.textContent = 'Paket wechseln';
    sub.innerHTML = `Dein aktuelles Paket: <b style="color:var(--purple)">${esc(payload.label)}</b> · ${fmtPrice(payload.price_monthly_eur)}. Up- oder Downgrade jederzeit möglich.`;
    closeBtn.style.display = '';
  } else {
    title.textContent = 'Welches Paket möchtest du?';
    sub.innerHTML = 'Wähle ein Paket — du kannst es später jederzeit wechseln.';
    closeBtn.style.display = 'none';
  }

  grid.innerHTML = payload.plans.map(p => {
    const totalAgents = 1 + p.max_teams * (1 + p.max_workers_per_team);
    return `
    <div class="plan-card ${p.active ? 'active' : ''}" onclick="selectPlan('${p.slug}', this)">
      <div class="plan-price">${fmtPrice(p.price_monthly_eur)}</div>
      <div class="plan-name">${esc(p.label)}</div>
      <div class="plan-tag">${esc(p.tagline || '')}</div>
      <div class="plan-desc">${esc(p.description)}</div>
      <div class="plan-stats">
        <span class="plan-stat ceo-stat">◈ CEO inklusive</span>
        <span class="plan-stat">${p.max_teams} Teams</span>
        <span class="plan-stat">${p.max_workers_per_team} Worker/Team</span>
        <span class="plan-stat">≤ ${totalAgents} Agents gesamt</span>
      </div>
      ${p.highlights.map(h => `<div class="plan-hl">${esc(h)}</div>`).join('')}
      <button class="plan-pick">${p.active ? 'Aktiv' : 'Wählen'}</button>
    </div>`;
  }).join('') +
    `<div style="grid-column:1/-1" class="plan-free-note">
       ◈ Der CEO ist in jedem Paket dabei — er plant, delegiert und antwortet dir.<br>
       Wechsel zwischen Plänen ist jederzeit möglich (Up- oder Downgrade).
     </div>`;

  document.getElementById('plan-modal').classList.add('show');
}

function closePlan() {
  // Erstboot: nicht schließen lassen, bis was gewählt wurde
  if (S.system && S.system.plan && !S.system.plan.selected) return;
  document.getElementById('plan-modal').classList.remove('show');
}

async function selectPlan(slug, cardEl) {
  const card = (S.system && S.system.plan && S.system.plan.plans || []).find(p => p.slug === slug);
  if (card && card.active) { document.getElementById('plan-modal').classList.remove('show'); return; }

  const priceTxt = card ? fmtPrice(card.price_monthly_eur) : '';
  const isChange = S.system && S.system.plan && S.system.plan.selected;
  const msg = isChange
    ? `Auf Plan „${slug}" (${priceTxt}) wechseln?`
    : `Plan „${slug}" (${priceTxt}) wählen?`;
  if (!confirm(msg)) return;

  const allCards = document.querySelectorAll('.plan-card');
  allCards.forEach(c => c.style.pointerEvents = 'none');
  try {
    await api('POST', '/api/plans/select', { plan: slug });
    toast(isChange ? `Auf ${slug} gewechselt` : `Plan gewählt: ${slug}`, 'ok');
    document.getElementById('plan-modal').classList.remove('show');
    await pollSystem();
    render();
  } catch (e) {
    toast(e.message, 'err');
    allCards.forEach(c => c.style.pointerEvents = '');
  }
}

function maybeAutoOpenPlan() {
  if (_planAutoShown) return;
  if (S.system && S.system.plan && S.system.plan.selected === false) {
    _planAutoShown = true;
    openPlan();
  }
}

/* ─── Data Polling ───────────────────────────────────────────────────────── */

let pollTimer = null;

async function poll() {
  try {
    const [ov, chat, feed, org, cmds, reqs] = await Promise.all([
      fetch('/api/overview').then(r => r.json()),
      fetch('/api/chat').then(r => r.json()),
      fetch('/api/feed').then(r => r.json()),
      fetch('/api/org').then(r => r.json()),
      fetch('/api/commands').then(r => r.json()),
      fetch('/api/requests').then(r => r.json()),
    ]);

    S.dbLive      = ov.db_exists;
    S.sessions    = ov.sessions || [];
    S.pendingCmds = ov.pending_commands || 0;
    S.pendingReqs = (ov.pending_software || 0) + (ov.pending_access || 0);
    S.messages    = chat.messages || [];
    S.feed        = feed || [];
    S.org         = org || [];
    S.commands    = cmds || [];
    S.requests    = reqs || { software: [], access: [], terminal: [] };

    if (!S.activeSess && S.sessions.length) S.activeSess = S.sessions[0].id;
    if (!S.activeTeam && S.org.length)      S.activeTeam = S.org[0].id;

    if (S.view === 'teams' && S.activeTeam) {
      try { S.teamDetail = await fetch('/api/team/' + S.activeTeam).then(r => r.json()); } catch (_) {}
    }
    if (S.view === 'system' || !S.system) await pollSystem(true);
    if (S.view === 'uploads' || S.view === 'chat') await pollUploads();

    render();
    maybeAutoOpenPlan();
  } catch (e) {
    console.error('poll error:', e);
  }
  clearTimeout(pollTimer);
  pollTimer = setTimeout(poll, 3000);
}

async function pollSystem(silent) {
  try { S.system = await fetch('/api/system').then(r => r.json()); }
  catch (_) {}
  if (!silent) render();
}

async function pollUploads() {
  try {
    const url = '/api/uploads' + (S.activeSess ? `?session_id=${S.activeSess}` : '');
    S.uploads = await fetch(url).then(r => r.json());
  } catch (_) {}
  try {
    const url = '/api/workspaces' + (S.activeSess ? `?session_id=${S.activeSess}` : '');
    S.workspaces = await fetch(url).then(r => r.json());
  } catch (_) {}
}

/* ─── Init ───────────────────────────────────────────────────────────────── */

window.addEventListener('DOMContentLoaded', () => {
  const ta = document.getElementById('composer-text');
  if (ta) {
    ta.addEventListener('input', () => autoResize(ta));
    ta.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendChat();
      }
    });
  }
  // Esc schließt Modal
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeHelp(); });
  poll();
});
