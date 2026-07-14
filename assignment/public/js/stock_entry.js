frappe.ui.form.on("Stock Entry", {
    purpose: function(frm) {
        set_default_warehouse(frm);
    },
    refresh: function(frm) {
        set_default_warehouse(frm);
    }
});

frappe.ui.form.on("Stock Entry Detail", {
    items_add: function(frm, cdt, cdn) {
        copy_from_previous_row(frm, cdt, cdn);
    },
    item_code: function(frm, cdt, cdn) {
        // Intercepts and overwrites the default cost center fetched by ERPNext master data
        copy_from_previous_row(frm, cdt, cdn);
    }
});

function copy_from_previous_row(frm, cdt, cdn) {
    // A 200ms delay gives ERPNext core enough time to finish populating item defaults
    setTimeout(() => {
        let items = frm.doc.items || [];
        let current_index = items.findIndex(d => d.name === cdn);
        
        // If there is a valid row directly above us
        if (current_index > 0) {
            let previous_row = items[current_index - 1];
            
            if (previous_row && previous_row.cost_center) {
                frappe.model.set_value(cdt, cdn, "cost_center", previous_row.cost_center);
            }
        }
    }, 200);
}

function set_default_warehouse(frm) {
    var default_wh = "Stores - MF";

    if (frm.is_new()) {
        if (frm.doc.purpose === "Material Receipt" && !frm.doc.to_warehouse) {
            frm.set_value("to_warehouse", default_wh);
        } 
        else if (frm.doc.purpose === "Material Issue" && !frm.doc.from_warehouse) {
            frm.set_value("from_warehouse", default_wh);
        }
    }
}