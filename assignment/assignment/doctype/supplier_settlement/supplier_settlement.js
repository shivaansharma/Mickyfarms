frappe.ui.form.on('Supplier Settlement', {
    supplier: function(frm) {
        if (frm.doc.company && frm.doc.supplier) {
            // Fetch the live outstanding balance for the supplier
            frappe.call({
                method: 'erpnext.accounts.utils.get_balance_on',
                args: {
                    party_type: 'Supplier',
                    party: frm.doc.supplier,
                    company: frm.doc.company
                },
                callback: function(r) {
                    if (r.message !== undefined) {
                        // In ERPNext, a positive balance for a supplier means they owe you (Debit).
                        // A negative balance means you owe them (Credit). 
                        // We multiply by -1 so it makes sense to the client: Positive = We Owe.
                        frm.set_value('running_balance', r.message * -1);
                    }
                }
            });
        }
    }
});