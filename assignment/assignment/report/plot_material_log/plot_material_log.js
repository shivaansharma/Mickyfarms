frappe.query_reports["Plot Material Log"] = {
	"filters": [
		{
			"fieldname": "cost_center",
			"label": __("Filter Specific Plot"),
			"fieldtype": "Link",
			"options": "Cost Center",
			"get_query": function() {
				return {
					filters: {
						"custom_is_plot": 1   
					}
				};
			}
		}
	]
};