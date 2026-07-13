frappe.ui.form.on('Employee Contract', {
    onload: function(frm) {
        // 1. FILTER: Only show Cost Centers marked as plots in the child table
        frm.set_query('plot', 'assigned_plots', function() {
            return {
                filters: {
                    'custom_is_plot': 1,
                    'company': frm.doc.company || ["!=", ""]
                }
            };
        });
    },

    refresh: function(frm) {
        // Dynamic Pay Balance button shows up ONLY after submission and if there is money left to pay
        if (frm.doc.docstatus === 1 && flt(frm.doc.net_payable_amount) > 0) {
            frm.add_custom_button(__('Pay Remaining Balance'), function() {
                frappe.new_doc('Payment Entry', {
                    'payment_type': 'Pay',
                    'party_type': 'Supplier',
                    'party': frm.doc.employee,
                    'paid_amount': frm.doc.net_payable_amount,
                    'reference_no': frm.doc.name,
                    'paid_from': 'Cash - MF',
                    'paid_to': 'Creditors - MF',
                    'company': frm.doc.company
                });
            }, __('Actions'));
        }
    },

    // Recalculate if the base rate changes
    rate_per_acre: function(frm) {
        calculate_totals(frm);
    },

    // Recalculate if the advance fee changes
    pay_advance: function(frm) {
        calculate_totals(frm);
    }
});

// Child Table Event Listeners
frappe.ui.form.on('Employee Contract Plot', {
    // 2. AUTO-FETCH AREA: Pull custom_area when a plot is chosen
    plot: function(frm, cdt, cdn) {
        let row = frappe.get_doc(cdt, cdn);
        if (row.plot) {
            frappe.db.get_value('Cost Center', row.plot, 'custom_area', (r) => {
                if (r && r.custom_area) {
                    frappe.model.set_value(cdt, cdn, 'area', flt(r.custom_area));
                } else {
                    frappe.model.set_value(cdt, cdn, 'area', 0);
                }
                calculate_totals(frm);
            });
        } else {
            frappe.model.set_value(cdt, cdn, 'area', 0);
            calculate_totals(frm);
        }
    },

    // Recalculate if someone overrides an individual row area manually
    area: function(frm, cdt, cdn) {
        calculate_totals(frm);
    },

    // Recalculate if a row is removed
    assigned_plots_remove: function(frm) {
        calculate_totals(frm);
    }
});

// Core Calculation Logic
function calculate_totals(frm) {
    let total_area = 0;

    // Sum up the areas of all assigned plots
    (frm.doc.assigned_plots || []).forEach(row => {
        total_area += flt(row.area);
    });

    // Update aggregate area field if it exists on main form
    if (frm.meta.has_field('total_area')) {
        frm.set_value('total_area', total_area);
    }

    // Calculations based on the dynamic sum
    let total_payout = flt(frm.doc.rate_per_acre) * total_area;
    
    // Total outlays to factor out include advance + what was cleared before
    let total_deductions = flt(frm.doc.pay_advance) + flt(frm.doc.total_paid_already);
    let net_payable = total_payout - total_deductions;

    frm.set_value('total_payout_amount', total_payout);
    frm.set_value('net_payable_amount', net_payable);
}