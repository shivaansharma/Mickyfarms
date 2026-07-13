import frappe
from frappe.utils import flt, fmt_money, getdate

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
        {"label": "Debit (Owed)", "fieldname": "goods_value", "fieldtype": "Currency", "width": 140},
        {"label": "Credit (Paid)", "fieldname": "amount_paid", "fieldtype": "Currency", "width": 120},
        {"label": "Running Balance", "fieldname": "balance", "fieldtype": "Currency", "width": 240},
    ]

def build_date_filter(filters, fieldname="posting_date"):
    conditions = {}
    if filters.get("from_date") and filters.get("to_date"):
        conditions[fieldname] = ["between", [filters["from_date"], filters["to_date"]]]
    elif filters.get("from_date"):
        conditions[fieldname] = [">=", filters["from_date"]]
    elif filters.get("to_date"):
        conditions[fieldname] = ["<=", filters["to_date"]]
    return conditions

def get_contract_value(ec):
    val = flt(getattr(ec, "net_payable_amount", None))
    if val != 0:
        return val

    val = flt(ec.total_payout_amount)
    if val != 0:
        return val

    plots = frappe.get_all("Employee Contract Plot", filters={"parent": ec.name}, fields=["area"])
    return flt(ec.rate_per_acre) * sum(flt(p.area) for p in plots)

def get_data(filters):
    supplier = filters.get("supplier")
    if not supplier:
        frappe.throw("Please select a Supplier to view this report.")

    company = filters.get("company")
    date_conditions = build_date_filter(filters, "posting_date")

    # 1. Fetch Purchase Invoices
    pi_filters = {"supplier": supplier, "docstatus": 1, **date_conditions}
    if company:
        pi_filters["company"] = company

    invoices = frappe.get_all(
        "Purchase Invoice",
        filters=pi_filters,
        fields=["name", "posting_date", "grand_total", "bill_no"],
    )

    # 2. Fetch Employee Contracts
    ec_filters = {"employee": supplier, "docstatus": 1, **date_conditions}
    if company and frappe.get_meta("Employee Contract").has_field("company"):
        ec_filters["company"] = company

    contracts = frappe.get_all(
        "Employee Contract",
        filters=ec_filters,
        fields=["name", "posting_date", "net_payable_amount", "total_payout_amount", "rate_per_acre"],
    )

    # 3. Fetch Doctor Logs
    dl_filters = {"doctor": supplier, "docstatus": 1, **date_conditions}
    if company:
        dl_filters["company"] = company

    doctor_logs = frappe.get_all(
        "Doctor Log",
        filters=dl_filters,
        fields=["name", "posting_date", "cost", "purchase_invoice"]
    )
    
    # Create a mapping of Purchase Invoice to Doctor Log so we don't double count
    pi_to_dl_map = {log.purchase_invoice: log for log in doctor_logs if log.purchase_invoice}
    unlinked_logs = [log for log in doctor_logs if not log.purchase_invoice]

    # 4. Fetch Payment Entries
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

    # Process Purchase Invoices (and inject Doctor Log details if they generated the bill)
    for inv in invoices:
        inv_date = getdate(inv.posting_date)
        
        if inv.name in pi_to_dl_map:
            # This invoice came from a Doctor Log. Show the Log instead for clarity.
            log = pi_to_dl_map[inv.name]
            rows.append({
                "date": inv_date,
                "type": "Vet Services",
                "reference_doctype": "Doctor Log",
                "reference": log.name,
                "description": f"Vet Visit Log: {log.name} (GL Invoice: {inv.name})",
                "goods_value": inv.grand_total,
                "amount_paid": 0,
                "_sort": (inv_date, inv.name),
            })
        else:
            rows.append({
                "date": inv_date,
                "type": "Goods Purchased",
                "reference_doctype": "Purchase Invoice",
                "reference": inv.name,
                "description": f"Purchase Invoice {inv.bill_no or inv.name}",
                "goods_value": inv.grand_total,
                "amount_paid": 0,
                "_sort": (inv_date, inv.name),
            })

    # Process any legacy Doctor Logs that don't have a Purchase Invoice attached
    for log in unlinked_logs:
        log_date = getdate(log.posting_date)
        rows.append({
            "date": log_date,
            "type": "Vet Services",
            "reference_doctype": "Doctor Log",
            "reference": log.name,
            "description": f"Vet Visit Log: {log.name} (No Invoice Linked)",
            "goods_value": log.cost,
            "amount_paid": 0,
            "_sort": (log_date, log.name),
        })

    # Process Employee Contracts
    for ec in contracts:
        contract_date = getdate(ec.posting_date)
        contract_value = get_contract_value(ec)

        rows.append({
            "date": contract_date,
            "type": "Contract Payout",
            "reference_doctype": "Employee Contract",
            "reference": ec.name,
            "description": f"Employee Contract {ec.name}",
            "goods_value": contract_value,
            "amount_paid": 0,
            "_sort": (contract_date, ec.name),
        })

    # Process Payments
    for pe in payments:
        refs = frappe.get_all(
            "Payment Entry Reference",
            filters={"parent": pe.name},
            fields=["reference_doctype", "reference_name", "allocated_amount"],
        )

        pi_refs = [r for r in refs if r.reference_doctype == "Purchase Invoice"]
        ec_refs = [r for r in refs if r.reference_doctype == "Employee Contract"]
        dl_refs = [r for r in refs if r.reference_doctype == "Doctor Log"] # In case allocated directly

        parts = []
        if pi_refs:
            parts.append("Settled against Invoice " + ", ".join(r.reference_name for r in pi_refs))
        if ec_refs:
            parts.append("Settled against Contract " + ", ".join(r.reference_name for r in ec_refs))
        if dl_refs:
            parts.append("Settled against Vet Services " + ", ".join(r.reference_name for r in dl_refs))
            
        if not refs:
            parts.append("Advance / pre-payment")

        pay_date = getdate(pe.posting_date)
        
        # Determine specific payment type label
        if ec_refs:
            pay_type = "Contract Payment"
        elif dl_refs:
            pay_type = "Vet Payment"
        else:
            pay_type = "Settlement Payment"

        rows.append({
            "date": pay_date,
            "type": pay_type,
            "reference_doctype": "Payment Entry",
            "reference": pe.name,
            "description": "; ".join(parts) + (f" via {pe.mode_of_payment}" if pe.mode_of_payment else ""),
            "goods_value": 0,
            "amount_paid": pe.paid_amount,
            "_sort": (pay_date, pe.name),
        })

    # Sort everything chronologically
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
    return [
        {"label": "Total Liability", "value": total_goods, "datatype": "Currency"},
        {"label": "Total Paid", "value": total_paid, "datatype": "Currency"},
        {"label": "Outstanding Owed", "value": net_balance, "datatype": "Currency", "indicator": "Red" if net_balance > 0 else "Green"},
    ]