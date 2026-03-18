import streamlit as st
import pandas as pd
from lib.db import get_conn, init_db, fetch_jobs, STATUS_ORDER, update_status

st.set_page_config(page_title="Kanban", layout="wide")

conn = get_conn()
init_db(conn)
df = fetch_jobs(conn)

st.title("Kanban (simple)")
st.caption("No drag-and-drop. Streamlit isn't that kind of party. But it's still useful.")

if df.empty:
    st.info("No jobs yet.")
    st.stop()

cols = st.columns(len(STATUS_ORDER))
for i, status in enumerate(STATUS_ORDER):
    with cols[i]:
        st.subheader(status)
        subset = df[df["status"] == status].head(20)
        for r in subset.itertuples(index=False):
            st.write(f"#{r.id} {r.company} | {r.role}")
            if st.button("➡ move", key=f"mv_{r.id}_{status}"):
                # move forward in status order
                idx = STATUS_ORDER.index(status)
                new_status = STATUS_ORDER[min(idx+1, len(STATUS_ORDER)-1)]
                update_status(conn, r.id, new_status)
                st.rerun()
