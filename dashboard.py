"""
Unified Streamlit Web Dashboard for Email Automation & Reminder System.
Connected directly to the SQLAlchemy database as the single source of truth.
Run with: python -m streamlit run dashboard.py
"""
import streamlit as st
import pandas as pd
from pathlib import Path

from db.database import SessionLocal
from db.models import Employee, MessageLog, EmailTemplate, ReminderJob, Campaign, CampaignRecipient
from src.services import employee_service, campaign_service, template_service
from api.schemas import EmployeeCreate, CampaignCreate
from src.scheduler import dispatch_batch
from src.data_loader import get_merged_reminder_jobs
from src.templating import render_email_content

st.set_page_config(page_title="Email Automation & HR Hub", page_icon="✉️", layout="wide")

st.title("Workforce Management & Email Automation Hub")
st.caption("Enterprise-grade notification engine, employee directory, and delivery tracker")

tabs = st.tabs([
    "Overview & Dispatch",
    "Employee Management",
    "Campaign Studio",
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


# ----------------- TAB 3: CAMPAIGN STUDIO & TARGETING ----------------- #
with tabs[2]:
    st.subheader("Email Campaign Studio (Unified Database)")
    db = SessionLocal()
    try:
        camp_stats = campaign_service.get_campaign_stats(db)

        # Overview Stats
        ckpi1, ckpi2, ckpi3, ckpi4, ckpi5 = st.columns(5)
        ckpi1.metric("Total Campaigns", camp_stats.total_campaigns)
        ckpi2.metric("Ready to Send", camp_stats.ready_campaigns)
        ckpi3.metric("Drafts", camp_stats.draft_campaigns)
        ckpi4.metric("Scheduled", camp_stats.scheduled_campaigns)
        ckpi5.metric("Targeted Recipients", camp_stats.total_recipients_targeted)

        st.markdown("---")
        c_list_col, c_create_col = st.columns([3, 2])

        with c_list_col:
            st.markdown("**Campaigns Directory**")
            campaigns_list, total_c = campaign_service.list_campaigns(db, limit=100)
            if campaigns_list:
                c_rows = [{
                    "ID": c.id,
                    "Name": c.campaign_name,
                    "Category": c.category,
                    "Template": c.template.template_name if c.template else "None",
                    "Recipients": len(c.recipients),
                    "Status": c.status,
                    "Scheduled": c.scheduled_at.strftime("%Y-%m-%d %H:%M") if c.scheduled_at else "Immediate"
                } for c in campaigns_list]
                st.dataframe(pd.DataFrame(c_rows), use_container_width=True)

                st.markdown("##### Personalized Recipient Preview")
                selected_c_id = st.selectbox(
                    "Choose Campaign to Inspect",
                    [c.id for c in campaigns_list],
                    format_func=lambda cid: next(f"[{c.status}] {c.campaign_name} ({len(c.recipients)} recipients)" for c in campaigns_list if c.id == cid)
                )

                chosen_camp = next((c for c in campaigns_list if c.id == selected_c_id), None)
                if chosen_camp and chosen_camp.recipients:
                    target_emp_id = st.selectbox(
                        "Preview for Recipient",
                        [r.employee_id for r in chosen_camp.recipients],
                        format_func=lambda eid: next(f"{r.employee.full_name} ({r.recipient_email}) - {r.employee.department}" for r in chosen_camp.recipients if r.employee_id == eid)
                    )

                    if target_emp_id:
                        p_res = campaign_service.preview_campaign_for_recipient(db, chosen_camp.id, target_emp_id)
                        if p_res.is_valid:
                            st.success(f"Personalized Subject: **{p_res.rendered_subject}**")
                            c_ptab1, c_ptab2 = st.tabs(["HTML Preview", "Plain-Text Fallback"])
                            with c_ptab1:
                                st.components.v1.html(p_res.rendered_html, height=350, scrolling=True)
                            with c_ptab2:
                                st.text(p_res.plain_text_fallback)
                            st.caption(f"Tags Resolved: `{', '.join(p_res.variables_used) or 'None'}`")
                        else:
                            st.error(f"Render Error: {p_res.validation_error}")
                else:
                    st.info("This campaign currently has no targeted recipients.")
            else:
                st.info("No campaigns created yet. Use the creation form on the right.")

        with c_create_col:
            st.markdown("**Create New Campaign**")
            with st.form("create_campaign_form"):
                new_c_name = st.text_input("Campaign Title *")
                new_c_desc = st.text_area("Description (Optional)", height=70)
                new_c_cat = st.selectbox("Category", [
                    "Technical Training", "Employee Onboarding", "Meeting Invitation",
                    "Training Reminder", "Performance Review", "Webinar Invitation",
                    "General Announcement", "Task Deadline", "Other"
                ])

                templates_avail, _ = template_service.list_templates(db)
                template_options = [(t.id, f"{t.template_name} ({t.category})") for t in templates_avail]
                new_c_tmpl_id = st.selectbox(
                    "Select Template",
                    [opt[0] for opt in template_options] if template_options else [None],
                    format_func=lambda tid: next((opt[1] for opt in template_options if opt[0] == tid), "No Templates Available")
                )

                all_emps, _ = employee_service.list_employees(db, limit=300)
                all_depts = sorted(list(set(e.department for e in all_emps if e.department)))
                target_by_dept = st.multiselect("Quick-Target by Department", all_depts)

                st.caption(f"Or target individual workforce members ({len(all_emps)} available):")
                target_emp_ids = st.multiselect(
                    "Select Individual Employees",
                    [e.id for e in all_emps],
                    format_func=lambda eid: next(f"{e.full_name} ({e.department})" for e in all_emps if e.id == eid)
                )

                campaign_status = st.radio("Initial Status", ["DRAFT", "READY"], horizontal=True)
                submit_campaign = st.form_submit_button("Create Campaign", type="primary")

                if submit_campaign:
                    if not new_c_name.strip():
                        st.error("Campaign Title is required.")
                    else:
                        # Combine department employees + individually selected employees
                        final_emp_ids = set(target_emp_ids)
                        if target_by_dept:
                            dept_emps = [e.id for e in all_emps if e.department in target_by_dept]
                            final_emp_ids.update(dept_emps)

                        camp_in = CampaignCreate(
                            campaign_name=new_c_name.strip(),
                            description=new_c_desc.strip() if new_c_desc.strip() else None,
                            category=new_c_cat,
                            template_id=new_c_tmpl_id,
                            status=campaign_status,
                            employee_ids=list(final_emp_ids)
                        )
                        try:
                            created_c = campaign_service.create_campaign(db, camp_in)
                            st.success(f"Campaign '{created_c.campaign_name}' created with {len(created_c.recipients)} recipients!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error creating campaign: {e}")
    finally:
        db.close()


# ----------------- TAB 4: SCHEDULED REMINDERS ----------------- #
with tabs[3]:
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


# ----------------- TAB 5: TEMPLATE STUDIO & PREVIEWS ----------------- #
with tabs[4]:
    st.subheader("Template Studio & Jinja2 Live Previews (Unified Database)")
    db = SessionLocal()
    try:
        all_templates, t_count = template_service.list_templates(db)
        all_employees, _ = employee_service.list_employees(db, limit=100)

        t_col1, t_col2 = st.columns([1, 1])

        with t_col1:
            st.markdown("**1. Select Template & Recipient Context**")
            if all_templates:
                chosen_template_idx = st.selectbox(
                    "Choose Template",
                    range(len(all_templates)),
                    format_func=lambda i: f"[{all_templates[i].category}] {all_templates[i].template_name}"
                )
                selected_tmpl = all_templates[chosen_template_idx]
            else:
                selected_tmpl = None
                st.warning("No templates found in database.")

            if all_employees:
                chosen_emp_idx = st.selectbox(
                    "Personalize with Employee",
                    range(len(all_employees)),
                    format_func=lambda i: f"{all_employees[i].full_name} ({all_employees[i].employee_id} - {all_employees[i].department})"
                )
                selected_emp = all_employees[chosen_emp_idx]
            else:
                selected_emp = None

        with t_col2:
            st.markdown("**2. Available Personalization Tags**")
            st.caption("Jinja2 Sandboxed: `{{ name }}`, `{{ email }}`, `{{ department }}`, `{{ event_name }}`, `{{ meeting_link }}`")
            if selected_tmpl:
                st.code(f"Subject: {selected_tmpl.subject}\nCategory: {selected_tmpl.category}")

        if selected_tmpl:
            preview_res = template_service.render_template_preview(
                db=db,
                subject_tmpl=selected_tmpl.subject,
                body_tmpl=selected_tmpl.body,
                employee_id=selected_emp.id if selected_emp else None
            )

            st.markdown("---")
            if preview_res.is_valid:
                st.success(f"Rendered Subject: **{preview_res.rendered_subject}**")
                ptab1, ptab2 = st.tabs(["HTML Preview", "Plain-Text Fallback"])
                with ptab1:
                    st.components.v1.html(preview_res.rendered_html, height=450, scrolling=True)
                with ptab2:
                    st.text(preview_res.plain_text_fallback)
            else:
                st.error(f"Validation Error: {preview_res.validation_error}")
    finally:
        db.close()


# ----------------- TAB 6: DELIVERY AUDIT LOGS ----------------- #
with tabs[5]:
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
