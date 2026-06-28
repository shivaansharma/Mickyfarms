// Copyright (c) 2026, shivaan and contributors
// For license information, please see license.txt

frappe.ui.form.on("Crop Cycle", {
    validate(frm) {
        // 1. FIXED: Corrected spelling from 'promies' to 'promises'
        let promises = []; 
        
        if (frm.doc.plots && frm.doc.plots.length > 0) {
            frm.doc.plots.forEach(row => {
                // 2. FIXED: Checking for row.plot (the actual Plot field) instead of row.name
                if (row.plot) { 
                    let p = frappe.db.get_value('Plot', row.plot, 'status')
                        .then(r => {
                            let status = r.message ? r.message.status : null;
                            if (status === 'Assigned') {
                                // 3. FIXED: Used frappe.validated = false to properly halt Frappe's save process
                                frappe.msgprint(`❌ Plot <b>${row.plot}</b> is already assigned.`);
                                frappe.validated = false; 
                            }
                        });
                    promises.push(p);
                }
            });
        }
        
        if (promises.length > 0) {
            return Promise.all(promises);
        }
    }
});

// Copyright (c) 2026, shivaan and contributors
// For license information, please see license.txt

frappe.ui.form.on("Crop Cycle", {
    refresh(frm) {
        // Show the Harvest button ONLY if the document is Submitted (docstatus == 1)
        // and hasn't already been marked as fully harvested/completed
        if (frm.doc.docstatus === 1 && frm.doc.status !== 'Harvested') {
            frm.add_custom_button(__('Harvest Crop'), () => {
                frm.trigger('process_harvest');
            }, __('Actions'));
        }
    },

    process_harvest(frm) {
        frappe.confirm(
            __('Are you sure you want to harvest this cycle? This will free up the assigned plots.'),
            () => {
                // 1. Call the backend Python method to free up the plots
                frappe.call({
                    method: 'harvest_plots', // Maps to the Python method
                    doc: frm.doc,
                    callback: function(r) {
                        if (!r.exc) {
                            // 2. Open the Stock Entry popup (Material Receipt) for the harvest
                            frappe.model.make_mapped_doc({
                                method: "erpnext.stock.doctype.stock_entry.stock_entry.make_stock_entry",
                                source_name: frm.doc.name,
                                target_doctype: "Stock Entry",
                                freeze: true,
                                callback: function(target_doc) {
                                    // Pre-set Stock Entry details if needed
                                    target_doc.purpose = "Material Receipt";
                                    frappe.set_route("Form", "Stock Entry", target_doc.name);
                                }
                            });
                            
                            // Refresh the form to show updated status
                            frm.reload_doc();
                        }
                    }
                });
            }
        );
    }
});