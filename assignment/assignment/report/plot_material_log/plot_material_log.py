import frappe
from frappe import _

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    chart = get_chart_data(data)
    return columns, data, None, chart

def get_columns():
    return [
        {
            "label": _("Cost Center (Plot)"),
            "fieldname": "cost_center",
            "fieldtype": "Link",
            "options": "Cost Center",
            "width": 180
        },
        {
            "label": _("Item Code"),
            "fieldname": "item_code",
            "fieldtype": "Link",
            "options": "Item",
            "width": 140
        },
        {
            "label": _("Item Name"),
            "fieldname": "item_name",
            "fieldtype": "Data",
            "width": 200
        },
        {
            "label": _("Type"),
            "fieldname": "purpose",
            "fieldtype": "Data",
            "width": 130
        },
        {
            "label": _("Posting Date"),
            "fieldname": "posting_date",
            "fieldtype": "Date",
            "width": 110
        },
        {
            "label": _("Quantity"),
            "fieldname": "qty",
            "fieldtype": "Float",
            "width": 100
        },
        {
            "label": _("Stock UOM"),
            "fieldname": "uom",
            "fieldtype": "Link",
            "options": "UOM",
            "width": 90
        },
        {
            "label": _("Amount Value"),
            "fieldname": "amount",
            "fieldtype": "Currency",
            "width": 140
        }
    ]

def get_data(filters):
    conditions = ""
    values = {}

    if filters.get("from_date") and filters.get("to_date"):
        conditions += " AND se.posting_date BETWEEN %(from_date)s AND %(to_date)s"
        values["from_date"] = filters["from_date"]
        values["to_date"] = filters["to_date"]

    # Updated: Filter against the line item cost center
    if filters.get("cost_center"):
        conditions += " AND sed.cost_center = %(cost_center)s"
        values["cost_center"] = filters["cost_center"]

    # Source 1: Stock Entries (Reading from Line Items)
    stock_data = frappe.db.sql(f"""
        SELECT
            se.posting_date,
            sed.cost_center,
            sed.item_code,
            sed.item_name,
            se.purpose,
            sed.qty,
            sed.stock_uom AS uom,
            sed.amount
        FROM
            `tabStock Entry Detail` sed
        INNER JOIN
            `tabStock Entry` se ON sed.parent = se.name
        INNER JOIN
            `tabCost Center` cc ON sed.cost_center = cc.name
        WHERE
            cc.custom_is_plot = 1
            AND se.docstatus = 1
            AND se.purpose IN ('Material Issue', 'Material Receipt')
            {conditions}
    """, values=values, as_dict=True)

    # Source 2: Employee Contracts
    contract_conditions = ""
    contract_values = {}

    if filters.get("from_date") and filters.get("to_date"):
        contract_conditions += " AND ec.creation BETWEEN %(from_date)s AND %(to_date)s"
        contract_values["from_date"] = filters["from_date"]
        contract_values["to_date"] = filters["to_date"]

    if filters.get("cost_center"):
        contract_conditions += " AND ecp.plot = %(cost_center)s"
        contract_values["cost_center"] = filters["cost_center"]

    contract_data = frappe.db.sql(f"""
        SELECT
            DATE(ec.creation) AS posting_date,
            ecp.plot AS cost_center,
            NULL AS item_code,
            CONCAT('Contract: ', ec.employee_name) AS item_name,
            'Employee Contract' AS purpose,
            CAST(ecp.area AS FLOAT) AS qty,
            'Acre' AS uom,
            CAST(ec.total_payout_amount AS FLOAT) AS amount
        FROM
            `tabEmployee Contract` ec
        INNER JOIN
            `tabEmployee Contract Plot` ecp ON ecp.parent = ec.name
        INNER JOIN
            `tabCost Center` cc ON ecp.plot = cc.name
        WHERE
            cc.custom_is_plot = 1
            AND ec.docstatus = 1
            {contract_conditions}
    """, values=contract_values, as_dict=True)

    # Combine and sort everything cleanly by Cost Center
    combined_data = stock_data + contract_data
    combined_data.sort(key=lambda x: (x.get("cost_center") or "", x.get("posting_date") or ""))
    
    return combined_data

def get_chart_data(data):
    if not data:
        return None

    plot_summary = {}
    for row in data:
        cc = row.get("cost_center")
        if not cc:
            continue
            
        if cc not in plot_summary:
            plot_summary[cc] = {"issue": 0, "receipt": 0, "contract": 0}

        amount = row.get("amount") or 0
        purpose = row.get("purpose")
        
        if purpose == "Material Issue":
            plot_summary[cc]["issue"] += amount
        elif purpose == "Material Receipt":
            plot_summary[cc]["receipt"] += amount
        elif purpose == "Employee Contract":
            plot_summary[cc]["contract"] += amount

    labels = list(plot_summary.keys())

    return {
        "data": {
            "labels": labels,
            "datasets": [
                {"name": _("Material Issue"), "values": [plot_summary[cc]["issue"] for cc in labels]},
                {"name": _("Material Receipt"), "values": [plot_summary[cc]["receipt"] for cc in labels]},
                {"name": _("Contract Payout"), "values": [plot_summary[cc]["contract"] for cc in labels]}
            ]
        },
        "type": "bar",
        "colors": ["#ff5858", "#2ecc71", "#3498db"]
    }