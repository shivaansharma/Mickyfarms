# Copyright (c) 2026, shivaan and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt

def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = get_data(filters)
    
    total_qty = sum(flt(row.get("qty")) for row in data)
    total_val = sum(flt(row.get("amount")) for row in data)
        
    report_summary = [
        {"value": total_qty, "label": _("Total Qty Issued"), "datatype": "Float", "indicator": "Blue"},
        {"value": total_val, "label": _("Total Material Value"), "datatype": "Currency", "indicator": "Green"}
    ]
    
    if data:
        data.append({
            "cost_center": "", # Left blank to prevent breaking the Link field formatting
            "item_name": f"<b>TOTAL (Total Qty Issued: {total_qty})</b>",
            "description": "", 
            "amount": total_val
        })
    
    return columns, data, None, None, report_summary

def get_columns():
    return [
        {"label": _("Cost Center"), "fieldname": "cost_center", "fieldtype": "Link", "options": "Cost Center", "width": 180},
        {"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 110},
        {"label": _("Stock Entry"), "fieldname": "parent", "fieldtype": "Link", "options": "Stock Entry", "width": 150},
        {"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 140},
        {"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 260}, # Widened slightly to accommodate the bold totals text
        {"label": _("Description"), "fieldname": "description", "fieldtype": "Data", "width": 200},
        {"label": _("UOM"), "fieldname": "uom", "fieldtype": "Data", "width": 90},
        {"label": _("Rate"), "fieldname": "basic_rate", "fieldtype": "Currency", "width": 110},
        {"label": _("Total Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 130},
    ]

def get_data(filters):
    conditions = ["se.docstatus = 1", "se.purpose = 'Material Issue'"]
    params = {}
    
    if filters.get("company"):
        conditions.append("se.company = %(company)s")
        params["company"] = filters.get("company")
    if filters.get("cost_center"):
        conditions.append("sed.cost_center = %(cost_center)s")
        params["cost_center"] = filters.get("cost_center")
        
    # Split the date filter so it works even if the user only provides one date
    if filters.get("from_date"):
        conditions.append("se.posting_date >= %(from_date)s")
        params["from_date"] = filters.get("from_date")
    if filters.get("to_date"):
        conditions.append("se.posting_date <= %(to_date)s")
        params["to_date"] = filters.get("to_date")
        
    if filters.get("item_code"):
        conditions.append("sed.item_code = %(item_code)s")
        params["item_code"] = filters.get("item_code")

    data = frappe.db.sql(f"""
        SELECT sed.cost_center, se.posting_date, sed.parent, sed.item_code, 
               sed.item_name, sed.description, sed.qty, sed.uom, sed.basic_rate, sed.amount
        FROM `tabStock Entry Detail` sed
        JOIN `tabStock Entry` se ON sed.parent = se.name
        JOIN `tabCost Center` cc ON sed.cost_center = cc.name
        WHERE { " AND ".join(conditions) }
          /* This explicitly filters out rows where custom_is_plot is 1 */
          AND (cc.custom_is_plot IS NULL OR cc.custom_is_plot = 0)
        ORDER BY se.posting_date DESC, sed.cost_center ASC
    """, params, as_dict=1)
    
    return list(data)