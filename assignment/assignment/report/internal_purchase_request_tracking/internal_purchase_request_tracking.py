# Copyright (c) 2024, Your Name/Company and contributors
# For license information, please see license.txt

import frappe

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {
            "fieldname": "name",
            "label": "ID",
            "fieldtype": "Link",
            "options": "Internal Purchase Request",
            "width": 180
        },
        {
            "fieldname": "employee",
            "label": "Employee",
            "fieldtype": "Link",
            "options": "Employee",
            "width": 150
        },
        {
            "fieldname": "department",
            "label": "Department",
            "fieldtype": "Link",
            "options": "Department",
            "width": 150
        },
        {
            "fieldname": "status",
            "label": "Status",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "fieldname": "require_by_date",
            "label": "Required Date",
            "fieldtype": "Date",
            "width": 120
        }
    ]

def get_data(filters):
    # Build dynamic conditions based on what the user selects in the filters
    conditions = {}
    
    if filters:
        if filters.get("status"):
            conditions["status"] = filters.get("status")
        if filters.get("department"):
            conditions["department"] = filters.get("department")

    # Fetch the data from the database using Frappe's ORM
    data = frappe.get_all(
        "Internal Purchase Request",
        filters=conditions,
        fields=["name", "employee", "department", "status", "require_by_date"],
        order_by="creation desc"
    )
    
    return data