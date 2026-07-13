frappe.query_reports["Milk Production Report"] = {
	"filters": [
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
			"default": frappe.datetime.get_today(),
			"reqd": 1
		},
		{
			"fieldname": "animal",
			"label": __("Animal (Cow)"),
			"fieldtype": "Link",
			"options": "Animal",
			"description": __("Leave empty to see overall total for all cows")
		}
	]
};