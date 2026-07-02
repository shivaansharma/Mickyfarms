frappe.ui.form.on("Stock Entry", {
    purpose: function(frm) {
        set_default_warehouse(frm);
    },
    refresh: function(frm) {
        set_default_warehouse(frm);
    }
});

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