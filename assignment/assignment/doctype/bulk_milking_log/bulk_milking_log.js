frappe.ui.form.on("Bulk Milking Log", {
    refresh(frm) {
        frm.add_custom_button(__("Get Animals"), () => {
            frappe.call({
                method: "frappe.client.get_list",
                args: {
                    doctype: "Animal",
                    filters: {
                        status: "Active",
                        lactation_status: "Milking"
                    },
                    fields: [
                        "name",
                        "name1" // Pulling your exact custom identity label field
                    ],
                    order_by: "name1 asc"
                },
                callback(r) {
                    if (!r.message || !r.message.length) {
                        frappe.msgprint(__("No active milking animals found."));
                        return;
                    }

                    frm.clear_table("milking_rows");

                    r.message.forEach(animal => {
                        let row = frm.add_child("milking_rows");
                        // Maps the true database document key link
                        row.animal = animal.name; 
                        // Populates the descriptive label column with your custom title
                        row.animal_name = animal.name1; 
                    });

                    frm.refresh_field("milking_rows");
                    update_document_total(frm);
                }
            });
        }, __("Actions"));
    }
});

frappe.ui.form.on("Bulk Milking Item", {
    morning_yield(frm, cdt, cdn) {
        update_row(frm, cdt, cdn);
    },

    evening_yield(frm, cdt, cdn) {
        update_row(frm, cdt, cdn);
    }
});

function update_row(frm, cdt, cdn) {
    let row = locals[cdt][cdn];

    let morning = parseFloat(row.morning_yield) || 0;
    let evening = parseFloat(row.evening_yield) || 0;
    let total = morning + evening;

    frappe.model.set_value(cdt, cdn, "total_yield", total);

    update_document_total(frm);
}

function update_document_total(frm) {
    let total = 0;

    (frm.doc.milking_rows || []).forEach(row => {
        total += parseFloat(row.total_yield) || 0;
    });

    // Make sure your parent doctype uses one of these matching target fields
    let target_field = frm.meta.fields.find(f => f.fieldname === "total_milk") ? "total_milk" : "total_farm_yield";
    
    frm.set_value(target_field, total);
    frm.refresh_field(target_field);
}