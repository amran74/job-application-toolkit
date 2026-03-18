import sqlite3
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
