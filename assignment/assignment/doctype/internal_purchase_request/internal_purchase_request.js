frappe.ui.form.on('Internal Purchase Request', {
    refresh: function(frm) {
        // frm.toggle_display('approval_remarks', frm.doc.status === 'Rejected');

        if (frm.doc.docstatus === 1 && frm.doc.status === 'Pending Approval') {
            if (frappe.user.has_role('Manager') || frappe.user.has_role('System Manager')) {
                frm.add_custom_button('Approve', () => update_status(frm, 'Approved'), 'Actions');
                frm.add_custom_button('Reject', () => prompt_for_rejection(frm), 'Actions');
            }
        }

        if (frm.doc.status === 'Approved' && !frm.doc.material_request) {
            frm.add_custom_button('Create Material Request', () => {
                frappe.call({
                    method: 'assignment.assignment.doctype.internal_purchase_request.internal_purchase_request.create_material_request',
                    args: { source_name: frm.doc.name },
                    callback: function(r) {
                        if (!r.exc) frm.reload_doc();
                    }
                });
            });
        }
    }
});


frappe.ui.form.on('Internal Purchase Request Item', {
    qty: function(frm, cdt, cdn) { calculate_amount(frm, cdt, cdn); },
    estimated_rate: function(frm, cdt, cdn) { calculate_amount(frm, cdt, cdn); }
});

function calculate_amount(frm, cdt, cdn) {
    let row = frappe.get_doc(cdt, cdn);
    if (row.qty && row.estimated_rate) {
        frappe.model.set_value(cdt, cdn, 'amount', row.qty * row.estimated_rate);
    }
}

function update_status(frm, status, remarks="") {
    frappe.call({
        method: 'assignment.assignment.doctype.internal_purchase_request.internal_purchase_request.update_status',
        args: { name: frm.doc.name, status: status, remarks: remarks },
        callback: function(r) {
            if (!r.exc) frm.reload_doc();
        }
    });
}

function prompt_for_rejection(frm) {
    frappe.prompt([
        { label: 'Reason for Rejection', fieldname: 'remarks', fieldtype: 'Text', reqd: 1 }
    ], (values) => {
        update_status(frm, 'Rejected', values.remarks);
    }, 'Reject Request', 'Submit');
}