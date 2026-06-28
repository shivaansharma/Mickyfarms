frappe.query_reports["Material Issue by Plot"] = {
	"filters": [
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company")
		},
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date"
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date"
		},
		{
			"fieldname": "cost_center",
			"label": __("Plot (Cost Center)"),
			"fieldtype": "Link",
			"options": "Cost Center",
			"get_query": function() {
				return {
					filters: {
						"custom_is_plot": 1
					}
				};
			}
		},
		{
			"fieldname": "item_code",
			"label": __("Item"),
			"fieldtype": "Link",
			"options": "Item"
		}
	]
};