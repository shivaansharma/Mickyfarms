import frappe
from frappe.utils import flt, fmt_money


def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data, total_goods, total_paid = get_data(filters)
    report_summary = get_report_summary(total_goods, total_paid)
    return columns, data, None, None, report_summary


def get_columns():
    return [
        {"label": "Date", "fieldname": "date", "fieldtype": "Date", "width": 95},
        {"label": "Type", "fieldname": "type", "fieldtype": "Data", "width": 150},
        {"label": "Reference Doctype", "fieldname": "reference_doctype", "fieldtype": "Data", "width": 0},
        {"label": "Reference", "fieldname": "reference", "fieldtype": "Dynamic Link", "options": "reference_doctype", "width": 140},
        {"label": "Description", "fieldname": "description", "fieldtype": "Data", "width": 340},
        {"label": "Goods Value", "fieldname": "goods_value", "fieldtype": "Currency", "width": 120},
        {"label": "Amount Paid", "fieldname": "amount_paid", "fieldtype": "Currency", "width": 120},
        {"label": "Running Balance (Owed to Supplier)", "fieldname": "balance", "fieldtype": "Currency", "width": 220},
    ]


def build_date_filter(filters):
    conditions = {}
    if filters.get("from_date") and filters.get("to_date"):
        conditions["posting_date"] = ["between", [filters["from_date"], filters["to_date"]]]
    elif filters.get("from_date"):
        conditions["posting_date"] = [">=", filters["from_date"]]
    elif filters.get("to_date"):
        conditions["posting_date"] = ["<=", filters["to_date"]]
    return conditions


def get_data(filters):
    supplier = filters.get("supplier")
    if not supplier:
        frappe.throw("Please select a Supplier to view this report.")

    company = filters.get("company")
    date_conditions = build_date_filter(filters)

    # 1. All goods purchased (cost side)
    pi_filters = {"supplier": supplier, "docstatus": 1, **date_conditions}
    if company:
        pi_filters["company"] = company

    invoices = frappe.get_all(
        "Purchase Invoice",
        filters=pi_filters,
        fields=["name", "posting_date", "grand_total", "bill_no"],
    )

    # 2. All money paid - settlements, manual payments, and advances alike
    pe_filters = {
        "party_type": "Supplier",
        "party": supplier,
        "docstatus": 1,
        "payment_type": "Pay",
        **date_conditions,
    }
    if company:
        pe_filters["company"] = company

    payments = frappe.get_all(
        "Payment Entry",
        filters=pe_filters,
        fields=["name", "posting_date", "paid_amount", "mode_of_payment"],
    )

    rows = []

    for inv in invoices:
        rows.append({
            "date": inv.posting_date,
            "type": "Goods Purchased",
            "reference_doctype": "Purchase Invoice",
            "reference": inv.name,
            "description": f"Purchase Invoice {inv.bill_no or inv.name}",
            "goods_value": inv.grand_total,
            "amount_paid": 0,
            "_sort": (inv.posting_date, inv.name),
        })

    for pe in payments:
        refs = frappe.get_all(
            "Payment Entry Reference",
            filters={"parent": pe.name},
            fields=["reference_doctype", "reference_name", "allocated_amount"],
        )

        pi_refs = [r for r in refs if r.reference_doctype == "Purchase Invoice"]
        po_refs = [r for r in refs if r.reference_doctype == "Purchase Order"]
        allocated_total = sum(flt(r.allocated_amount) for r in refs)
        unallocated = flt(pe.paid_amount) - allocated_total

        parts = []
        if pi_refs:
            parts.append("Settled against " + ", ".join(r.reference_name for r in pi_refs))
        if po_refs:
            parts.append("Advance against " + ", ".join(r.reference_name for r in po_refs))
        if not refs:
            parts.append("Advance / pre-payment (no order or invoice linked yet)")
        if unallocated > 0.005 and refs:
            parts.append(f"+ unallocated {fmt_money(unallocated)}")

        rows.append({
            "date": pe.posting_date,
            "type": "Settlement Payment" if pi_refs else "Advance Payment",
            "reference_doctype": "Payment Entry",
            "reference": pe.name,
            "description": "; ".join(parts) + (f" via {pe.mode_of_payment}" if pe.mode_of_payment else ""),
            "goods_value": 0,
            "amount_paid": pe.paid_amount,
            "_sort": (pe.posting_date, pe.name),
        })

    rows.sort(key=lambda r: r["_sort"])

    running_balance = 0
    total_goods = 0
    total_paid = 0

    for row in rows:
        running_balance += flt(row["goods_value"]) - flt(row["amount_paid"])
        row["balance"] = running_balance
        total_goods += flt(row["goods_value"])
        total_paid += flt(row["amount_paid"])
        del row["_sort"]

    return rows, total_goods, total_paid


def get_report_summary(total_goods, total_paid):
    net_balance = total_goods - total_paid

    if net_balance > 0.005:
        label, value, indicator = "You Owe Supplier", net_balance, "Red"
    elif net_balance < -0.005:
        label, value, indicator = "Supplier Owes You", abs(net_balance), "Green"
    else:
        label, value, indicator = "Settled", 0, "Blue"

    return [
        {"label": "Total Goods Purchased", "value": total_goods, "datatype": "Currency"},
        {"label": "Total Amount Paid", "value": total_paid, "datatype": "Currency"},
        {"label": label, "value": value, "datatype": "Currency", "indicator": indicator},
    ]