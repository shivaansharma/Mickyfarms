# Copyright (c) 2026, shivaan and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt, getdate


def execute(filters=None):
    filters = filters or {}
    
    # 1. Validate mandatory filters
    if not filters.get("from_date") or not filters.get("to_date"):
        frappe.throw("Please select both From Date and To Date.")

    # 2. Dynamically set columns based on selection
    columns = get_columns(filters)
    
    # 3. Retrieve and aggregate data
    data, grand_total = get_data(filters)
    
    # 4. Create KPI cards for the top of the report
    report_summary = get_report_summary(grand_total)

    return columns, data, None, None, report_summary


def get_columns(filters):
    """Returns columns dynamically depending on whether an animal filter is applied."""
    if filters.get("animal"):
        # Detailed daily log view for a single animal
        return [
            {"label": "Date", "fieldname": "date", "fieldtype": "Date", "width": 120},
            {"label": "Animal", "fieldname": "animal", "fieldtype": "Link", "options": "Animal", "width": 150},
            {"label": "Morning Yield (Ltrs)", "fieldname": "morning_yield", "fieldtype": "Float", "width": 150},
            {"label": "Evening Yield (Ltrs)", "fieldname": "evening_yield", "fieldtype": "Float", "width": 150},
            {"label": "Total Yield (Ltrs)", "fieldname": "total_yield", "fieldtype": "Float", "width": 180},
        ]
    else:
        # Aggregated summary view for all animals
        return [
            {"label": "Animal", "fieldname": "animal", "fieldtype": "Link", "options": "Animal", "width": 200},
            {"label": "Total Morning Yield (Ltrs)", "fieldname": "morning_yield", "fieldtype": "Float", "width": 200},
            {"label": "Total Evening Yield (Ltrs)", "fieldname": "evening_yield", "fieldtype": "Float", "width": 200},
            {"label": "Grand Total Yield (Ltrs)", "fieldname": "total_yield", "fieldtype": "Float", "width": 240},
        ]


def get_data(filters):
    """Builds query based on filters and processes row calculations."""
    conditions = ["parent.docstatus = 1"]
    query_values = {
        "from_date": filters.get("from_date"),
        "to_date": filters.get("to_date")
    }

    # Base date range conditions
    conditions.append("parent.date BETWEEN %(from_date)s AND %(to_date)s")

    if filters.get("animal"):
        conditions.append("child.animal = %(animal)s")
        query_values["animal"] = filters.get("animal")

        # View 1: Specific animal selected -> Fetch raw daily logs
        raw_data = frappe.db.sql(f"""
            SELECT 
                parent.date,
                child.animal,
                child.morning_yield,
                child.evening_yield,
                child.total_yield
            FROM `tabBulk Milking Item` child
            INNER JOIN `tabBulk Milking Log` parent ON child.parent = parent.name
            WHERE {" AND ".join(conditions)}
            ORDER BY parent.date ASC
        """, query_values, as_dict=True)

        grand_total = 0
        processed_rows = []
        for row in raw_data:
            m_yield = flt(row.morning_yield)
            e_yield = flt(row.evening_yield)
            t_yield = flt(row.total_yield) or (m_yield + e_yield)
            
            grand_total += t_yield
            processed_rows.append({
                "date": getdate(row.date),
                "animal": row.animal,
                "morning_yield": m_yield,
                "evening_yield": e_yield,
                "total_yield": t_yield
            })
            
        return processed_rows, grand_total

    else:
        # View 2: No animal selected -> Run SUM grouping by animal
        summary_data = frappe.db.sql(f"""
            SELECT 
                child.animal,
                SUM(CAST(child.morning_yield AS DECIMAL(10,2))) as morning_yield,
                SUM(CAST(child.evening_yield AS DECIMAL(10,2))) as evening_yield,
                SUM(CAST(child.total_yield AS DECIMAL(10,2))) as total_yield
            FROM `tabBulk Milking Item` child
            INNER JOIN `tabBulk Milking Log` parent ON child.parent = parent.name
            WHERE {" AND ".join(conditions)}
            GROUP BY child.animal
            ORDER BY total_yield DESC
        """, query_values, as_dict=True)

        grand_total = 0
        processed_rows = []
        for row in summary_data:
            m_yield = flt(row.morning_yield)
            e_yield = flt(row.evening_yield)
            t_yield = flt(row.total_yield) or (m_yield + e_yield)
            
            grand_total += t_yield
            processed_rows.append({
                "animal": row.animal,
                "morning_yield": m_yield,
                "evening_yield": e_yield,
                "total_yield": t_yield
            })

        return processed_rows, grand_total


def get_report_summary(grand_total):
    """Generates the top metric visualization block."""
    return [
        {
            "label": "Total Production in Period",
            "value": grand_total,
            "datatype": "Float",
            "indicator": "Green" if grand_total > 0 else "Red"
        }
    ]