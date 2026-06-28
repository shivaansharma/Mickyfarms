frappe.ui.form.on('Employee Contract', {
    refresh: function(frm) {
        // 1. Filter Cost Centers
        frm.set_query('plot', 'assigned_plots', function() {
            return {
                filters: { 'custom_is_plot': 1 }
            };
        });

        // Dashboard action payment generator button
        if (!frm.is_new() && frm.doc.total_payout_amount > 0) {
            frm.add_custom_button(__('Create Payment'), function() {
                
                let first_row = frm.doc.assigned_plots ? frm.doc.assigned_plots[0] : null;
                if (!first_row || !first_row.plot) {
                    frappe.msgprint(__('Please add at least one Plot row before generating a payment.'));
                    return;
                }
                
                frappe.db.get_value('Cost Center', first_row.plot, 'company')
                    .then(r => {
                        let target_company = r.message ? r.message.company : "";
                        let rate = flt(frm.doc.rate_per_acre);
                        
                        // We will build the split rows for the multi-cost-center allocation
                        let deduction_rows = [];
                        
                        $.each(frm.doc.assigned_plots || [], function(i, row) {
                            let row_cost = flt(row.area) * rate;
                            if (row_cost > 0) {
                                deduction_rows.push({
                                    "account": "contract - MF", // <-- Your Expense/Liability Account
                                    "cost_center": row.plot,                 // <-- Individual Plot Cost Center
                                    "amount": row_cost,                      // <-- Cost calculated for THIS plot
                                    "description": __("Acreage cost split for {0} ({1} Acres)", [row.plot, row.area])
                                });
                            }
                        });

                        frappe.call({
                            method: "frappe.client.insert",
                            args: {
                                doc: {
                                    "doctype": "Payment Entry",
                                    "payment_type": "Pay",
                                    "party_type": "Employee",
                                    "party": frm.doc.employee,
                                    "paid_amount": flt(frm.doc.total_payout_amount),
                                    "received_amount": flt(frm.doc.total_payout_amount),
                                    "reference_no": frm.doc.name,
                                    "reference_date": frappe.datetime.get_today(),
                                    "company": target_company,
                                    
                                    // Primary fallbacks required by system validation rules
                                    "cost_center": first_row.plot, 
                                    "paid_from": "Cash - MF", 
                                    "paid_to": "Employee Advances - MF",
                                    
                                    "paid_from_currency": "INR",
                                    "paid_to_currency": "INR",
                                    "source_exchange_rate": flt(1.0),
                                    "target_exchange_rate": flt(1.0),
                                    "base_paid_amount": flt(frm.doc.total_payout_amount),
                                    "base_received_amount": flt(frm.doc.total_payout_amount),

                                    // NEW: Multi-cost center allocation split data array
                                    "deductions": deduction_rows 
                                }
                            },
                            callback: function(r) {
                                if(!r.exc) {
                                    frappe.show_alert({message: __('Multi-plot Payment Entry Created Successfully!'), indicator: 'green'});
                                    frappe.set_route('Form', 'Payment Entry', r.message.name);
                                }
                            }
                        });
                    });
            }, __('Actions'));
        }
    },
    
    employee: function(frm) {
        if (frm.doc.employee) {
            frappe.db.get_value('Employee', frm.doc.employee, 'employee_name', (r) => {
                if (r && r.employee_name) {
                    frm.set_value('employee_name', r.employee_name);
                }
            });
        }
    },
    
    rate_per_acre: function(frm) {
        calculate_totals(frm);
    }
});

frappe.ui.form.on('Employee Contract Plot', {
    plot: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.plot) {
            frappe.db.get_value('Cost Center', row.plot, 'custom_area')
                .then(r => {
                    let area_val = r.message ? r.message.custom_area : 0;
                    frappe.model.set_value(cdt, cdn, 'area', flt(area_val));
                    calculate_totals(frm);
                });
        }
    },
    area: function(frm, cdt, cdn) {
        calculate_totals(frm);
    },
    assigned_plots_remove: function(frm) {
        calculate_totals(frm);
    }
});

function calculate_totals(frm) {
    let total_area = 0;
    $.each(frm.doc.assigned_plots || [], function(i, row) {
        total_area += flt(row.area);
    });
    
    let rate = flt(frm.doc.rate_per_acre);
    let total_payout = total_area * rate;
    
    frm.set_value('total_contracted_area', total_area);
    frm.set_value('total_payout_amount', total_payout);
}