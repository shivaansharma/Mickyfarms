# Copyright (c) 2026, shivaan and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, getdate, add_days

class WeeklyWagePayment(Document):
    def on_submit(self):
        if not self.wage_details:
            frappe.throw("Cannot submit a payment run without employee line items.")

        company      = getattr(self, "company", "Micky Farms")
        company_abbr = frappe.get_cached_value('Company', company, 'abbr')
        cost_center  = getattr(self, "cost_center", f"Main - {company_abbr}")

        salary_expense  = f"Salary - {company_abbr}"
        salary_payable  = f"Salary Payable - {company_abbr}"
        advance_account = f"Employee Advances - {company_abbr}"

        je = frappe.new_doc("Journal Entry")
        je.voucher_type = "Journal Entry"
        je.company      = company
        je.posting_date = self.to_date
        je.remark = (
            f"Automated wage processing up to {self.to_date} "
            f"via {self.doctype} {self.name}"
        )

        for item in self.wage_details:
            emp = item.employee

            current_cycle_earnings = flt(item.days_worked) * flt(item.daily_wage_rate)
            final_net_payout       = flt(item.final_net_payout)

            # ── Re-derive balances fresh from GL at submit time ──────────────
            # This is the critical fix: we do NOT trust the snapshot fields
            # saved on the child row (they may be stale if the form was saved
            # before the user refreshed).  We always read live GL balances.
            live_advance_balance = _get_advance_balance(emp, advance_account)
            live_wages_owed      = _get_wages_owed(emp, salary_payable)

            # ── Step 1: Book current cycle earnings as expense ───────────────
            if current_cycle_earnings > 0:
                je.append("accounts", {
                    "account": salary_expense,
                    "debit_in_account_currency": current_cycle_earnings,
                    "cost_center": cost_center,
                    "user_remark": f"Wage Cycle: {self.name}"
                })
                je.append("accounts", {
                    "account": salary_payable,
                    "party_type": "Employee",
                    "party": emp,
                    "credit_in_account_currency": current_cycle_earnings,
                    "cost_center": cost_center,
                    "user_remark": f"Wage Cycle: {self.name}"
                })

            # ── Step 2: Net advance against total wages now owed ─────────────
            # Total owed after this cycle = prior unpaid wages + this cycle
            total_wages_owed = live_wages_owed + current_cycle_earnings

            # If there is an existing advance balance, offset it against wages
            advance_deduction = 0.0
            if live_advance_balance > 0 and total_wages_owed > 0:
                advance_deduction = min(live_advance_balance, total_wages_owed)

                # Debit Salary Payable (reduce what we owe the employee)
                # Credit Employee Advances (reduce what employee owes us)
                je.append("accounts", {
                    "account": salary_payable,
                    "party_type": "Employee",
                    "party": emp,
                    "debit_in_account_currency": advance_deduction,
                    "cost_center": cost_center,
                    "user_remark": f"Advance Auto-Offset Against Wages: {self.name}"
                })
                je.append("accounts", {
                    "account": advance_account,
                    "party_type": "Employee",
                    "party": emp,
                    "credit_in_account_currency": advance_deduction,
                    "cost_center": cost_center,
                    "user_remark": f"Advance Auto-Offset Against Wages: {self.name}"
                })

            # ── Step 3: Actual cash payout ───────────────────────────────────
            net_wages_after_offset = total_wages_owed - advance_deduction

            if final_net_payout > 0:
                # How much of payout covers remaining wages vs becomes new advance
                payout_against_wages = min(final_net_payout, net_wages_after_offset)
                overpayment          = final_net_payout - net_wages_after_offset

                # Debit Salary Payable, Credit Cash/Bank
                je.append("accounts", {
                    "account": salary_payable,
                    "party_type": "Employee",
                    "party": emp,
                    "debit_in_account_currency": final_net_payout,
                    "cost_center": cost_center,
                    "user_remark": f"Cash Payout: {self.name}"
                })
                je.append("accounts", {
                    "account": self.paid_from_account,
                    "credit_in_account_currency": final_net_payout,
                    "cost_center": cost_center,
                    "user_remark": f"Cash Payout: {self.name}"
                })

                # ── Step 4: If cash paid > wages owed, excess = new advance ──
                if overpayment > 0.01:
                    je.append("accounts", {
                        "account": advance_account,
                        "party_type": "Employee",
                        "party": emp,
                        "debit_in_account_currency": overpayment,
                        "cost_center": cost_center,
                        "user_remark": f"Overpayment → New Advance Debt: {self.name}"
                    })
                    je.append("accounts", {
                        "account": salary_payable,
                        "party_type": "Employee",
                        "party": emp,
                        "credit_in_account_currency": overpayment,
                        "cost_center": cost_center,
                        "user_remark": f"Overpayment → New Advance Debt: {self.name}"
                    })

            # ── Write derived values back onto the child row so the report ───
            # ── and the saved document reflect what actually happened ─────────
            item.advance_deduction  = advance_deduction
            item.payment            = current_cycle_earnings

        if len(je.accounts) > 0:
            je.insert(ignore_permissions=True)
            je.submit()

    def on_cancel(self):
        linked_jes = frappe.get_all(
            "Journal Entry Account",
            filters={
                "user_remark": ["like", f"%{self.name}%"],
                "docstatus": 1
            },
            pluck="parent"
        )
        for je_name in set(linked_jes):
            frappe.get_doc("Journal Entry", je_name).cancel()


def _get_advance_balance(employee, advance_account):
    """Live advance balance from GL — positive means employee owes us."""
    result = frappe.db.sql("""
        SELECT SUM(debit - credit)
        FROM `tabGL Entry`
        WHERE party = %s
          AND account = %s
          AND docstatus = 1
          AND is_cancelled = 0
    """, (employee, advance_account))[0][0]
    val = flt(result)
    return val if val > 0 else 0.0


def _get_wages_owed(employee, salary_payable):
    """Live wages owed balance from GL — positive means we owe the employee."""
    result = frappe.db.sql("""
        SELECT SUM(credit - debit)
        FROM `tabGL Entry`
        WHERE party = %s
          AND account = %s
          AND docstatus = 1
          AND is_cancelled = 0
    """, (employee, salary_payable))[0][0]
    val = flt(result)
    return val if val > 0 else 0.0


@frappe.whitelist()
def get_employee_wages_owed(employee, company):
    if not company or not employee:
        return 0

    company_abbr = frappe.get_cached_value('Company', company, 'abbr')
    return _get_wages_owed(employee, f"Salary Payable - {company_abbr}")


@frappe.whitelist()
def fetch_employees_and_metrics(to_date, company, employee=None):
    company_abbr = frappe.get_cached_value('Company', company, 'abbr')
    advance_account = f"Employee Advances - {company_abbr}"
    salary_payable  = f"Salary Payable - {company_abbr}"
    results = []

    filters = {'status': 'Active', 'company': company}
    if employee:
        filters['name'] = employee

    employees = frappe.get_all(
        'Employee',
        filters=filters,
        fields=['name', 'employee_name', 'custom_daily_wage_rate']
    )

    for emp in employees:
        # Only use wage runs where attendance was actually counted to determine
        # the last processed date — pure financial runs don't move this forward.
        last_record = frappe.db.sql("""
            SELECT MAX(wwp.to_date)
            FROM `tabWeekly Wage Payment` wwp
            JOIN `tabWeekly Wage Line Item` wwli ON wwp.name = wwli.parent
            WHERE wwp.docstatus = 1
              AND wwli.employee = %s
              AND wwli.days_worked > 0
        """, (emp.name,))

        last_date = last_record[0][0] if last_record and last_record[0][0] else None

        if last_date:
            computed_from_date = add_days(last_date, 1)
        else:
            date_parts = to_date.split("-")
            computed_from_date = f"{date_parts[0]}-{date_parts[1]}-01"

        total_days = 0
        if getdate(computed_from_date) <= getdate(to_date):
            attendance_records = frappe.get_all(
                'Attendance',
                filters={
                    "employee": emp.name,
                    "attendance_date": ["between", [computed_from_date, to_date]],
                    "docstatus": 1,
                    "status": ["in", ["Present", "Half Day"]],
                    "custom_processed_in_je": ["is", "not set"]
                },
                fields=["status"]
            )
            for a in attendance_records:
                total_days += 1 if a.status == "Present" else 0.5

        # Always read live GL balances — never stale snapshots
        advance_balance     = _get_advance_balance(emp.name, advance_account)
        previous_wages_owed = _get_wages_owed(emp.name, salary_payable)

        results.append({
            "employee":              emp.name,
            "employee_name":         emp.employee_name,
            "daily_wage_rate":       flt(emp.custom_daily_wage_rate) or 0,
            "days_worked":           total_days,
            "advance_snapshot":      advance_balance,
            "outstanding_snapshot":  previous_wages_owed,
            "final_net_payout":      0
        })

    return results