# DB-Schema

## `managers_shared.db` (Leadership Channel)

### `master_plans`
| Spalte      | Typ      | Beschreibung                          |
|-------------|----------|---------------------------------------|
| id          | INTEGER  | PRIMARY KEY AUTOINCREMENT             |
| created_at  | TEXT     | ISO-Timestamp                         |
| author      | TEXT     | "ceo"                                 |
| user_request| TEXT     | Original-Anfrage des Users            |
| content     | TEXT     | Master-Plan-Text                      |
| version     | INTEGER  | Bei Anpassung +1                      |

### `briefings`
| Spalte      | Typ      | Beschreibung                          |
|-------------|----------|---------------------------------------|
| id          | INTEGER  | PRIMARY KEY AUTOINCREMENT             |
| created_at  | TEXT     |                                       |
| plan_id     | INTEGER  | FK → master_plans.id                  |
| target_dept | TEXT     | "engineering" / "research" / ...      |
| content     | TEXT     | Konkrete Aufgaben für das Team        |
| read_at     | TEXT     | Wann der Manager es gelesen hat       |

### `threads`
| Spalte      | Typ      | Beschreibung                          |
|-------------|----------|---------------------------------------|
| id          | INTEGER  | PRIMARY KEY AUTOINCREMENT             |
| created_at  | TEXT     |                                       |
| parent_id   | INTEGER  | NULL = neuer Thread, sonst Antwort    |
| author      | TEXT     | "ceo" / "manager_engineering" / ...   |
| topic       | TEXT     | Nur bei parent_id=NULL                |
| content     | TEXT     | Nachricht                             |

### `status_updates`
| Spalte      | Typ      | Beschreibung                          |
|-------------|----------|---------------------------------------|
| id          | INTEGER  | PRIMARY KEY AUTOINCREMENT             |
| created_at  | TEXT     |                                       |
| author      | TEXT     | Manager-ID                            |
| status      | TEXT     | "in_progress" / "blocked" / "done"    |
| blocker     | INTEGER  | 0/1 — Boolean                         |
| message     | TEXT     | Freitext                              |

### `reports`
| Spalte      | Typ      | Beschreibung                          |
|-------------|----------|---------------------------------------|
| id          | INTEGER  | PRIMARY KEY AUTOINCREMENT             |
| created_at  | TEXT     |                                       |
| author      | TEXT     | Manager-ID                            |
| plan_id     | INTEGER  | FK → master_plans.id                  |
| content     | TEXT     | Konsolidierter Team-Report            |

### `terminal_commands`
| Spalte      | Typ      | Beschreibung                          |
|-------------|----------|---------------------------------------|
| id          | INTEGER  | PRIMARY KEY AUTOINCREMENT             |
| created_at  | TEXT     |                                       |
| requester   | TEXT     | meistens "ceo"                        |
| command     | TEXT     | Shell-Befehl                          |
| cwd         | TEXT     | Arbeitsordner oder NULL               |
| reason      | TEXT     | Warum der Befehl gebraucht wird       |
| status      | TEXT     | pending / denied / running / done / error |
| exit_code   | INTEGER  | Prozess-Exit-Code                     |
| stdout      | TEXT     | Standardausgabe                       |
| stderr      | TEXT     | Fehlerausgabe                         |
| decided_at  | TEXT     | Zeitpunkt der User-Freigabe/Ablehnung |
| finished_at | TEXT     | Zeitpunkt nach Ausführung             |

---

## `team_<id>_chat.db` (eine pro dynamischem Team)

### `tasks`
| Spalte      | Typ      | Beschreibung                          |
|-------------|----------|---------------------------------------|
| id          | INTEGER  | PRIMARY KEY AUTOINCREMENT             |
| created_at  | TEXT     |                                       |
| assigner    | TEXT     | z.B. "manager_t3"                     |
| worker_id   | TEXT     | z.B. "worker_t3_2"                    |
| description | TEXT     |                                       |
| status      | TEXT     | "pending" / "in_progress" / "done"    |

### `chat`
| Spalte      | Typ      | Beschreibung                          |
|-------------|----------|---------------------------------------|
| id          | INTEGER  | PRIMARY KEY AUTOINCREMENT             |
| created_at  | TEXT     |                                       |
| author      | TEXT     | Worker- oder Manager-ID               |
| content     | TEXT     |                                       |
| reply_to    | INTEGER  | NULL oder chat.id                     |

### `results`
| Spalte      | Typ      | Beschreibung                          |
|-------------|----------|---------------------------------------|
| id          | INTEGER  | PRIMARY KEY AUTOINCREMENT             |
| created_at  | TEXT     |                                       |
| task_id     | INTEGER  | FK → tasks.id                         |
| worker_id   | TEXT     |                                       |
| content     | TEXT     | Ergebnis                              |

---

## Index für Performance
Alle DBs bekommen einen Index auf `created_at` für schnelles Polling
nach „Einträgen seit timestamp X".
