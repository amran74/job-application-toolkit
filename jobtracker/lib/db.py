import sqlite3
import json
from datetime import datetime, date
import pandas as pd

DB_PATH = "jobs.db"

STATUS_ORDER = ["Interested", "Applied", "Interview", "Offer", "Rejected", "Ghosted"]
CHANNELS = ["LinkedIn", "Company Site", "Referral", "Email", "Recruiter", "Other"]
CV_VERSIONS = ["Data/BI", "Marketing Analyst", "Ops/Management", "Fraud/Risk", "Custom"]

def utc_now():
    return datetime.utcnow().isoformat(timespec="seconds")

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            company TEXT NOT NULL,
            role TEXT NOT NULL,
            location TEXT,
            link TEXT,
            channel TEXT,
            status TEXT NOT NULL,

            cv_version TEXT,
            tags TEXT,
            contact_name TEXT,
            contact_email TEXT,
            salary_min INTEGER,
            salary_max INTEGER,

            date_interested TEXT,
            date_applied TEXT,
            date_outcome TEXT,
            next_followup TEXT,

            last_update TEXT,
            jd_text TEXT,
            notes TEXT
        );
    """)

    cols = [r[1] for r in conn.execute("PRAGMA table_info(jobs);").fetchall()]
    def add_col(name, ddl):
        if name not in cols:
            conn.execute(f"ALTER TABLE jobs ADD COLUMN {ddl};")

    add_col("cv_version", "cv_version TEXT")
    add_col("date_outcome", "date_outcome TEXT")
    add_col("tags", "tags TEXT")
    add_col("contact_name", "contact_name TEXT")
    add_col("contact_email", "contact_email TEXT")
    add_col("salary_min", "salary_min INTEGER")
    add_col("salary_max", "salary_max INTEGER")
    add_col("next_followup", "next_followup TEXT")

    conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company);")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS cv_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            model TEXT,
            archetype TEXT,
            tone TEXT,
            length TEXT,
            include_cover INTEGER NOT NULL,
            cv_json TEXT NOT NULL,
            cover_json TEXT NOT NULL,
            notes_json TEXT NOT NULL,
            cv_pdf_path TEXT,
            cover_pdf_path TEXT,
            FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
        );
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_cv_versions_job ON cv_versions(job_id);")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT
        );
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS cv_library (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            label TEXT NOT NULL,
            source TEXT NOT NULL,
            job_id INTEGER,
            file_path TEXT NOT NULL,
            notes TEXT
        );
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_cv_library_job ON cv_library(job_id);")

    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cv_content_blocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            language_code TEXT NOT NULL,
            section_key TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            tags TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            sort_order INTEGER NOT NULL DEFAULT 0
        );
    """)

    conn.commit()


def set_setting(conn, key: str, value: str):
    conn.execute("""
        INSERT INTO app_settings(key, value, updated_at)
        VALUES(?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at;
    """, (key, value, utc_now()))
    conn.commit()

def get_setting(conn, key: str) -> str:
    row = conn.execute("SELECT value FROM app_settings WHERE key=?;", (key,)).fetchone()
    return row[0] if row and row[0] else ""

def infer_channel(link: str):
    if not link:
        return "Other"
    s = link.lower()
    if "linkedin.com" in s:
        return "LinkedIn"
    return "Company Site"

def parse_tags(tag_text: str):
    if not tag_text:
        return ""
    items = [t.strip() for t in tag_text.replace(";", ",").split(",")]
    items = [t for t in items if t]
    return ", ".join(dict.fromkeys(items))

def fetch_jobs(conn) -> pd.DataFrame:
    df = pd.read_sql_query("SELECT * FROM jobs ORDER BY datetime(created_at) DESC;", conn)
    if df.empty:
        return df
    for col in ["created_at", "date_interested", "date_applied", "date_outcome", "next_followup", "last_update"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    df["channel"] = df["channel"].fillna("Other")
    df["cv_version"] = df["cv_version"].fillna("Custom")
    df["tags"] = df["tags"].fillna("")
    return df

def get_job(conn, job_id: int) -> dict | None:
    cur = conn.execute("SELECT * FROM jobs WHERE id=?;", (job_id,))
    row = cur.fetchone()
    if not row:
        return None
    cols = [d[0] for d in cur.description]
    return dict(zip(cols, row))

def upsert_job(conn, job_id, payload: dict):
    now = utc_now()
    payload = payload.copy()
    payload["last_update"] = now

    cols = [
        "company","role","location","link","channel","status",
        "cv_version","tags","contact_name","contact_email","salary_min","salary_max",
        "date_interested","date_applied","date_outcome","next_followup",
        "jd_text","notes","last_update"
    ]

    if job_id is None:
        created_at = now
        values = [created_at] + [payload.get(c) for c in cols]
        conn.execute(
            f"INSERT INTO jobs (created_at, {', '.join(cols)}) VALUES (?, {', '.join(['?']*len(cols))});",
            values
        )
    else:
        sets = ", ".join([f"{c}=?" for c in cols])
        values = [payload.get(c) for c in cols] + [job_id]
        conn.execute(f"UPDATE jobs SET {sets} WHERE id=?;", values)
    conn.commit()

def delete_job(conn, job_id: int):
    conn.execute("DELETE FROM jobs WHERE id=?;", (job_id,))
    conn.commit()

def update_status(conn, job_id: int, new_status: str):
    now = utc_now()
    row = conn.execute("SELECT date_applied, date_outcome FROM jobs WHERE id=?;", (job_id,)).fetchone()
    date_applied, date_outcome = row if row else (None, None)

    today = date.today().isoformat()
    set_applied = None
    set_outcome = None

    if new_status in ["Applied","Interview","Offer","Rejected","Ghosted"] and not date_applied:
        set_applied = today
    if new_status in ["Interview","Offer","Rejected","Ghosted"] and not date_outcome:
        set_outcome = today

    if set_applied and set_outcome:
        conn.execute("UPDATE jobs SET status=?, date_applied=?, date_outcome=?, last_update=? WHERE id=?;",
                     (new_status, set_applied, set_outcome, now, job_id))
    elif set_applied:
        conn.execute("UPDATE jobs SET status=?, date_applied=?, last_update=? WHERE id=?;",
                     (new_status, set_applied, now, job_id))
    elif set_outcome:
        conn.execute("UPDATE jobs SET status=?, date_outcome=?, last_update=? WHERE id=?;",
                     (new_status, set_outcome, now, job_id))
    else:
        conn.execute("UPDATE jobs SET status=?, last_update=? WHERE id=?;",
                     (new_status, now, job_id))
    conn.commit()

def metrics(df):
    if df is None or df.empty:
        return {"total_applied":0,"app_to_interview":0,"interview_to_offer":0,"ghost_rate":0,"avg_days_to_outcome":None}

    total_applied = int(df["status"].isin(["Applied","Interview","Offer","Rejected","Ghosted"]).sum())
    positives = df["status"].isin(["Interview","Offer"])
    interviews = int(positives.sum())
    offers = int(df["status"].eq("Offer").sum())
    ghosts = int(df["status"].eq("Ghosted").sum())

    app_to_interview = (int(positives.sum())/total_applied)*100 if total_applied else 0
    interview_to_offer = (offers/interviews)*100 if interviews else 0
    ghost_rate = (ghosts/total_applied)*100 if total_applied else 0

    if "date_applied" in df.columns and "date_outcome" in df.columns:
        tmp = df[df["date_applied"].notna() & df["date_outcome"].notna()].copy()
        avg_days = float((tmp["date_outcome"] - tmp["date_applied"]).dt.days.mean()) if not tmp.empty else None
    else:
        avg_days = None

    return {
        "total_applied": total_applied,
        "app_to_interview": app_to_interview,
        "interview_to_offer": interview_to_offer,
        "ghost_rate": ghost_rate,
        "avg_days_to_outcome": avg_days
    }

def outcome_breakdown(df, group_col: str, min_count: int = 2):
    if df is None or df.empty or group_col not in df.columns:
        return None
    outcomes = df[df["status"].isin(["Interview","Offer","Rejected","Ghosted"])].copy()
    if outcomes.empty:
        return None
    outcomes["is_positive"] = outcomes["status"].isin(["Interview","Offer"]).astype(int)
    g = outcomes.groupby(group_col)["is_positive"].agg(["count","mean"]).reset_index()
    g.rename(columns={"mean":"positive_rate"}, inplace=True)
    g = g[g["count"] >= min_count].sort_values(["positive_rate","count"], ascending=[False, False])
    return g

def save_cv_version(conn, job_id: int, model: str, archetype: str, tone: str, length: str, include_cover: bool,
                    cv_json: str, cover_json: str, notes_json: str,
                    cv_pdf_path: str | None = None, cover_pdf_path: str | None = None) -> int:
    now = utc_now()
    cur = conn.execute("""
        INSERT INTO cv_versions
        (job_id, created_at, model, archetype, tone, length, include_cover, cv_json, cover_json, notes_json, cv_pdf_path, cover_pdf_path)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (job_id, now, model, archetype, tone, length, 1 if include_cover else 0,
          cv_json, cover_json, notes_json, cv_pdf_path, cover_pdf_path))
    conn.commit()
    return int(cur.lastrowid)

def update_cv_paths(conn, version_id: int, cv_pdf_path: str | None, cover_pdf_path: str | None):
    conn.execute("""
        UPDATE cv_versions
        SET cv_pdf_path = COALESCE(?, cv_pdf_path),
            cover_pdf_path = COALESCE(?, cover_pdf_path)
        WHERE id = ?;
    """, (cv_pdf_path, cover_pdf_path, version_id))
    conn.commit()

def fetch_cv_versions(conn, job_id: int) -> pd.DataFrame:
    df = pd.read_sql_query("""
        SELECT id, job_id, created_at, model, archetype, tone, length, include_cover, cv_pdf_path, cover_pdf_path
        FROM cv_versions
        WHERE job_id = ?
        ORDER BY datetime(created_at) DESC;
    """, conn, params=(job_id,))
    if df.empty:
        return df
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
    return df

def read_cv_version(conn, version_id: int) -> dict | None:
    cur = conn.execute("SELECT * FROM cv_versions WHERE id=?;", (version_id,))
    row = cur.fetchone()
    if not row:
        return None
    cols = [d[0] for d in cur.description]
    return dict(zip(cols, row))

def fetch_cv_content_blocks(conn, section_key: str | None = None, language_code: str | None = None, active_only: bool = False) -> pd.DataFrame:
    sql = """
        SELECT id, created_at, updated_at, language_code, section_key, title, content, tags, is_active, sort_order
        FROM cv_content_blocks
        WHERE 1=1
    """
    params = []

    if section_key:
        sql += " AND section_key = ?"
        params.append(section_key)

    if language_code:
        sql += " AND language_code = ?"
        params.append(language_code)

    if active_only:
        sql += " AND is_active = 1"

    sql += " ORDER BY language_code, section_key, sort_order, datetime(updated_at) DESC, id DESC"

    return pd.read_sql_query(sql, conn, params=params)


def get_cv_content_block(conn, block_id: int) -> dict | None:
    cur = conn.execute("""
        SELECT id, created_at, updated_at, language_code, section_key, title, content, tags, is_active, sort_order
        FROM cv_content_blocks
        WHERE id = ?;
    """, (block_id,))
    row = cur.fetchone()
    if not row:
        return None
    cols = [d[0] for d in cur.description]
    return dict(zip(cols, row))


def save_cv_content_block(
    conn,
    language_code: str,
    section_key: str,
    title: str,
    content: str,
    tags: str = "",
    is_active: bool = True,
    sort_order: int = 0,
    block_id: int | None = None,
) -> int:
    now = utc_now()
    language_code = (language_code or "").strip().lower()
    section_key = (section_key or "").strip().lower()
    title = (title or "").strip()
    content = (content or "").strip()
    tags = parse_tags(tags or "")

    if not language_code:
        raise ValueError("language_code is required")
    if language_code not in ("en", "he"):
        raise ValueError("language_code must be 'en' or 'he'")
    if not section_key:
        raise ValueError("section_key is required")
    if not title:
        raise ValueError("title is required")
    if not content:
        raise ValueError("content is required")

    if block_id is None:
        cur = conn.execute("""
            INSERT INTO cv_content_blocks
            (created_at, updated_at, language_code, section_key, title, content, tags, is_active, sort_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            now, now, language_code, section_key, title, content,
            tags, 1 if is_active else 0, int(sort_order or 0)
        ))
        conn.commit()
        return int(cur.lastrowid)

    conn.execute("""
        UPDATE cv_content_blocks
        SET updated_at = ?,
            language_code = ?,
            section_key = ?,
            title = ?,
            content = ?,
            tags = ?,
            is_active = ?,
            sort_order = ?
        WHERE id = ?;
    """, (
        now, language_code, section_key, title, content,
        tags, 1 if is_active else 0, int(sort_order or 0), int(block_id)
    ))
    conn.commit()
    return int(block_id)


def delete_cv_content_block(conn, block_id: int):
    conn.execute("DELETE FROM cv_content_blocks WHERE id = ?;", (block_id,))
    conn.commit()


def build_cv_source_text(conn, block_ids: list[int], language_code: str | None = None) -> str:
    if not block_ids:
        return ""

    ordered_ids = []
    seen = set()
    for x in block_ids:
        try:
            xid = int(x)
        except Exception:
            continue
        if xid not in seen:
            seen.add(xid)
            ordered_ids.append(xid)

    if not ordered_ids:
        return ""

    placeholders = ",".join(["?"] * len(ordered_ids))
    sql = f"""
        SELECT id, language_code, section_key, title, content, tags, is_active, sort_order
        FROM cv_content_blocks
        WHERE id IN ({placeholders})
    """
    params = list(ordered_ids)

    if language_code:
        sql += " AND language_code = ?"
        params.append((language_code or "").strip().lower())

    rows = conn.execute(sql, params).fetchall()
    if not rows:
        return ""

    by_id = {}
    for r in rows:
        by_id[int(r[0])] = {
            "id": int(r[0]),
            "language_code": str(r[1] or "").strip().lower(),
            "section_key": str(r[2] or "").strip().lower(),
            "title": str(r[3] or "").strip(),
            "content": str(r[4] or "").strip(),
            "tags": str(r[5] or "").strip(),
            "is_active": int(r[6] or 0),
            "sort_order": int(r[7] or 0),
        }

    ordered_rows = [by_id[x] for x in ordered_ids if x in by_id and int(by_id[x]["is_active"]) == 1]
    if not ordered_rows:
        return ""

    section_labels = {
        "summary": "Summary",
        "experience": "Experience",
        "projects": "Projects",
        "education": "Education",
        "skills": "Skills",
        "languages": "Languages",
    }

    parts = []
    current_section = None

    for row in ordered_rows:
        sec = row["section_key"] or "other"
        title = row["title"]
        content = row["content"]

        if sec != current_section:
            label = section_labels.get(sec, sec.replace("_", " ").title())
            parts.append(label)
            current_section = sec

        if title and content:
            parts.append(f"{title}\n{content}")
        elif title:
            parts.append(title)
        elif content:
            parts.append(content)

    return "\n\n".join([x for x in parts if str(x).strip()]).strip()

# ==== CV CONTENT BLOCKS V2 ====

CV_BLOCK_SECTION_LABELS = {
    "summary": "Summary",
    "experience": "Experience",
    "projects": "Projects",
    "education": "Education",
    "skills": "Skills",
    "languages": "Languages",
}


def _safe_json_loads(s: str):
    try:
        return json.loads(s or "{}")
    except Exception:
        return {}


def _safe_json_dumps(obj) -> str:
    return json.dumps(obj or {}, ensure_ascii=False)


def _clean_text(x) -> str:
    return str(x or "").strip()


def _clean_url(x) -> str:
    return _clean_text(x)


def _bulletize_lines(text: str) -> str:
    text = _clean_text(text)
    if not text:
        return ""
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    out = []
    for line in lines:
        if line.startswith("•") or line.startswith("-"):
            out.append("• " + line.lstrip("•- ").strip())
        else:
            out.append("• " + line)
    return "\n".join(out)


def _period_text(start_value: str, end_value: str, is_current: bool = False) -> str:
    start_value = _clean_text(start_value)
    end_value = "Present" if bool(is_current) else _clean_text(end_value)

    if start_value and end_value:
        return f"{start_value}-{end_value}"
    if start_value:
        return start_value
    if end_value:
        return end_value
    return ""


def _normalize_block_payload(section_key: str, payload: dict):
    section_key = _clean_text(section_key).lower()
    payload = payload if isinstance(payload, dict) else {}
    data = {}
    label = ""
    source_text = ""

    if section_key == "summary":
        summary = _clean_text(payload.get("summary"))
        data = {"summary": summary}
        label = (summary[:70] + "...") if len(summary) > 70 else (summary or "Summary")
        source_text = summary

    elif section_key == "projects":
        project_name = _clean_text(payload.get("project_name"))
        tools = _clean_text(payload.get("tools"))
        period = _clean_text(payload.get("period"))
        description = _clean_text(payload.get("description"))
        github_url = _clean_url(payload.get("github_url"))
        live_url = _clean_url(payload.get("live_url"))

        data = {
            "project_name": project_name,
            "tools": tools,
            "period": period,
            "description": description,
            "github_url": github_url,
            "live_url": live_url,
        }

        header_parts = [x for x in [project_name, tools, period] if x]
        body_parts = []
        if description:
            body_parts.append(_bulletize_lines(description))
        if github_url:
            body_parts.append(f"GitHub: {github_url}")
        if live_url:
            body_parts.append(f"Live: {live_url}")

        label = project_name or "Project"
        source_text = "\n".join([" | ".join(header_parts)] + body_parts).strip()

    elif section_key == "experience":
        employer = _clean_text(payload.get("employer"))
        location = _clean_text(payload.get("location"))
        role = _clean_text(payload.get("role"))
        start_date = _clean_text(payload.get("start_date"))
        end_date = _clean_text(payload.get("end_date"))
        is_current = bool(payload.get("is_current"))
        achievements = _clean_text(payload.get("achievements"))

        data = {
            "employer": employer,
            "location": location,
            "role": role,
            "start_date": start_date,
            "end_date": end_date,
            "is_current": is_current,
            "achievements": achievements,
        }

        left = employer
        if location:
            left = f"{left}, {location}" if left else location

        period = _period_text(start_date, end_date, is_current)
        header_parts = [x for x in [left, role, period] if x]

        label = " - ".join([x for x in [employer, role] if x]) or "Experience"
        source_text = " | ".join(header_parts).strip()
        if achievements:
            source_text = (source_text + "\n" + _bulletize_lines(achievements)).strip()

    elif section_key == "education":
        degree = _clean_text(payload.get("degree"))
        field = _clean_text(payload.get("field"))
        institution = _clean_text(payload.get("institution"))
        location = _clean_text(payload.get("location"))
        start_date = _clean_text(payload.get("start_date"))
        end_date = _clean_text(payload.get("end_date"))
        notes = _clean_text(payload.get("notes"))

        data = {
            "degree": degree,
            "field": field,
            "institution": institution,
            "location": location,
            "start_date": start_date,
            "end_date": end_date,
            "notes": notes,
        }

        left = institution
        if location:
            left = f"{left}, {location}" if left else location

        middle = degree
        if field:
            middle = f"{middle} in {field}" if middle else field

        period = _period_text(start_date, end_date, False)
        header_parts = [x for x in [left, middle, period] if x]

        label = institution or degree or "Education"
        source_text = " | ".join(header_parts).strip()
        if notes:
            source_text = (source_text + "\n" + _bulletize_lines(notes)).strip()

    elif section_key == "skills":
        category = _clean_text(payload.get("category"))
        items = _clean_text(payload.get("items"))
        data = {
            "category": category,
            "items": items,
        }
        label = category or "Skills"
        source_text = f"{category}: {items}".strip(": ").strip()

    elif section_key == "languages":
        language = _clean_text(payload.get("language"))
        proficiency = _clean_text(payload.get("proficiency"))
        data = {
            "language": language,
            "proficiency": proficiency,
        }
        label = language or "Language"
        source_text = " - ".join([x for x in [language, proficiency] if x]).strip()

    else:
        title = _clean_text(payload.get("title"))
        content = _clean_text(payload.get("content"))
        data = {"title": title, "content": content}
        label = title or "Block"
        source_text = "\n".join([x for x in [title, content] if x]).strip()

    title = label
    content = source_text
    return {
        "label": label,
        "title": title,
        "content": content,
        "data_json": _safe_json_dumps(data),
        "source_text": source_text,
    }


def fetch_cv_content_blocks(conn, section_key=None, language_code=None, active_only=False) -> pd.DataFrame:
    sql = """
        SELECT id, created_at, updated_at, language_code, section_key, label, title, content, data_json, source_text, tags, is_active, sort_order
        FROM cv_content_blocks
        WHERE 1=1
    """
    params = []

    if section_key:
        sql += " AND section_key = ?"
        params.append(section_key)

    if language_code:
        sql += " AND language_code = ?"
        params.append(language_code)

    if active_only:
        sql += " AND is_active = 1"

    sql += " ORDER BY language_code, section_key, sort_order, datetime(updated_at) DESC, id DESC"
    return pd.read_sql_query(sql, conn, params=params)


def get_cv_content_block(conn, block_id):
    cur = conn.execute("""
        SELECT id, created_at, updated_at, language_code, section_key, label, title, content, data_json, source_text, tags, is_active, sort_order
        FROM cv_content_blocks
        WHERE id = ?;
    """, (block_id,))
    row = cur.fetchone()
    if not row:
        return None
    cols = [d[0] for d in cur.description]
    data = dict(zip(cols, row))
    data["payload"] = _safe_json_loads(data.get("data_json") or "{}")
    return data


def save_cv_content_block(
    conn,
    language_code,
    section_key,
    payload,
    tags="",
    is_active=True,
    sort_order=0,
    block_id=None,
):
    now = utc_now()
    language_code = _clean_text(language_code).lower()
    section_key = _clean_text(section_key).lower()
    tags = parse_tags(tags or "")

    if language_code not in ("en", "he"):
        raise ValueError("language_code must be 'en' or 'he'")
    if not section_key:
        raise ValueError("section_key is required")

    normalized = _normalize_block_payload(section_key, payload or {})

    if not normalized["label"] or not normalized["source_text"]:
        raise ValueError("Block is missing required content")

    values = (
        now,
        now,
        language_code,
        section_key,
        normalized["label"],
        normalized["title"],
        normalized["content"],
        normalized["data_json"],
        normalized["source_text"],
        tags,
        1 if is_active else 0,
        int(sort_order or 0),
    )

    if block_id is None:
        cur = conn.execute("""
            INSERT INTO cv_content_blocks
            (created_at, updated_at, language_code, section_key, label, title, content, data_json, source_text, tags, is_active, sort_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, values)
        conn.commit()
        return int(cur.lastrowid)

    conn.execute("""
        UPDATE cv_content_blocks
        SET updated_at = ?,
            language_code = ?,
            section_key = ?,
            label = ?,
            title = ?,
            content = ?,
            data_json = ?,
            source_text = ?,
            tags = ?,
            is_active = ?,
            sort_order = ?
        WHERE id = ?;
    """, (
        now,
        language_code,
        section_key,
        normalized["label"],
        normalized["title"],
        normalized["content"],
        normalized["data_json"],
        normalized["source_text"],
        tags,
        1 if is_active else 0,
        int(sort_order or 0),
        int(block_id),
    ))
    conn.commit()
    return int(block_id)


def delete_cv_content_block(conn, block_id):
    conn.execute("DELETE FROM cv_content_blocks WHERE id = ?;", (block_id,))
    conn.commit()


def build_cv_source_text(conn, block_ids, language_code=None):
    if not block_ids:
        return ""

    ordered_ids = []
    seen = set()
    for x in block_ids:
        try:
            xid = int(x)
        except Exception:
            continue
        if xid not in seen:
            seen.add(xid)
            ordered_ids.append(xid)

    if not ordered_ids:
        return ""

    placeholders = ",".join(["?"] * len(ordered_ids))
    sql = f"""
        SELECT id, language_code, section_key, label, source_text, is_active
        FROM cv_content_blocks
        WHERE id IN ({placeholders})
    """
    params = list(ordered_ids)

    if language_code:
        sql += " AND language_code = ?"
        params.append(_clean_text(language_code).lower())

    rows = conn.execute(sql, params).fetchall()
    if not rows:
        return ""

    by_id = {}
    for r in rows:
        by_id[int(r[0])] = {
            "id": int(r[0]),
            "language_code": _clean_text(r[1]).lower(),
            "section_key": _clean_text(r[2]).lower(),
            "label": _clean_text(r[3]),
            "source_text": _clean_text(r[4]),
            "is_active": int(r[5] or 0),
        }

    ordered_rows = [by_id[x] for x in ordered_ids if x in by_id and int(by_id[x]["is_active"]) == 1 and by_id[x]["source_text"]]
    if not ordered_rows:
        return ""

    out = []
    current_section = None

    for row in ordered_rows:
        section_key = row["section_key"] or "other"
        if section_key != current_section:
            out.append(CV_BLOCK_SECTION_LABELS.get(section_key, section_key.replace("_", " ").title()))
            current_section = section_key
        out.append(row["source_text"])

    return "\n\n".join([x for x in out if _clean_text(x)]).strip()


SECTION_LABELS = {
    "summary": "Summary",
    "experience": "Experience",
    "projects": "Projects",
    "education": "Education",
    "skills": "Skills",
    "languages": "Languages",
}

def _safe_json_loads(value):
    if not value:
        return {}
    try:
        data = json.loads(value)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def _clean_lines(lines):
    return [str(x).strip() for x in lines if str(x or "").strip()]

def render_cv_block_text(section_key: str, data: dict) -> str:
    data = data or {}
    section_key = (section_key or "").strip().lower()

    if section_key == "summary":
        return str(data.get("summary", "")).strip()

    if section_key == "projects":
        header_parts = _clean_lines([
            data.get("project_name", ""),
            data.get("tools", ""),
            data.get("period", "")
        ])
        header = " | ".join(header_parts)

        lines = []
        if header:
            lines.append(header)

        description = str(data.get("description", "")).strip()
        if description:
            lines.append(description)

        github = str(data.get("github_link", "")).strip()
        demo = str(data.get("demo_link", "")).strip()

        if github:
            lines.append(f"GitHub: {github}")
        if demo:
            lines.append(f"Demo: {demo}")

        return "\n".join(_clean_lines(lines))

    if section_key == "experience":
        left = _clean_lines([
            data.get("employer", ""),
            data.get("location", "")
        ])
        left_text = ", ".join(left)

        role = str(data.get("role", "")).strip()
        period_from = str(data.get("start_date", "")).strip()
        period_to = str(data.get("end_date", "")).strip()
        if str(data.get("is_current", "")).strip().lower() in ("1", "true", "yes"):
            period_to = "Present"

        period = " - ".join(_clean_lines([period_from, period_to]))
        header_parts = _clean_lines([
            left_text,
            role if not left_text else (f"{role}" if role else ""),
            period
        ])

        # Avoid ugly double separators
        if left_text and role:
            header = f"{left_text} - {role}"
            if period:
                header = f"{header} | {period}"
        else:
            header = " | ".join(_clean_lines([left_text or role, period]))

        bullets_raw = str(data.get("achievements", "")).replace("\r\n", "\n").strip()
        bullet_lines = []
        for line in bullets_raw.split("\n"):
            line = line.strip()
            if not line:
                continue
            if not line.startswith("-"):
                line = f"- {line.lstrip('-').strip()}"
            bullet_lines.append(line)

        lines = []
        if header:
            lines.append(header)
        lines.extend(bullet_lines)

        return "\n".join(_clean_lines(lines))

    if section_key == "education":
        degree = str(data.get("degree", "")).strip()
        field = str(data.get("field", "")).strip()
        institution = str(data.get("institution", "")).strip()
        location = str(data.get("location", "")).strip()
        start_year = str(data.get("start_year", "")).strip()
        end_year = str(data.get("end_year", "")).strip()
        notes = str(data.get("notes", "")).strip()

        degree_line = " - ".join(_clean_lines([degree, field]))
        place_line = ", ".join(_clean_lines([institution, location]))
        period_line = " - ".join(_clean_lines([start_year, end_year]))

        lines = _clean_lines([degree_line, place_line, period_line, notes])
        return "\n".join(lines)

    if section_key == "skills":
        category = str(data.get("category", "")).strip()
        items = str(data.get("items", "")).strip()
        if category and items:
            return f"{category}: {items}"
        return category or items

    if section_key == "languages":
        language = str(data.get("language", "")).strip()
        proficiency = str(data.get("proficiency", "")).strip()
        if language and proficiency:
            return f"{language}: {proficiency}"
        return language or proficiency

    return str(data.get("content", "")).strip()

def fetch_cv_content_blocks(conn, section_key=None, language_code=None, active_only=False):
    sql = """
        SELECT id, created_at, updated_at, language_code, section_key, title, content, data_json, tags, is_active, sort_order
        FROM cv_content_blocks
        WHERE 1=1
    """
    params = []

    if section_key:
        sql += " AND section_key = ?"
        params.append(section_key)

    if language_code:
        sql += " AND language_code = ?"
        params.append(language_code)

    if active_only:
        sql += " AND is_active = 1"

    sql += " ORDER BY language_code, section_key, sort_order, datetime(updated_at) DESC, id DESC"
    return pd.read_sql_query(sql, conn, params=params)

def get_cv_content_block(conn, block_id):
    cur = conn.execute("""
        SELECT id, created_at, updated_at, language_code, section_key, title, content, data_json, tags, is_active, sort_order
        FROM cv_content_blocks
        WHERE id = ?;
    """, (block_id,))
    row = cur.fetchone()
    if not row:
        return None
    cols = [d[0] for d in cur.description]
    out = dict(zip(cols, row))
    out["data"] = _safe_json_loads(out.get("data_json"))
    return out

def save_cv_content_block(conn, language_code, section_key, title, data, tags="", is_active=True, sort_order=0, block_id=None):
    now = utc_now()
    language_code = (language_code or "").strip().lower()
    section_key = (section_key or "").strip().lower()
    title = (title or "").strip()
    tags = parse_tags(tags or "")
    data = data or {}

    if not language_code:
        raise ValueError("language_code is required")
    if language_code not in ("en", "he"):
        raise ValueError("language_code must be 'en' or 'he'")
    if not section_key:
        raise ValueError("section_key is required")
    if not title:
        raise ValueError("title is required")

    content = render_cv_block_text(section_key, data).strip()
    data_json = json.dumps(data, ensure_ascii=False)

    if not content:
        raise ValueError("Rendered block content is empty")

    if block_id is None:
        cur = conn.execute("""
            INSERT INTO cv_content_blocks
            (created_at, updated_at, language_code, section_key, title, content, data_json, tags, is_active, sort_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            now, now, language_code, section_key, title, content,
            data_json, tags, 1 if is_active else 0, int(sort_order or 0)
        ))
        conn.commit()
        return int(cur.lastrowid)

    conn.execute("""
        UPDATE cv_content_blocks
        SET updated_at = ?,
            language_code = ?,
            section_key = ?,
            title = ?,
            content = ?,
            data_json = ?,
            tags = ?,
            is_active = ?,
            sort_order = ?
        WHERE id = ?;
    """, (
        now, language_code, section_key, title, content,
        data_json, tags, 1 if is_active else 0, int(sort_order or 0), int(block_id)
    ))
    conn.commit()
    return int(block_id)

def delete_cv_content_block(conn, block_id):
    conn.execute("DELETE FROM cv_content_blocks WHERE id = ?;", (block_id,))
    conn.commit()

def build_cv_source_text(conn, block_ids, language_code=None):
    if not block_ids:
        return ""

    ordered_ids = []
    seen = set()
    for x in block_ids:
        try:
            xid = int(x)
        except Exception:
            continue
        if xid not in seen:
            seen.add(xid)
            ordered_ids.append(xid)

    if not ordered_ids:
        return ""

    placeholders = ",".join(["?"] * len(ordered_ids))
    sql = f"""
        SELECT id, language_code, section_key, title, content, data_json, tags, is_active, sort_order
        FROM cv_content_blocks
        WHERE id IN ({placeholders})
    """
    params = list(ordered_ids)

    if language_code:
        sql += " AND language_code = ?"
        params.append((language_code or "").strip().lower())

    rows = conn.execute(sql, params).fetchall()
    if not rows:
        return ""

    by_id = {}
    for r in rows:
        by_id[int(r[0])] = {
            "id": int(r[0]),
            "language_code": str(r[1] or "").strip().lower(),
            "section_key": str(r[2] or "").strip().lower(),
            "title": str(r[3] or "").strip(),
            "content": str(r[4] or "").strip(),
            "data_json": str(r[5] or "").strip(),
            "tags": str(r[6] or "").strip(),
            "is_active": int(r[7] or 0),
            "sort_order": int(r[8] or 0),
        }

    ordered_rows = [by_id[x] for x in ordered_ids if x in by_id and int(by_id[x]["is_active"]) == 1]
    if not ordered_rows:
        return ""

    parts = []
    current_section = None

    for row in ordered_rows:
        sec = row["section_key"] or "other"
        if sec != current_section:
            parts.append(SECTION_LABELS.get(sec, sec.replace("_", " ").title()))
            current_section = sec

        content = str(row.get("content", "")).strip()
        if content:
            parts.append(content)

    return "\n\n".join([x for x in parts if str(x).strip()]).strip()