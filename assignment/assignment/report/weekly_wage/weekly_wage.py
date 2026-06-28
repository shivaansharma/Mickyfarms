# Copyright (c) 2026, shivaan and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate
import re

def execute(filters=None):
    filters = filters or {}

    if filters.get("employee"):
        columns = get_detail_columns()
        data = get_detail_data(filters)
        
        # Calculate summary values for a Single Employee Statement
        emp_id = filters.get("employee")
        company_abbr = get_company_abbr()
        live_bal = get_current_balances(emp_id, company_abbr)
        
        total_wages_owed = live_bal["outstanding_balance"]
        total_advance = live_bal["advance_owed"]
        net_position = total_wages_owed - total_advance
        
        report_summary = [
            {
                "value": total_wages_owed,
                "label": _("Wages Owed (We Owe Them)"),
                "datatype": "Currency",
                "indicator": "Red" if total_wages_owed > 0 else "Green"
            },
            {
                "value": total_advance,
                "label": _("Advance Balance (They Owe Us)"),
                "datatype": "Currency",
                "indicator": "Green" if total_advance > 0 else "Grey"
            },
            {
                "value": net_position,
                "label": _("Net Position"),
                "datatype": "Currency",
                "indicator": "Red" if net_position > 0 else "Green"
            }
        ]
    else:
        columns = get_summary_columns()
        data = get_summary_data(filters)
        
        # Calculate summary values for Global Farm Overview
        total_advance = 0.0
        total_wages_owed = 0.0
        for row in data:
            if row.get("employee"):  # Skip total row aggregation loop
                total_advance += flt(row.get("latest_advance_owed"))
                total_wages_owed += flt(row.get("outstanding_balance"))
                
        net_position = total_wages_owed - total_advance
        
        report_summary = [
            {
                "value": total_wages_owed,
                "label": _("Total Wages Owed (We Owe Them)"),
                "datatype": "Currency",
                "indicator": "Red" if total_wages_owed > 0 else "Green"
            },
            {
                "value": total_advance,
                "label": _("Total Advances (They Owe Us)"),
                "datatype": "Currency",
                "indicator": "Green" if total_advance > 0 else "Grey"
            },
            {
                "value": net_position,
                "label": _("Net Owed Position"),
                "datatype": "Currency",
                "indicator": "Red" if net_position > 0 else "Green"
            }
        ]

    return columns, data, None, None, report_summary


def get_company_abbr():
    company = frappe.defaults.get_user_default("Company") or "Micky Farms"
    return frappe.get_cached_value("Company", company, "abbr")


def get_current_balances(employee, company_abbr):
    """Fetches real-time live balance totals straight from the General Ledger and nets them."""
    advance_balance = frappe.db.sql("""
        SELECT SUM(debit - credit)
        FROM `tabGL Entry`
        WHERE
            party = %s
            AND account = %s
            AND docstatus = 1
            AND is_cancelled = 0
    """, (employee, f"Employee Advances - {company_abbr}"))[0][0] or 0

    payable_balance = frappe.db.sql("""
        SELECT SUM(credit - debit)
        FROM `tabGL Entry`
        WHERE
            party = %s
            AND account = %s
            AND docstatus = 1
            AND is_cancelled = 0
    """, (employee, f"Salary Payable - {company_abbr}"))[0][0] or 0

    adv = flt(advance_balance) if advance_balance > 0 else 0.0
    pay = flt(payable_balance) if payable_balance > 0 else 0.0

    # Netting logic to prevent both showing simultaneously
    if adv > 0 and pay > 0:
        if adv >= pay:
            adv = adv - pay
            pay = 0.0
        else:
            pay = pay - adv
            adv = 0.0

    return {
        "advance_owed": adv,
        "outstanding_balance": pay,
    }


# ===============================================================
# DETAIL MODE (Chronological Statement Ledger for One Employee)
# ===============================================================
def get_detail_columns():
    return [
        {"label": _("Date"),        "fieldname": "payment_date", "fieldtype": "Date",         "width": 110},
        {"label": _("Description"), "fieldname": "tx_type",      "fieldtype": "Data",         "width": 240},
        {
            "label": _("Reference No"),
            "fieldname": "voucher_no",
            "fieldtype": "Dynamic Link",
            "options": "voucher_type",
            "width": 140,
        },
        {"label": _("Days Worked"),                    "fieldname": "days_worked",      "fieldtype": "Float",    "width": 100},
        {"label": _("Wages Earned"),                   "fieldname": "wages_earned",     "fieldtype": "Currency", "width": 130},
        {"label": _("Cash Paid Out"),                  "fieldname": "cash_paid_out",    "fieldtype": "Currency", "width": 130},
        {"label": _("Advance Balance (Their Debt)"),   "fieldname": "running_advance",  "fieldtype": "Currency", "width": 190},
        {"label": _("Wages Owed Balance (Our Debt)"),  "fieldname": "running_payable",  "fieldtype": "Currency", "width": 190},
        {"label": _("Net Position (+ve = they owe you)"), "fieldname": "net_balance", "fieldtype": "Currency", "width": 210},
       
    ]


def get_weekly_wage_voucher_nos():
    wage_names = frappe.db.sql(
        "SELECT name FROM `tabWeekly Wage Payment` WHERE docstatus = 1",
        as_dict=0
    )
    excluded = {r[0] for r in wage_names}

    if excluded:
        like_clauses = " OR ".join(["remarks LIKE %s"] * len(excluded))
        params = [f"%{name}%" for name in excluded]
        linked = frappe.db.sql(
            f"SELECT DISTINCT voucher_no FROM `tabGL Entry` "
            f"WHERE docstatus = 1 AND ({like_clauses})",
            params, as_dict=0
        )
        excluded |= {r[0] for r in linked}

    return excluded

def get_detail_data(filters):
    company_abbr = get_company_abbr()
    emp_id = filters.get("employee")

    wage_conditions = ["parent.docstatus = 1", "child.employee = %(employee)s"]
    wage_params = {"employee": emp_id}

    if filters.get("from_date") and filters.get("to_date"):
        wage_conditions.append("parent.to_date BETWEEN %(from_date)s AND %(to_date)s")
        wage_params["from_date"] = filters.get("from_date")
        wage_params["to_date"] = filters.get("to_date")

    wage_rows = frappe.db.sql(f"""
        SELECT
            parent.to_date               AS payment_date,
            'Weekly Wage Payment'        AS voucher_type,
            parent.name                  AS voucher_no,
            child.days_worked            AS days_worked,
            child.payment                AS wages_earned,
            child.final_net_payout       AS cash_paid_out,
            child.advance_deduction      AS advance_deducted,
            'Wages Calculated (Attendance)' AS tx_type
        FROM `tabWeekly Wage Line Item` child
        JOIN `tabWeekly Wage Payment` parent ON child.parent = parent.name
        WHERE {" AND ".join(wage_conditions)}
    """, wage_params, as_dict=1)

    excluded_vouchers = get_weekly_wage_voucher_nos()

    gl_conditions = [
        "gle.party = %(employee)s",
        "gle.docstatus = 1",
        "gle.is_cancelled = 0",
    ]
    gl_params = {"employee": emp_id}

    if filters.get("from_date") and filters.get("to_date"):
        gl_conditions.append("gle.posting_date BETWEEN %(from_date)s AND %(to_date)s")
        gl_params["from_date"] = filters.get("from_date")
        gl_params["to_date"] = filters.get("to_date")

    standalone_gl = frappe.db.sql(f"""
        SELECT
            gle.posting_date  AS payment_date,
            gle.voucher_type  AS voucher_type,
            gle.voucher_no    AS voucher_no,
            gle.account       AS account,
            gle.debit         AS debit,
            gle.credit         AS credit,
            je.remark         AS je_remark
        FROM `tabGL Entry` gle
        LEFT JOIN `tabJournal Entry` je ON gle.voucher_no = je.name AND gle.voucher_type = 'Journal Entry'
        WHERE {" AND ".join(gl_conditions)}
    """, gl_params, as_dict=1)

    standalone_gl = [e for e in standalone_gl if e["voucher_no"] not in excluded_vouchers]

    advance_account = f"Employee Advances - {company_abbr}"
    payable_account = f"Salary Payable - {company_abbr}"

    raw_timeline = []
    auto_jv_groups = {}
    seen_cash_payments = {}

    for w in wage_rows:
        raw_timeline.append({
            "payment_date":  w["payment_date"],
            "voucher_type":  w["voucher_type"],
            "voucher_no":    w["voucher_no"],
            "days_worked":   flt(w["days_worked"]),
            "wages_earned":  flt(w["wages_earned"]),
            "cash_paid_out": flt(w["cash_paid_out"]),
            "tx_type":       w["tx_type"],
            "delta_advance": -flt(w["advance_deducted"]),
            "delta_payable": flt(w["wages_earned"]) - flt(w["cash_paid_out"]),
            "signature" : ""
        })

    for entry in standalone_gl:
        account = entry["account"]
        debit   = flt(entry["debit"])
        credit  = flt(entry["credit"])
        key     = entry["voucher_no"]
        remark  = entry["je_remark"] or ""
        if "Auto attendance processing" in remark or "Retroactive attendance clawback" in remark:
            if key not in auto_jv_groups:
                # Extract days and rate via regex from the automated remark string
                days_match = re.search(r"Net\s+(-?[\d.]+)\s+days", remark)
                rate_match = re.search(r"₹\s*([\d.]+)/day", remark)
                
                extracted_days = flt(days_match.group(1)) if days_match else 0.0
                extracted_rate = flt(rate_match.group(1)) if rate_match else 0.0
                
                display_label = f"Automated Attendance Adjustment"
                if extracted_rate > 0:
                    display_label += f" (₹{extracted_rate}/day)"

                auto_jv_groups[key] = {
                    "payment_date":  entry["payment_date"],
                    "voucher_type":  entry["voucher_type"],
                    "voucher_no":    key,
                    "days_worked":   extracted_days,
                    "wages_earned":  0.0,
                    "cash_paid_out": 0.0,
                    "delta_advance": 0.0,
                    "delta_payable": 0.0,
                    "tx_type":       display_label,
                    "signature":     ""
                }
            
            if advance_account in account:
                auto_jv_groups[key]["delta_advance"] += (debit - credit)
            elif payable_account in account:
                auto_jv_groups[key]["delta_payable"] += (credit - debit)
                if credit > 0:
                    auto_jv_groups[key]["wages_earned"] += credit
            continue

        row = {
            "payment_date":  entry["payment_date"],
            "voucher_type":  entry["voucher_type"],
            "voucher_no":    entry["voucher_no"],
            "days_worked":   0.0,
            "wages_earned":  0.0,
            "cash_paid_out": 0.0,
            "delta_advance": 0.0,
            "delta_payable": 0.0,
            "tx_type":       "",
            "signature":     ""  
        }

        if advance_account in account:
            if debit > 0:
                row["tx_type"]       = "Advance Given to Employee"
                row["cash_paid_out"] = debit
                row["delta_advance"] = debit
            elif credit > 0:
                row["tx_type"]       = "Advance Returned by Employee"
                row["cash_paid_out"] = -credit
                row["delta_advance"] = -credit
            raw_timeline.append(row)

        elif payable_account in account:
            if debit > 0:
                row["tx_type"]       = "Wages Paid Out"
                row["cash_paid_out"] = debit
                row["delta_payable"] = -debit
            elif credit > 0:
                row["tx_type"]       = "Wages Earned"
                row["wages_earned"]  = credit
                row["delta_payable"] = credit
            raw_timeline.append(row)

        elif credit > 0 and entry["voucher_type"] in ("Payment Entry", "Journal Entry"):
            if key in seen_cash_payments:
                continue
            seen_cash_payments[key] = True
            row["tx_type"]       = "Direct Cash / Bank Payment"
            row["cash_paid_out"] = credit
            row["delta_payable"] = -credit
            raw_timeline.append(row)

    for jv_row in auto_jv_groups.values():
        raw_timeline.append(jv_row)

    raw_timeline.sort(key=lambda x: x["payment_date"] or getdate("1970-01-01"))

    current_running_advance = 0.0
    current_running_payable = 0.0
    total_days   = 0.0
    total_earned = 0.0
    total_paid   = 0.0

    for item in raw_timeline:
        current_running_advance += item["delta_advance"]
        current_running_payable += item["delta_payable"]

        if current_running_advance > 0 and current_running_payable > 0:
            net = current_running_advance - current_running_payable
            if net >= 0:
                current_running_advance = net
                current_running_payable = 0.0
            else:
                current_running_advance = 0.0
                current_running_payable = -net

        item["running_advance"] = current_running_advance
        item["running_payable"] = current_running_payable
        item["net_balance"] = current_running_advance - current_running_payable
        total_days   += item["days_worked"]
        total_earned += item["wages_earned"]
        total_paid   += item["cash_paid_out"]

    raw_timeline.reverse()

    live_bal = get_current_balances(emp_id, company_abbr)

    if not raw_timeline:
        raw_timeline.append({
            "payment_date":    None,
            "tx_type":         "<b>No transactional history found</b>",
            "voucher_type":    "",
            "voucher_no":      "",
            "days_worked":     0.0,
            "wages_earned":    0.0,
            "cash_paid_out":   0.0,
            "running_advance": live_bal["advance_owed"],
            "running_payable": live_bal["outstanding_balance"],
            "net_balance": live_bal["advance_owed"] - live_bal["outstanding_balance"],
            "signature":     ""  
        })
    else:
        raw_timeline.append({
            "payment_date":    "",
            "tx_type":         "<b>LIVE ACCOUNT TOTALS</b>",
            "voucher_type":    "",
            "voucher_no":      "",
            "days_worked":     total_days,
            "wages_earned":    total_earned,
            "cash_paid_out":   total_paid,
            "running_advance": live_bal["advance_owed"],
            "running_payable": live_bal["outstanding_balance"],
            "net_balance": live_bal["advance_owed"] - live_bal["outstanding_balance"],
            "signature":     ""  
        })

    return raw_timeline
# ===============================================================
# SUMMARY MODE (Clean, Consolidated Overview - One Row Per Person)
# ===============================================================
def get_summary_columns():
    return [
        {"label": _("Employee ID"),                   "fieldname": "employee",            "fieldtype": "Link",     "options": "Employee", "width": 140},
        {"label": _("Employee Name"),                 "fieldname": "employee_name",       "fieldtype": "Data",     "width": 160},
        {"label": _("Last Attendance Entry"),         "fieldname": "last_payment_date",   "fieldtype": "Date",     "width": 140},
        {"label": _("Total Days Worked"),             "fieldname": "total_days_worked",   "fieldtype": "Float",    "width": 130},
        {"label": _("Calculated Wages"),              "fieldname": "total_payment",       "fieldtype": "Currency", "width": 140},
        {"label": _("Total Cash Distributed"),        "fieldname": "total_net_payout",    "fieldtype": "Currency", "width": 150},
        {"label": _("Current Advance Balance (Live)"), "fieldname": "latest_advance_owed", "fieldtype": "Currency", "width": 200},
        {"label": _("Current Wages Owed (Live)"),     "fieldname": "outstanding_balance", "fieldtype": "Currency", "width": 200},
        {"label": _("Signature"),                      "fieldname": "signature",           "fieldtype": "Data",     "width": 150 },
    ]


def get_summary_data(filters):
    company_abbr = get_company_abbr()
    conditions = ["parent.docstatus = 1"]
    params = {}

    is_date_filtered = False
    if filters.get("from_date") and filters.get("to_date"):
        conditions.append("parent.to_date BETWEEN %(from_date)s AND %(to_date)s")
        params["from_date"] = filters.get("from_date")
        params["to_date"] = filters.get("to_date")
        is_date_filtered = True

    wage_records = frappe.db.sql(f"""
        SELECT
            child.employee,
            child.employee_name,
            MAX(parent.to_date)          AS last_payment_date,
            SUM(child.days_worked)       AS total_days_worked,
            SUM(child.payment)           AS total_payment,
            SUM(child.final_net_payout)  AS total_net_payout
        FROM `tabWeekly Wage Line Item` child
        JOIN `tabWeekly Wage Payment` parent ON child.parent = parent.name
        WHERE {" AND ".join(conditions)}
        GROUP BY child.employee, child.employee_name
    """, params, as_dict=1)

    report_data       = []
    balance_cache     = {}
    tracked_employees = set()

    for r in wage_records:
        emp = r["employee"]
        tracked_employees.add(emp)
        if emp not in balance_cache:
            balance_cache[emp] = get_current_balances(emp, company_abbr)

        report_data.append({
            "employee":            emp,
            "employee_name":       r["employee_name"],
            "last_payment_date":   r["last_payment_date"],
            "total_days_worked":   flt(r["total_days_worked"]),
            "total_payment":       flt(r["total_payment"]),
            "total_net_payout":    flt(r["total_net_payout"]),
            "latest_advance_owed": balance_cache[emp]["advance_owed"],
            "outstanding_balance": balance_cache[emp]["outstanding_balance"],
        })

    if not is_date_filtered:
        all_active = frappe.get_all("Employee", filters={"status": "Active"}, fields=["name", "employee_name"])
        for emp in all_active:
            if emp.name not in tracked_employees:
                if emp.name not in balance_cache:
                    balance_cache[emp.name] = get_current_balances(emp.name, company_abbr)
                report_data.append({
                    "employee":            emp.name,
                    "employee_name":       emp.employee_name,
                    "last_payment_date":   None,
                    "total_days_worked":   0.0,
                    "total_payment":       0.0,
                    "total_net_payout":    0.0,
                    "latest_advance_owed": balance_cache[emp.name]["advance_owed"],
                    "outstanding_balance": balance_cache[emp.name]["outstanding_balance"],
                })

    report_data.sort(key=lambda x: (x["employee_name"] or ""))

    if report_data:
        total_days        = sum(r["total_days_worked"] for r in report_data)
        total_payment     = sum(r["total_payment"] for r in report_data)
        total_net         = sum(r["total_net_payout"] for r in report_data)
        total_advance     = sum(b["advance_owed"] for b in balance_cache.values())
        total_outstanding = sum(b["outstanding_balance"] for b in balance_cache.values())

        report_data.append({
            "employee":            "",
            "employee_name":       "<b>MICKY FARM TOTALS</b>",
            "last_payment_date":   "",
            "total_days_worked":   total_days,
            "total_payment":       total_payment,
            "total_net_payout":    total_net,
            "latest_advance_owed": total_advance,
            "outstanding_balance": total_outstanding,
        })

    return report_data


# ===============================================================
# PROCESS UNRECORDED ATTENDANCE — automatically handles retro edits
# ===============================================================
def cancel_previous_auto_entries(employee):
    previous_entries = frappe.db.sql("""
        SELECT DISTINCT je.name
        FROM `tabJournal Entry` je
        JOIN `tabJournal Entry Account` jea ON jea.parent = je.name
        WHERE jea.party = %s 
          AND jea.party_type = 'Employee'
          AND je.docstatus = 1
          AND (je.remark LIKE 'Auto attendance processing%%' OR je.remark LIKE 'Retroactive attendance clawback%%')
    """, (employee,), as_dict=0)

    for row in previous_entries:
        je_name = row[0]

        # ── Clear the backlinks FIRST before Frappe checks dependencies ──
        frappe.db.sql("""
            UPDATE `tabAttendance`
            SET custom_processed_in_je = NULL
            WHERE custom_processed_in_je = %s
        """, (je_name,))
        frappe.db.commit()

        # Now Frappe won't find any linked Attendance records
        je_doc = frappe.get_doc("Journal Entry", je_name)
        je_doc.cancel()

@frappe.whitelist()
def process_unrecorded_attendance(employee=None):
    from frappe.utils import add_days, nowdate

    company      = frappe.defaults.get_user_default("Company") or "Micky Farms"
    company_abbr = frappe.get_cached_value("Company", company, "abbr")
    cost_center  = f"Main - {company_abbr}"

    salary_expense  = f"Salary - {company_abbr}"
    salary_payable  = f"Salary Payable - {company_abbr}"
    advance_account = f"Employee Advances - {company_abbr}"

    filters = {"status": "Active", "company": company}
    if employee:
        filters["name"] = employee

    employees = frappe.get_all(
        "Employee",
        filters=filters,
        fields=["name", "employee_name", "custom_daily_wage_rate"]
    )

    processed = []
    skipped   = []
    to_date   = nowdate()

    for emp in employees:
        daily_rate = flt(emp.custom_daily_wage_rate)
        if not daily_rate:
            skipped.append(f"{emp.employee_name} (no daily wage rate set)")
            continue

        # Cancel any previous automated run entries first to prevent double booking
        cancel_previous_auto_entries(emp.name)

        last_record = frappe.db.sql("""
            SELECT MAX(wwp.to_date)
            FROM `tabWeekly Wage Payment` wwp
            JOIN `tabWeekly Wage Line Item` wwli ON wwp.name = wwli.parent
            WHERE wwp.docstatus = 1
              AND wwli.employee = %s
              AND wwli.days_worked > 0
        """, (emp.name,))

        last_date = last_record[0][0] if last_record and last_record[0][0] else None
        advance_deduction = 0.0

        if last_date:
            # Look back 60 days to capture any retroactive manual edits
            lookback_start = add_days(last_date, -60)

            # 1. Calculate how many days are approved in live attendance records for this window
            attendance_records = frappe.get_all(
                "Attendance",
                filters={
                    "employee": emp.name,
                    "attendance_date": ["between", [lookback_start, to_date]],
                    "docstatus": 1,
                    "status": ["in", ["Present", "Half Day"]]
                },
                fields=["status"]
            )
            total_attendance_days = sum(1 if a.status == "Present" else 0.5 for a in attendance_records)

            # 2. See how many days we already paid them for within this same sliding window
            already_paid_days = frappe.db.sql("""
                SELECT SUM(child.days_worked)
                FROM `tabWeekly Wage Line Item` child
                JOIN `tabWeekly Wage Payment` parent ON child.parent = parent.name
                WHERE parent.docstatus = 1
                  AND child.employee = %s
                  AND parent.to_date BETWEEN %s AND %s
            """, (emp.name, lookback_start, to_date))[0][0] or 0.0

            total_days = flt(total_attendance_days) - flt(already_paid_days)
            from_date = add_days(last_date, 1)
        else:
            from_date = frappe.db.sql(
                "SELECT MIN(attendance_date) FROM `tabAttendance` WHERE employee=%s AND docstatus=1",
                emp.name
            )[0][0]

            if not from_date:
                skipped.append(f"{emp.employee_name} (no attendance found)")
                continue

            attendance_records = frappe.get_all(
                "Attendance",
                filters={
                    "employee": emp.name,
                    "attendance_date": ["between", [from_date, to_date]],
                    "docstatus": 1,
                    "status": ["in", ["Present", "Half Day"]]
                },
                fields=["status"]
            )
            total_days = sum(1 if a.status == "Present" else 0.5 for a in attendance_records)

        if total_days == 0:
            skipped.append(f"{emp.employee_name} (no net processing changes)")
            continue

        current_cycle_earnings = total_days * daily_rate

        # SCENARIO A: Net Positive (Employee earned more days than retro deductions)
        if current_cycle_earnings > 0:
            advance_balance = _get_live_advance_balance(emp.name, advance_account)
            wages_owed      = _get_live_wages_owed(emp.name, salary_payable)

            total_wages_owed  = wages_owed + current_cycle_earnings
            advance_deduction = min(advance_balance, current_cycle_earnings) if advance_balance > 0 else 0.0

            je = frappe.new_doc("Journal Entry")
            je.voucher_type = "Journal Entry"
            je.company      = company
            je.posting_date = to_date
            je.remark = (
                f"Auto attendance processing (with retro adjustments) for {emp.employee_name} "
                f"({from_date} to {to_date}) — Net {total_days} days @ ₹{daily_rate}/day"
            )

            je.append("accounts", {
                "account": salary_expense,
                "debit_in_account_currency": current_cycle_earnings,
                "cost_center": cost_center,
                "user_remark": f"Wages Earned: {emp.name}"
            })
            je.append("accounts", {
                "account": salary_payable,
                "party_type": "Employee",
                "party": emp.name,
                "credit_in_account_currency": current_cycle_earnings,
                "cost_center": cost_center,
                "user_remark": f"Wages Earned: {emp.name}"
            })

            if advance_deduction > 0:
                je.append("accounts", {
                    "account": salary_payable,
                    "party_type": "Employee",
                    "party": emp.name,
                    "debit_in_account_currency": advance_deduction,
                    "cost_center": cost_center,
                    "user_remark": f"Advance Auto-Offset: {emp.name}"
                })
                je.append("accounts", {
                    "account": advance_account,
                    "party_type": "Employee",
                    "party": emp.name,
                    "credit_in_account_currency": advance_deduction,
                    "cost_center": cost_center,
                    "user_remark": f"Advance Auto-Offset: {emp.name}"
                })

        # SCENARIO B: Net Negative (Clawback is higher than earnings, employee owes money back)
        else:
            abs_earnings = abs(current_cycle_earnings)
            je = frappe.new_doc("Journal Entry")
            je.voucher_type = "Journal Entry"
            je.company      = company
            je.posting_date = to_date
            je.remark = (
                f"Retroactive attendance clawback for {emp.employee_name} — "
                f"Net overpayment recovery of {abs(total_days)} days @ ₹{daily_rate}/day"
            )

            je.append("accounts", {
                "account": salary_expense,
                "credit_in_account_currency": abs_earnings,
                "cost_center": cost_center,
                "user_remark": f"Retro Adjustment Recovery: {emp.name}"
            })
            je.append("accounts", {
                "account": advance_account,
                "party_type": "Employee",
                "party": emp.name,
                "debit_in_account_currency": abs_earnings,
                "cost_center": cost_center,
                "user_remark": f"Overpayment clawback converted to Advance: {emp.name}"
            })

        je.insert(ignore_permissions=True)
        je.submit()
        # Stamp each attendance record so fetch knows it's been accounted for
        for att in frappe.get_all(
            "Attendance",
            filters={
                "employee": emp.name,
                "attendance_date": ["between", [from_date, to_date]],
                "docstatus": 1,
                "status": ["in", ["Present", "Half Day"]]
            },
            fields=["name"]
        ):
            frappe.db.set_value("Attendance", att.name, "custom_processed_in_je", je.name)
        processed.append({
            "employee":         emp.name,
            "employee_name":    emp.employee_name,
            "days":             total_days,
            "wages_booked":     current_cycle_earnings,
            "advance_offset":   advance_deduction,
            "net_owed":         (total_wages_owed - advance_deduction) if current_cycle_earnings > 0 else current_cycle_earnings,
            "je":               je.name
        })

    return {"processed": processed, "skipped": skipped}


def _get_live_advance_balance(employee, advance_account):
    result = frappe.db.sql("""
        SELECT SUM(debit - credit) FROM `tabGL Entry`
        WHERE party = %s AND account = %s AND docstatus = 1 AND is_cancelled = 0
    """, (employee, advance_account))[0][0]
    val = flt(result)
    return val if val > 0 else 0.0


def _get_live_wages_owed(employee, salary_payable):
    result = frappe.db.sql("""
        SELECT SUM(credit - debit) FROM `tabGL Entry`
        WHERE party = %s AND account = %s AND docstatus = 1 AND is_cancelled = 0
    """, (employee, salary_payable))[0][0]
    val = flt(result)
    return val if val > 0 else 0.0