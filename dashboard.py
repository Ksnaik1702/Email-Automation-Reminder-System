"""
Unified Streamlit Web Dashboard for Email Automation & Reminder System.
Connected directly to the SQLAlchemy database as the single source of truth.
Run with: python -m streamlit run dashboard.py
"""
import streamlit as st
import pandas as pd
from pathlib import Path

from db.database import SessionLocal
from db.models import Employee, MessageLog, EmailTemplate, ReminderJob
from src.services import employee_service
from api.schemas import EmployeeCreate
from src.scheduler import dispatch_batch
from src.data_loader import get_merged_reminder_jobs
from src.templating import render_email_content

st.set_page_config(page_title="Email Automation & HR Hub", page_icon="✉️", layout="wide")

st.title("Workforce Management & Email Automation Hub")
st.caption("Enterprise-grade notification engine, employee directory, and delivery tracker")

tabs = st.tabs([
    "Overview & Dispatch",
    "Employee Management",
    "Scheduled Reminders",
    "Template Previews",
    "Delivery Audit Logs"
])

# ----------------- TAB 1: OVERVIEW & DISPATCH ----------------- #
with tabs[0]:
    st.subheader("Automated Notification Dispatch Console")
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("""
        **Simulation & Safety Control:**
        By default, the system runs in **Virtual Simulation Mode**. Emails are safely rendered, validated, and saved to disk as HTML previews without triggering live SMTP servers.
        """)
        mode = st.radio("Dispatch Mode", ["Virtual Simulation (Dry-Run)", "Live SMTP Delivery"], horizontal=True)
        is_dry_run = "Virtual" in mode

        if st.button("Trigger Notification Batch Now", type="primary"):
            with st.spinner("Processing batch jobs..."):
                results = dispatch_batch(dry_run=is_dry_run)
                st.success(f"Batch completed! Processed {len(results)} notification jobs.")
                st.rerun()

    with col2:
        db = SessionLocal()
        try:
            total_logs = db.query(MessageLog).count()
            sent_count = db.query(MessageLog).filter(MessageLog.execution_status.in_(["SENT", "SIMULATED_SUCCESS"])).count()
            failed_count = db.query(MessageLog).filter(MessageLog.execution_status == "FAILED").count()

            st.metric("Total Executions Recorded", total_logs)
            st.metric("Successful / Simulated", sent_count)
            st.metric("Failed", failed_count)
        finally:
            db.close()


# ----------------- TAB 2: EMPLOYEE MANAGEMENT ----------------- #
with tabs[1]:
    st.subheader("Corporate Employee Directory (Unified Database)")
    db = SessionLocal()
    try:
        stats = employee_service.get_employee_stats(db)

        # Overview Stats
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Total Employees", stats["total_employees"])
        kpi2.metric("Active Employees", stats["active_employees"])
        kpi3.metric("Inactive / Leave", stats["inactive_employees"])
        kpi4.metric("Departments", stats["departments_count"])

        # Filters
        st.markdown("---")
        fcol1, fcol2, fcol3 = st.columns([3, 2, 2])
        search_query = fcol1.text_input("Search Workforce", placeholder="Search by name, ID, or email...")
        departments = ["All"] + sorted(list(stats["department_distribution"].keys()))
        selected_dept = fcol2.selectbox("Filter Department", departments)
        selected_status = fcol3.selectbox("Filter Status", ["All", "Active", "Inactive", "On Leave", "Terminated"])

        # Action Buttons
        act_col1, act_col2 = st.columns([1, 1])
        with act_col1:
            csv_export_data = employee_service.export_employees_to_csv(
                db,
                search=search_query if search_query else None,
                department=selected_dept if selected_dept != "All" else None
            )
            st.download_button(
                label="Download Filtered Employees (CSV)",
                data=csv_export_data,
                file_name="employees_export.csv",
                mime="text/csv"
            )

        # Employee Data Table
        employees, total_found = employee_service.list_employees(
            db,
            search=search_query if search_query else None,
            department=selected_dept if selected_dept != "All" else None,
            status=selected_status if selected_status != "All" else None,
            limit=200
        )

        if employees:
            data_rows = [{
                "Code": e.employee_id,
                "Full Name": e.full_name,
                "Email": e.email,
                "Department": e.department,
                "Designation": e.designation,
                "Timezone": e.timezone,
                "Status": e.employment_status,
                "Created": e.created_at.strftime("%Y-%m-%d") if e.created_at else ""
            } for e in employees]
            st.dataframe(pd.DataFrame(data_rows), use_container_width=True)
            st.caption(f"Displaying {len(employees)} of {total_found} matching records.")
        else:
            st.info("No employee records found matching your filter criteria.")

        # Sub-sections: Add and Import
        st.markdown("---")
        exp1, exp2 = st.columns(2)

        with exp1:
            with st.expander("Add New Employee", expanded=False):
                with st.form("add_employee_form"):
                    new_code = st.text_input("Employee Code *", placeholder="e.g. EMP-201")
                    new_name = st.text_input("Full Name *", placeholder="e.g. Rajesh Kumar")
                    new_email = st.text_input("Corporate Email *", placeholder="rajesh@company.com")
                    new_dept = st.text_input("Department", value="Operations")
                    new_role = st.text_input("Designation", value="Analyst")
                    new_tz = st.text_input("Timezone", value="Asia/Kolkata")
                    new_status = st.selectbox("Status", ["Active", "Inactive", "On Leave"])

                    if st.form_submit_button("Create Employee", type="primary"):
                        if not new_code or not new_name or not new_email:
                            st.error("Employee Code, Full Name, and Email are required.")
                        else:
                            try:
                                emp_payload = EmployeeCreate(
                                    employee_id=new_code,
                                    full_name=new_name,
                                    email=new_email,
                                    department=new_dept,
                                    designation=new_role,
                                    timezone=new_tz,
                                    employment_status=new_status
                                )
                                employee_service.create_employee(db, emp_payload)
                                st.success(f"Employee {new_name} added to database successfully!")
                                st.rerun()
                            except Exception as ex:
                                st.error(f"Error: {ex}")

        with exp2:
            with st.expander("Bulk Ingest via CSV", expanded=False):
                uploaded_csv = st.file_uploader("Upload CSV File", type=["csv"])
                if uploaded_csv is not None:
                    if st.button("Process & Import CSV"):
                        with st.spinner("Validating and importing records..."):
                            summary = employee_service.import_employees_from_csv(db, uploaded_csv.getvalue())
                            st.write(f"Total Rows: **{summary.total_rows}**")
                            st.write(f"Successfully Imported: :green[**{summary.successfully_imported}**]")
                            st.write(f"Skipped (Duplicates): :orange[**{summary.skipped_records}**]")
                            st.write(f"Failed: :red[**{summary.failed_records}**]")
                            if summary.errors:
                                st.warning("Detailed Diagnostics:")
                                for err in summary.errors:
                                    st.write(f"- Row {err.row_number} [{err.employee_id}]: {err.reason}")
                            st.rerun()

    finally:
        db.close()


# ----------------- TAB 3: SCHEDULED REMINDERS ----------------- #
with tabs[2]:
    st.subheader("Active Reminder Jobs")
    db = SessionLocal()
    try:
        reminders = db.query(ReminderJob).all()
        if reminders:
            rem_rows = [{
                "Title": r.reminder_title,
                "Employee": r.employee.full_name if r.employee else "N/A",
                "Email": r.employee.email if r.employee else "N/A",
                "Scheduled (UTC)": r.scheduled_at.strftime("%Y-%m-%d %H:%M") if r.scheduled_at else "",
                "Recurrence": r.recurrence_type,
                "Status": r.status
            } for r in reminders]
            st.dataframe(pd.DataFrame(rem_rows), use_container_width=True)
        else:
            st.info("No active reminder jobs in database.")
    finally:
        db.close()


# ----------------- TAB 4: TEMPLATE PREVIEWS ----------------- #
with tabs[3]:
    st.subheader("Live Notification Template Previews")
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

        st.info(f"Subject: {subject}")
        st.components.v1.html(html, height=500, scrolling=True)


# ----------------- TAB 5: DELIVERY AUDIT LOGS ----------------- #
with tabs[4]:
    st.subheader("Unified Execution & Delivery Audit Log")
    db = SessionLocal()
    try:
        logs = db.query(MessageLog).order_by(MessageLog.executed_at.desc()).limit(100).all()
        if logs:
            log_data = [{
                "Timestamp (UTC)": l.executed_at.strftime("%Y-%m-%d %H:%M:%S") if l.executed_at else "",
                "Recipient": l.recipient_email,
                "Subject": l.subject,
                "Status": l.execution_status,
                "Idempotency Key": l.execution_key,
                "Error": l.error_message or "None"
            } for l in logs]
            st.dataframe(pd.DataFrame(log_data), use_container_width=True)
        else:
            st.info("No message logs recorded yet. Trigger a batch to see live records.")
    finally:
        db.close()
