"""
Streamlit Web Dashboard for Email Automation & Reminder System.
Run with: streamlit run dashboard.py
"""
import streamlit as st
import pandas as pd
from pathlib import Path
from src.config import CONTACTS_FILE, REMINDERS_FILE, REPORT_FILE, PREVIEWS_DIR
from src.scheduler import dispatch_batch
from src.data_loader import get_merged_reminder_jobs
from src.templating import render_email_content

st.set_page_config(page_title="Email Automation Hub", page_icon="✉️", layout="wide")

st.title("📧 Email Automation & Reminder System")
st.caption("Industry-grade notification engine, contact manager, and delivery tracker")

tabs = st.tabs(["📊 Overview & Trigger", "👥 Contacts", "⏰ Reminders", "👁️ Live Previews", "📈 Delivery Logs"])

with tabs[0]:
    st.subheader("⚡ Quick Dispatch Console")
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        **Simulation & Safety Notice:**
        By default, the system runs in **Virtual Simulation Mode**. Emails are safely rendered, validated, and saved to disk as HTML previews without triggering your personal or external SMTP accounts.
        """)
        mode = st.radio("Dispatch Mode", ["🟢 Virtual Simulation (Dry-Run)", "🔴 Live SMTP Delivery"], horizontal=True)
        is_dry_run = "Virtual" in mode

        if st.button("🚀 Trigger Notification Batch Now", type="primary"):
            with st.spinner("Processing batch jobs..."):
                results = dispatch_batch(dry_run=is_dry_run)
                st.success(f"Batch completed! Processed {len(results)} notification jobs.")
                st.rerun()

    with col2:
        if REPORT_FILE.exists():
            df_rep = pd.read_csv(REPORT_FILE)
            st.metric("Total Executions Logged", len(df_rep))
            if not df_rep.empty:
                sent_count = (df_rep["status"] == "SIMULATED_SUCCESS").sum() + (df_rep["status"] == "SENT").sum()
                st.metric("Successful / Simulated", sent_count)
                st.metric("Failed", (df_rep["status"] == "FAILED").sum())

with tabs[1]:
    st.subheader("👥 Registered Contacts")
    if CONTACTS_FILE.exists():
        df_c = pd.read_csv(CONTACTS_FILE)
        st.dataframe(df_c, use_container_width=True)
    else:
        st.warning("Contacts file not found.")

with tabs[2]:
    st.subheader("⏰ Scheduled Reminders")
    if REMINDERS_FILE.exists():
        df_r = pd.read_csv(REMINDERS_FILE)
        st.dataframe(df_r, use_container_width=True)
    else:
        st.warning("Reminders file not found.")

with tabs[3]:
    st.subheader("👁️ Live Template Preview")
    jobs = get_merged_reminder_jobs()
    if jobs:
        selected_job_idx = st.selectbox(
            "Select a reminder to preview:",
            range(len(jobs)),
            format_func=lambda i: f"{jobs[i].get('reminder_id')} - {jobs[i].get('title')} ({jobs[i].get('name')})"
        )
        selected_job = jobs[selected_job_idx]
        tmpl = selected_job.get("template_name", "meeting_reminder.html")
        subject, html = render_email_content(tmpl, selected_job)
        
        st.info(f"**Subject Line:** {subject}")
        st.components.v1.html(html, height=500, scrolling=True)

with tabs[4]:
    st.subheader("📈 Execution Audit Report")
    if REPORT_FILE.exists():
        df_rep = pd.read_csv(REPORT_FILE)
        st.dataframe(df_rep.sort_values(by="timestamp", ascending=False), use_container_width=True)
    else:
        st.info("No delivery logs yet. Trigger a batch to see audit records.")
