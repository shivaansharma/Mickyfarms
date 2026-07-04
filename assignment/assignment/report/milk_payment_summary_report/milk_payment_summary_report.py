# Copyright (c) 2026, shivaan and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate
from erpnext.accounts.party import get_party_account


def execute(filters=None):
    filters = filters or {}

    if filters.get("customer"):
        columns = get_detail_columns()
        data = get_detail_data(filters)

        # Calculate summary values for a Single Customer Statement
        customer = filters.get("customer")
        company = get_default_company(filters)
        live_bal = get_current_balances(customer, company)

        total_owed = live_bal["outstanding_balance"]
        total_advance = live_bal["advance_owed"]
        net_position = total_owed - total_advance

        report_summary = [
            {
                "value": total_owed,
                "label": _("Balance Owed (They Owe You)"),
                "datatype": "Currency",
                "indicator": "Red" if total_owed > 0 else "Green"
            },
            {
                "value": total_advance,
                "label": _("Advance Held (You Owe Them)"),
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

        # Calculate summary values for the Global Customer Overview
        total_owed = 0.0
        total_advance = 0.0
        for row in data:
            if row.get("customer"):  # Skip the totals row
                total_owed += flt(row.get("outstanding_balance"))
                total_advance += flt(row.get("latest_advance_owed"))

        net_position = total_owed - total_advance

        report_summary = [
            {
                "value": total_owed,
                "label": _("Total Owed (They Owe You)"),
                "datatype": "Currency",
                "indicator": "Red" if total_owed > 0 else "Green"
            },
            {
                "value": total_advance,
                "label": _("Total Advances (You Owe Them)"),
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


def get_default_company(filters=None):
    filters = filters or {}
    return filters.get("company") or frappe.defaults.get_user_default("Company")


def get_current_balances(customer, company):
    """
    Fetches the real-time live balance for a customer straight from the GL,
    using their actual receivable account. A positive account balance means
    the customer owes the farm (outstanding). A negative balance means the
    customer has overpaid / holds credit (an advance the farm owes back).

    Note: unlike a payroll ledger with two distinct accounts (advance vs
    payable), a customer typically has a single receivable account, so the
    sign of that one balance already tells us which bucket applies — there's
    no separate "Customer Advance" account assumed here unless you have one
    configured, in which case this can be extended the same way as the
    reference employee ledger (summing two accounts and netting them).
    """
    receivable_account = get_party_account("Customer", customer, company)

    balance = frappe.db.sql("""
        SELECT SUM(debit - credit)
        FROM `tabGL Entry`
        WHERE
            party = %s
            AND account = %s
            AND docstatus = 1
            AND is_cancelled = 0
    """, (customer, receivable_account))[0][0] or 0

    balance = flt(balance)

    if balance >= 0:
        outstanding = balance
        advance = 0.0
    else:
        outstanding = 0.0
        advance = -balance

    return {
        "outstanding_balance": outstanding,
        "advance_owed": advance,
        "account": receivable_account,
    }


# ===============================================================
# DETAIL MODE (Chronological Statement Ledger for One Customer)
# ===============================================================
def get_detail_columns():
    return [
        {"label": _("Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 110},
        {"label": _("Description"), "fieldname": "tx_type", "fieldtype": "Data", "width": 220},
        {
            "label": _("Reference No"),
            "fieldname": "voucher_no",
            "fieldtype": "Dynamic Link",
            "options": "voucher_type",
            "width": 150,
        },
        {"label": _("Mode of Payment"), "fieldname": "mode_of_payment", "fieldtype": "Data", "width": 120},
        {"label": _("Milk Value Invoiced"), "fieldname": "amount_invoiced", "fieldtype": "Currency", "width": 160},
        {"label": _("Payment Received"), "fieldname": "amount_paid", "fieldtype": "Currency", "width": 150},
        {"label": _("Balance Owed (Running)"), "fieldname": "running_owed", "fieldtype": "Currency", "width": 180},
        {"label": _("Advance Held (Running)"), "fieldname": "running_advance", "fieldtype": "Currency", "width": 180},
        {"label": _("Net Position (+ve = they owe you)"), "fieldname": "net_balance", "fieldtype": "Currency", "width": 210},
    ]


def get_milk_payment_label(voucher_no):
    """Look up the friendly Milk Payment record + mode behind a Payment Entry, if any."""
    row = frappe.db.get_value(
        "Milk Payment",
        {"payment_entry": voucher_no},
        ["name", "mode_of_payment"],
        as_dict=True,
    )
    if row:
        return row.name, row.mode_of_payment
    return None, None


def get_detail_data(filters):
    customer = filters.get("customer")
    company = get_default_company(filters)
    receivable_account = get_party_account("Customer", customer, company)

    gl_conditions = [
        "gle.party = %(customer)s",
        "gle.account = %(account)s",
        "gle.docstatus = 1",
        "gle.is_cancelled = 0",
    ]
    gl_params = {"customer": customer, "account": receivable_account}

    if filters.get("from_date") and filters.get("to_date"):
        gl_conditions.append("gle.posting_date BETWEEN %(from_date)s AND %(to_date)s")
        gl_params["from_date"] = filters.get("from_date")
        gl_params["to_date"] = filters.get("to_date")

    gl_entries = frappe.db.sql(f"""
        SELECT
            gle.posting_date AS posting_date,
            gle.voucher_type AS voucher_type,
            gle.voucher_no   AS voucher_no,
            gle.debit        AS debit,
            gle.credit       AS credit
        FROM `tabGL Entry` gle
        WHERE {" AND ".join(gl_conditions)}
        ORDER BY gle.posting_date ASC, gle.creation ASC
    """, gl_params, as_dict=1)

    raw_timeline = []
    total_invoiced = 0.0
    total_paid = 0.0

    for entry in gl_entries:
        debit = flt(entry["debit"])
        credit = flt(entry["credit"])

        row = {
            "posting_date": entry["posting_date"],
            "voucher_type": entry["voucher_type"],
            "voucher_no": entry["voucher_no"],
            "mode_of_payment": "",
            "amount_invoiced": 0.0,
            "amount_paid": 0.0,
            "delta": 0.0,
            "tx_type": "",
        }

        if entry["voucher_type"] == "Sales Invoice" and debit > 0:
            row["tx_type"] = "Milk Value Invoiced"
            row["amount_invoiced"] = debit
            row["delta"] = debit
            total_invoiced += debit

        elif entry["voucher_type"] == "Sales Invoice" and credit > 0:
            row["tx_type"] = "Credit Note Issued"
            row["amount_invoiced"] = -credit
            row["delta"] = -credit

        elif entry["voucher_type"] == "Payment Entry" and credit > 0:
            mp_name, mode = get_milk_payment_label(entry["voucher_no"])
            row["tx_type"] = "Payment Received" + (f" ({mp_name})" if mp_name else "")
            row["mode_of_payment"] = mode or ""
            row["amount_paid"] = credit
            row["delta"] = -credit
            total_paid += credit

        elif entry["voucher_type"] == "Payment Entry" and debit > 0:
            row["tx_type"] = "Refund to Customer"
            row["amount_paid"] = -debit
            row["delta"] = -debit

        elif entry["voucher_type"] == "Journal Entry":
            if debit > 0:
                row["tx_type"] = "Manual Adjustment (Journal Entry)"
                row["amount_invoiced"] = debit
                row["delta"] = debit
            else:
                row["tx_type"] = "Manual Adjustment (Journal Entry)"
                row["amount_paid"] = credit
                row["delta"] = -credit

        else:
            row["tx_type"] = f"Other Entry ({entry['voucher_type']})"
            row["delta"] = debit - credit

        raw_timeline.append(row)

    raw_timeline.sort(key=lambda x: x["posting_date"] or getdate("1970-01-01"))

    current_balance = 0.0
    for item in raw_timeline:
        current_balance += item["delta"]
        item["running_owed"] = current_balance if current_balance > 0 else 0.0
        item["running_advance"] = -current_balance if current_balance < 0 else 0.0
        item["net_balance"] = current_balance

    raw_timeline.reverse()

    live_bal = get_current_balances(customer, company)

    if not raw_timeline:
        raw_timeline.append({
            "posting_date": None,
            "tx_type": "<b>No transactional history found</b>",
            "voucher_type": "",
            "voucher_no": "",
            "mode_of_payment": "",
            "amount_invoiced": 0.0,
            "amount_paid": 0.0,
            "running_owed": live_bal["outstanding_balance"],
            "running_advance": live_bal["advance_owed"],
            "net_balance": live_bal["outstanding_balance"] - live_bal["advance_owed"],
        })
    else:
        raw_timeline.append({
            "posting_date": "",
            "tx_type": "<b>LIVE ACCOUNT TOTALS</b>",
            "voucher_type": "",
            "voucher_no": "",
            "mode_of_payment": "",
            "amount_invoiced": total_invoiced,
            "amount_paid": total_paid,
            "running_owed": live_bal["outstanding_balance"],
            "running_advance": live_bal["advance_owed"],
            "net_balance": live_bal["outstanding_balance"] - live_bal["advance_owed"],
        })

    return raw_timeline


# ===============================================================
# SUMMARY MODE (Clean, Consolidated Overview - One Row Per Customer)
# ===============================================================
def get_summary_columns():
    return [
        {"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 160},
        {"label": _("Customer Name"), "fieldname": "customer_name", "fieldtype": "Data", "width": 160},
        {"label": _("Last Payment Date"), "fieldname": "last_payment_date", "fieldtype": "Date", "width": 130},
        {"label": _("Payments Count"), "fieldname": "payment_count", "fieldtype": "Int", "width": 110},
        {"label": _("Total Paid (Period)"), "fieldname": "total_paid_period", "fieldtype": "Currency", "width": 150},
        {"label": _("Current Advance Balance (Live)"), "fieldname": "latest_advance_owed", "fieldtype": "Currency", "width": 200},
        {"label": _("Current Balance Owed (Live)"), "fieldname": "outstanding_balance", "fieldtype": "Currency", "width": 200},
    ]


def get_summary_data(filters):
    company = get_default_company(filters)

    milk_customers = frappe.get_all(
        "Customer",
        filters={"custom_is_milk_customer": 1},
        fields=["name", "customer_name"],
    )

    payment_stats = {}
    if milk_customers:
        payment_filters = {
            "docstatus": 1,
            "customer": ["in", [c.name for c in milk_customers]],
        }
        if filters.get("from_date") and filters.get("to_date"):
            payment_filters["posting_date"] = ["between", [filters.get("from_date"), filters.get("to_date")]]
        if filters.get("company"):
            payment_filters["company"] = filters.get("company")

        payments = frappe.get_all(
            "Milk Payment",
            filters=payment_filters,
            fields=["customer", "posting_date", "paid_amount"],
        )

        for p in payments:
            stat = payment_stats.setdefault(p.customer, {"count": 0, "total": 0.0, "last_date": None})
            stat["count"] += 1
            stat["total"] += flt(p.paid_amount)
            if not stat["last_date"] or getdate(p.posting_date) > getdate(stat["last_date"]):
                stat["last_date"] = p.posting_date

    report_data = []
    balance_cache = {}

    for cust in milk_customers:
        stat = payment_stats.get(cust.name, {"count": 0, "total": 0.0, "last_date": None})
        balance_cache[cust.name] = get_current_balances(cust.name, company)

        report_data.append({
            "customer": cust.name,
            "customer_name": cust.customer_name,
            "last_payment_date": stat["last_date"],
            "payment_count": stat["count"],
            "total_paid_period": stat["total"],
            "latest_advance_owed": balance_cache[cust.name]["advance_owed"],
            "outstanding_balance": balance_cache[cust.name]["outstanding_balance"],
        })

    report_data.sort(key=lambda x: (x["customer_name"] or ""))

    if report_data:
        total_paid = sum(r["total_paid_period"] for r in report_data)
        total_advance = sum(b["advance_owed"] for b in balance_cache.values())
        total_outstanding = sum(b["outstanding_balance"] for b in balance_cache.values())

        report_data.append({
            "customer": "",
            "customer_name": "<b>TOTALS</b>",
            "last_payment_date": "",
            "payment_count": sum(r["payment_count"] for r in report_data),
            "total_paid_period": total_paid,
            "latest_advance_owed": total_advance,
            "outstanding_balance": total_outstanding,
        })

    return report_data