// Copyright (c) 2026, shivaan and contributors
// For license information, please see license.txt

frappe.query_reports["Milk Payment Summary Report"] = {
    "filters": [
        {
            "fieldname": "company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "default": frappe.defaults.get_user_default("Company"),
            "reqd": 1
        },
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.month_start(),
            "reqd": 1
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.month_end(),
            "reqd": 1
        },
        {
            "fieldname": "customer",
            "label": __("Customer"),
            "fieldtype": "Link",
            "options": "Customer",
            "get_query": function() {
                return {
                    filters: {
                        "custom_is_milk_customer": 1
                    }
                };
            }
        }
    ],
    
    // Formatting: Color code balances for readability
    "formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        
        // Color coding for Net Position / Outstanding Balances
        if (column.fieldname === "net_balance" || column.fieldname === "outstanding_balance") {
            if (data[column.fieldname] > 0) {
                value = `<span style="color:red">${value}</span>`;
            } else if (data[column.fieldname] < 0) {
                value = `<span style="color:green">${value}</span>`;
            }
        }
        
        // Highlight the Total Row
        if (data.customer_name === "<b>TOTALS</b>" || data.tx_type === "<b>LIVE ACCOUNT TOTALS</b>") {
            return `<b>${value}</b>`;
        }
        
        return value;
    }
};