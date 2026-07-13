frappe.ui.form.on('Supplier Settlement', {
    supplier: function(frm) { fetch_total(frm); },
    company: function(frm) { fetch_total(frm); }
});

var fetch_total = function(frm) {
    if (frm.doc.company && frm.doc.supplier) {
        frappe.call({
            // Ensure this path matches your actual file structure!
            method: 'assignment.assignment.doctype.supplier_settlement.supplier_settlement.get_aggregated_outstanding',
            args: {
                supplier: frm.doc.supplier,
                company: frm.doc.company
            },
            callback: function(r) {
                if (r.message !== undefined) {
                    // This will display the aggregated sum of all outstanding invoices
                    frm.set_value('running_balance', r.message);
                }
            }
        });
    } else {
        frm.set_value('running_balance', 0);
    }
};