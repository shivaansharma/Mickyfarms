# Copyright (c) 2026, shivaan and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt, getdate


def execute(filters=None):
    filters = filters or {}

    # 1. Validate mandatory date filters
    if not filters.get("from_date") or not filters.get("to_date"):
        frappe.throw("Please select both From Date and To Date.")

    # 2. Dynamically set columns based on selection
    columns = get_columns(filters)

    # 3. Retrieve and aggregate animal expenses
    data, grand_total = get_data(filters)

    # 4. Generate summary metric card
    report_summary = get_report_summary(grand_total)

    return columns, data, None, None, report_summary


def get_columns(filters):
    """Returns columns dynamically depending on whether an animal filter is applied."""
    if filters.get("animal"):
        # Detailed medical history for a single animal
        return [
            {"label": "Posting Date", "fieldname": "posting_date", "fieldtype": "Date", "width": 110},
            {"label": "Log Reference", "fieldname": "name", "fieldtype": "Link", "options": "Doctor Log", "width": 130},
            {"label": "Doctor / Supplier", "fieldname": "doctor", "fieldtype": "Link", "options": "Supplier", "width": 150},
            {"label": "Description", "fieldname": "description", "fieldtype": "Data", "width": 280},
            {"label": "Invoice Linked", "fieldname": "purchase_invoice", "fieldtype": "Link", "options": "Purchase Invoice", "width": 180},
            {"label": "Cost", "fieldname": "cost", "fieldtype": "Currency", "width": 130},
        ]
    else:
        # Aggregated medical summary view across all cows
        return [
            {"label": "Animal", "fieldname": "animal", "fieldtype": "Link", "options": "Animal", "width": 220},
            {"label": "Total Treatments", "fieldname": "total_treatments", "fieldtype": "Int", "width": 160},
            {"label": "Total Medical Cost", "fieldname": "total_cost", "fieldtype": "Currency", "width": 200},
        ]


def get_data(filters):
    """Queries data based on filters and handles row transformations."""
    conditions = ["docstatus = 1"]
    query_values = {
        "from_date": filters.get("from_date"),
        "to_date": filters.get("to_date")
    }

    # Add date conditions
    conditions.append("posting_date BETWEEN %(from_date)s AND %(to_date)s")

    # Add company filter if present
    if filters.get("company"):
        conditions.append("company = %(company)s")
        query_values["company"] = filters.get("company")

    if filters.get("animal"):
        conditions.append("animal = %(animal)s")
        query_values["animal"] = filters.get("animal")

        # View 1: Specific Cow Selected -> Show itemized daily treatment history
        raw_logs = frappe.db.sql(f"""
            SELECT 
                name,
                posting_date,
                doctor,
                description,
                purchase_invoice,
                cost
            FROM `tabDoctor Log`
            WHERE {" AND ".join(conditions)}
            ORDER BY posting_date ASC
        """, query_values, as_dict=True)

        grand_total = 0
        processed_rows = []
        for log in raw_logs:
            log_cost = flt(log.cost)
            grand_total += log_cost

            processed_rows.append({
                "posting_date": getdate(log.posting_date),
                "name": log.name,
                "doctor": log.doctor,
                "description": log.description,
                "purchase_invoice": log.purchase_invoice,
                "cost": log_cost
            })

        return processed_rows, grand_total

    else:
        # View 2: No Cow Selected -> Show running group metrics per animal
        summary_logs = frappe.db.sql(f"""
            SELECT 
                animal,
                COUNT(name) as total_treatments,
                SUM(CAST(cost AS DECIMAL(10,2))) as total_cost
            FROM `tabDoctor Log`
            WHERE {" AND ".join(conditions)}
            GROUP BY animal
            ORDER BY total_cost DESC
        """, query_values, as_dict=True)

        grand_total = 0
        processed_rows = []
        for summary in summary_logs:
            t_cost = flt(summary.total_cost)
            grand_total += t_cost

            processed_rows.append({
                "animal": summary.animal,
                "total_treatments": summary.total_treatments,
                "total_cost": t_cost
            })

        return processed_rows, grand_total


def get_report_summary(grand_total):
    """Renders dashboard KPI card block at the top."""
    return [
        {
            "label": "Total Herd Medical Expense",
            "value": grand_total,
            "datatype": "Currency",
            "indicator": "Red" if grand_total > 0 else "Green"
        }
    ]