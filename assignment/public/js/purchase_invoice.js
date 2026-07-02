frappe.ui.form.on('Purchase Invoice', {
    onload(frm) {
        if (frm.is_new()) {
            frm.set_value('update_stock', 1);
        }
    },

    refresh(frm) {
        if (frm.is_new() && !frm.doc.update_stock) {
            frm.set_value('update_stock', 1);
        }
    },

    items_add(frm, cdt, cdn) {
        frappe.model.set_value(cdt, cdn, 'warehouse', 'Stores - MF');
    }
});

frappe.ui.form.on('Purchase Invoice Item', {
    item_code(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (!row.warehouse) {
            frappe.model.set_value(cdt, cdn, 'warehouse', 'Stores - MF');
        }
    }
});