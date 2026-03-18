import streamlit as st
import sqlite3
from datetime import datetime, date
import pandas as pd
import matplotlib.pyplot as plt

DB_PATH = "jobs.db"

STATUS_ORDER = ["Interested", "Applied", "Interview", "Offer", "Rejected", "Ghosted"]
CHANNELS = ["LinkedIn", "Company Site", "Referral", "Email", "Recruiter", "Other"]
CV_VERSIONS = ["Data/BI", "Marketing/Analyst", "Ops/Management", "Fraud/Risk", "Custom"]

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
            date_interested TEXT,
            date_applied TEXT,
            date_outcome TEXT,
            last_update TEXT,
            jd_text TEXT,
            notes TEXT
        );
    """)
    # Add columns if older DB exists
    cols = [r[1] for r in conn.execute("PRAGMA table_info(jobs);").fetchall()]
    def add_col(name, ddl):
        if name not in cols:
            conn.execute(f"ALTER TABLE jobs ADD COLUMN {ddl};")
    add_col("cv_version", "cv_version TEXT")
    add_col("date_outcome", "date_outcome TEXT")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company);")
    conn.commit()

def fetch_jobs(conn) -> pd.DataFrame:
    df = pd.read_sql_query("SELECT * FROM jobs ORDER BY datetime(created_at) DESC;", conn)
    if df.empty:
        return df
    for col in ["created_at", "date_interested", "date_applied", "date_outcome", "last_update"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    # Normalize channel nulls
    df["channel"] = df["channel"].fillna("Other")
    df["cv_version"] = df["cv_version"].fillna("Custom")
    return df

def infer_channel(link: str):
    if not link:
        return "Other"
    s = link.lower()
    if "linkedin.com" in s:
        return "LinkedIn"
    if "mail" in s:
        return "Email"
    return "Company Site"

def compute_days_since(dt):
    if dt is None or pd.isna(dt):
        return None
    return (pd.Timestamp(date.today()) - pd.Timestamp(dt.date())).days

def upsert_job(conn, job_id, payload: dict):
    now = utc_now()
    payload = payload.copy()
    payload["last_update"] = now

    cols = [
        "company","role","location","link","channel","status","cv_version",
        "date_interested","date_applied","date_outcome","jd_text","notes","last_update"
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

def update_status(conn, job_id: int, new_status: str):
    now = utc_now()
    # auto dates:
    # - if moving to Applied and date_applied is null -> set today
    # - if moving to outcome status -> set date_outcome today
    row = conn.execute("SELECT date_applied, date_outcome FROM jobs WHERE id=?;", (job_id,)).fetchone()
    date_applied, date_outcome = row if row else (None, None)

    set_applied = None
    set_outcome = None
    today = date.today().isoformat()

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

def update_cv_version(conn, job_id: int, cv_version: str):
    now = utc_now()
    conn.execute("UPDATE jobs SET cv_version=?, last_update=? WHERE id=?;", (cv_version, now, job_id))
    conn.commit()

def delete_job(conn, job_id: int):
    conn.execute("DELETE FROM jobs WHERE id=?;", (job_id,))
    conn.commit()

def metrics(df: pd.DataFrame):
    if df.empty:
        return {}
    total_applied = int(df["status"].isin(["Applied","Interview","Offer","Rejected","Ghosted"]).sum())
    outcomes = df["status"].isin(["Interview","Offer","Rejected","Ghosted"])
    positives = df["status"].isin(["Interview","Offer"])
    interviews = df["status"].isin(["Interview","Offer"]).sum()
    offers = df["status"].eq("Offer").sum()
    ghosts = df["status"].eq("Ghosted").sum()

    # rates guarded
    app_to_interview = (positives.sum()/total_applied)*100 if total_applied else 0
    interview_to_offer = (offers/interviews)*100 if interviews else 0
    ghost_rate = (ghosts/total_applied)*100 if total_applied else 0

    # avg days to outcome
    tmp = df[df["date_applied"].notna() & df["date_outcome"].notna()].copy()
    if not tmp.empty:
        tmp["days_to_outcome"] = (tmp["date_outcome"] - tmp["date_applied"]).dt.days
        avg_days = float(tmp["days_to_outcome"].mean())
    else:
        avg_days = None

    return {
        "total_applied": total_applied,
        "app_to_interview": app_to_interview,
        "interview_to_offer": interview_to_offer,
        "ghost_rate": ghost_rate,
        "avg_days_to_outcome": avg_days
    }

def outcome_breakdown(df: pd.DataFrame, group_col: str, min_count: int = 2):
    if df.empty or group_col not in df.columns:
        return None
    outcomes = df[df["status"].isin(["Interview","Offer","Rejected","Ghosted"])].copy()
    if outcomes.empty:
        return None
    outcomes["is_positive"] = outcomes["status"].isin(["Interview","Offer"]).astype(int)
    g = outcomes.groupby(group_col)["is_positive"].agg(["count","mean"]).reset_index()
    g.rename(columns={"mean":"positive_rate"}, inplace=True)
    g = g[g["count"] >= min_count].sort_values(["positive_rate","count"], ascending=[False, False])
    return g

# ---------------- UI ----------------
st.set_page_config(page_title="Job Tracker", layout="wide")

conn = get_conn()
init_db(conn)
df = fetch_jobs(conn)

st.title("Job Tracker (usable version)")
st.caption("Quick add, one-click status updates, real stats, aging highlights, and correlation by channel/CV version. Humans call this “structure”.")

tab_dash, tab_add, tab_manage, tab_patterns = st.tabs(["Dashboard", "Quick Add", "Manage", "Patterns"])

with tab_dash:
    m = metrics(df)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total applied", m.get("total_applied", 0))
    c2.metric("App → Interview/Offer", f'{m.get("app_to_interview", 0):.1f}%')
    c3.metric("Interview → Offer", f'{m.get("interview_to_offer", 0):.1f}%')
    c4.metric("Ghost rate", f'{m.get("ghost_rate", 0):.1f}%')
    avg = m.get("avg_days_to_outcome", None)
    c5.metric("Avg days to outcome", ("-" if avg is None else f"{avg:.1f}"))

    st.subheader("Jobs")
    if df.empty:
        st.info("No jobs yet. Add one in Quick Add.")
    else:
        view = df.copy()
        # search + filters
        f1, f2, f3, f4 = st.columns([2, 2, 2, 2])
        with f1:
            f_status = st.multiselect("Status", STATUS_ORDER, default=STATUS_ORDER)
        with f2:
            f_channel = st.multiselect("Channel", CHANNELS, default=CHANNELS)
        with f3:
            f_cv = st.multiselect("CV version", CV_VERSIONS, default=CV_VERSIONS)
        with f4:
            q = st.text_input("Search", value="")

        view = view[view["status"].isin(f_status)]
        view = view[view["channel"].isin(f_channel)]
        view = view[view["cv_version"].isin(f_cv)]
        if q.strip():
            s = q.strip().lower()
            view = view[
                view["company"].fillna("").str.lower().str.contains(s) |
                view["role"].fillna("").str.lower().str.contains(s) |
                view["location"].fillna("").str.lower().str.contains(s)
            ]

        # Add aging
        view["days_since_applied"] = view["date_applied"].apply(compute_days_since)
        show_cols = ["id","company","role","location","channel","cv_version","status","date_applied","days_since_applied","link"]
        view_show = view[show_cols].copy()

        def highlight_aging(row):
            d = row.get("days_since_applied")
            if pd.isna(d) or d is None:
                return [""] * len(row)
            if d >= 30:
                return ["background-color: #ffd6d6"] * len(row)
            if d >= 14:
                return ["background-color: #fff2cc"] * len(row)
            return [""] * len(row)

        st.dataframe(
            view_show.style.apply(highlight_aging, axis=1),
            use_container_width=True,
            hide_index=True
        )

        st.caption("Yellow = 14+ days since applied. Red = 30+ days. Translation: follow up or move on.")

        st.subheader("One-click updates")
        # pick an item
        choices = [f'#{r.id} | {r.company} - {r.role}' for r in view.itertuples(index=False)]
        pick = st.selectbox("Pick a job to update quickly", choices)
        job_id = int(pick.split("|")[0].strip().replace("#",""))

        u1, u2, u3 = st.columns([2,2,2])
        with u1:
            new_status = st.selectbox("Set status", STATUS_ORDER, index=STATUS_ORDER.index(df[df["id"]==job_id]["status"].iloc[0]))
            if st.button("Update status"):
                update_status(conn, job_id, new_status)
                st.success("Updated.")
                st.rerun()
        with u2:
            cvv = st.selectbox("Set CV version", CV_VERSIONS, index=CV_VERSIONS.index(df[df["id"]==job_id]["cv_version"].iloc[0]))
            if st.button("Update CV version"):
                update_cv_version(conn, job_id, cvv)
                st.success("Updated.")
                st.rerun()
        with u3:
            if st.button("Mark Applied Today"):
                update_status(conn, job_id, "Applied")
                st.success("Marked as Applied.")
                st.rerun()

        # simple time-series chart
        applied = df[df["date_applied"].notna()].copy()
        if not applied.empty:
            applied["applied_day"] = applied["date_applied"].dt.date
            series = applied.groupby("applied_day").size().sort_index()
            fig = plt.figure()
            plt.plot(series.index, series.values)
            plt.xticks(rotation=45, ha="right")
            plt.title("Applications over time")
            plt.xlabel("Date")
            plt.ylabel("Count")
            st.pyplot(fig, clear_figure=True)

with tab_add:
    st.subheader("Quick Add (fast, so you’ll actually use it)")
    c1, c2, c3 = st.columns(3)
    with c1:
        company = st.text_input("Company*", value="")
        role = st.text_input("Role*", value="")
    with c2:
        link = st.text_input("Link", value="")
        location = st.text_input("Location", value="")
    with c3:
        cv_version = st.selectbox("CV version", CV_VERSIONS, index=0)
        status = st.selectbox("Status", STATUS_ORDER, index=0)

    jd_text = st.text_area("Job description (optional but useful later)", height=160, value="")
    notes = st.text_area("Notes", height=100, value="")

    if st.button("Add job"):
        if not company.strip() or not role.strip():
            st.error("Company and Role are required.")
        else:
            ch = infer_channel(link.strip())
            # If user picked something else, let them override after add from dashboard.
            today = date.today().isoformat()
            date_applied = today if status in ["Applied","Interview","Offer","Rejected","Ghosted"] else None
            date_outcome = today if status in ["Interview","Offer","Rejected","Ghosted"] else None
            payload = {
                "company": company.strip(),
                "role": role.strip(),
                "location": location.strip() or None,
                "link": link.strip() or None,
                "channel": ch,
                "status": status,
                "cv_version": cv_version,
                "date_interested": today,
                "date_applied": date_applied,
                "date_outcome": date_outcome,
                "jd_text": jd_text.strip() or None,
                "notes": notes.strip() or None,
            }
            upsert_job(conn, None, payload)
            st.success("Added.")
            st.rerun()

with tab_manage:
    st.subheader("Manage")
    if df.empty:
        st.info("Nothing yet.")
    else:
        st.download_button(
            "Export CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="jobs_export.csv",
            mime="text/csv"
        )
        del_choice = st.selectbox("Select job to delete", [f'#{r.id} | {r.company} - {r.role}' for r in df.itertuples(index=False)])
        if st.button("Delete selected"):
            del_id = int(del_choice.split("|")[0].strip().replace("#",""))
            delete_job(conn, del_id)
            st.warning("Deleted.")
            st.rerun()

with tab_patterns:
    st.subheader("Patterns you can actually use")
    if df.empty:
        st.info("No data.")
    else:
        st.markdown("Channel performance (Interview/Offer vs Rejected/Ghosted)")
        by_channel = outcome_breakdown(df, "channel", min_count=2)
        if by_channel is None or by_channel.empty:
            st.write("Not enough outcomes yet.")
        else:
            st.dataframe(by_channel, use_container_width=True, hide_index=True)

        st.markdown("CV version performance")
        by_cv = outcome_breakdown(df, "cv_version", min_count=2)
        if by_cv is None or by_cv.empty:
            st.write("Not enough outcomes yet.")
        else:
            st.dataframe(by_cv, use_container_width=True, hide_index=True)

        st.markdown("Company performance (needs 2+ outcomes per company)")
        by_company = outcome_breakdown(df, "company", min_count=2)
        if by_company is None or by_company.empty:
            st.write("Not enough outcomes yet.")
        else:
            st.dataframe(by_company, use_container_width=True, hide_index=True)

st.divider()
st.caption("Next upgrade: AI CV tailoring + PDF export. First we make sure you actually log jobs consistently, because pattern recognition needs data, not dreams.")
