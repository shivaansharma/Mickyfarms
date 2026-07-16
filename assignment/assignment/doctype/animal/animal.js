frappe.ui.form.on('Animal Pregnancy Log', {
    breading_date: function(frm, cdt, cdn) {
        let row = frappe.get_doc(cdt, cdn);
        
        if (row.breading_date && !row.delivery_date) {
            frm.set_value('lactation_status', 'Pregnant');
            
            if (frm.doc.animal_type === 'Heifer') {
                frm.set_value('animal_type', 'Cow'); 
                frm.refresh_field('animal_type');
            }
            frm.refresh_field('lactation_status');
        }
    },
    
    delivery_date: function(frm, cdt, cdn) {
        let row = frappe.get_doc(cdt, cdn);
        
        if (row.delivery_date) {
            // If they gave birth but we explicitly left milk_start_date empty, it's Dry
            if (!row.milk_start_date) {
                frm.set_value('lactation_status', 'Dry');
            } else if (!row.dry_date) {
                frm.set_value('lactation_status', 'Milking');
            }
            frm.refresh_field('lactation_status');
        }
    },

    milk_start_date: function(frm, cdt, cdn) {
        let row = frappe.get_doc(cdt, cdn);
        
        // If a milking date is added, instantly switch to Milking unless a dry date is already present
        if (row.milk_start_date && !row.dry_date) {
            frm.set_value('lactation_status', 'Milking');
        } else if (!row.milk_start_date && row.delivery_date) {
            frm.set_value('lactation_status', 'Dry');
        }
        frm.refresh_field('lactation_status');
    },

    dry_date: function(frm, cdt, cdn) {
        let row = frappe.get_doc(cdt, cdn);
        if (row.dry_date) {
            frm.set_value('lactation_status', 'Dry');
            frm.refresh_field('lactation_status');
        }
    }
});