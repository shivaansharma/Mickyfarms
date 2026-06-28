// Copyright (c) 2024, Your Name/Company and contributors
// For license information, please see license.txt

frappe.query_reports["Internal Purchase Request Tracking"] = {
	"filters": [
		{
			"fieldname": "status",
			"label": __("Status"),
			"fieldtype": "Select",
			"options": "\nDraft\nPending Approval\nApproved\nRejected\nConverted",
			"width": "80"
		},
		{
			"fieldname": "department",
			"label": __("Department"),
			"fieldtype": "Link",
			"options": "Department",
			"width": "80"
		}
	]
};