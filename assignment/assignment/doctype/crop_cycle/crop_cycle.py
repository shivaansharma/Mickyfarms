# Copyright (c) 2026, shivaan and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class CropCycle(Document):
    def on_submit(self):
        """When the Crop Cycle is submitted, lock the plots."""
        if not self.plots:
            return
            
        for row in self.plots:
            if row.plot:
                frappe.db.set_value('Plot', row.plot, 'status', 'Assigned')
        
        frappe.db.commit()

    def on_cancel(self):
        """When the Crop Cycle is cancelled, free up the plots back to Free."""
        if not self.plots:
            return
            
        for row in self.plots:
            if row.plot:
                frappe.db.set_value('Plot', row.plot, 'status', 'Free')
                
        frappe.db.commit()

    @frappe.whitelist()
    def harvest_plots(self):
        """Custom method triggered by the 'Harvest' button to free plots."""
        if not self.plots:
            return

        # 1. Free up the plots
        for row in self.plots:
            if row.plot:
                frappe.db.set_value('Plot', row.plot, 'status', 'Free')
        
        # 2. Update the status of this Crop Cycle document
        self.db_set('status', 'Harvested')
        
        frappe.db.commit()
        frappe.msgprint("✅ Associated plots have been freed successfully.")