# Copyright (c) 2026, shivaan and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class BulkMilkingLog(Document):
    def validate(self):
        # Calculate totals safely converting input strings to numbers
        total = 0.0
        for row in self.milking_rows:
            morning = flt(row.morning_yield)
            evening = flt(row.evening_yield)
            
            row.total_yield = morning + evening
            total += row.total_yield
            
        # Aligned to your JSON field name: total_milk
        self.total_milk = total

    def on_submit(self):
        if flt(self.total_milk) <= 0:
            frappe.throw(_("Total milk yield must be greater than 0 to create a Stock Entry."))

        # Aligned to your JSON field name: milk_type
        if not self.milk_type:
            frappe.throw(_("Please select a Milk Type before submitting."))

        # Ensure that whatever string is entered into milk_type exists as an Item
        if not frappe.db.exists("Item", self.milk_type):
            frappe.throw(_("The Milk Type '{0}' does not exist as a registered Item Code.").format(self.milk_type))

        target_warehouse = "Stores - MF"
        
        if not frappe.db.exists("Warehouse", target_warehouse):
            frappe.throw(_("The warehouse '{0}' does not exist. Please check your inventory setup.").format(target_warehouse))

        # Create the Material Receipt
        stock_entry = frappe.new_doc("Stock Entry")
        stock_entry.stock_entry_type = "Material Receipt"
        stock_entry.posting_date = self.date
        
        stock_entry.append("items", {
            "item_code": self.milk_type,       # Map milk_type to item_code
            "t_warehouse": target_warehouse,
            "qty": flt(self.total_milk),       # Map total_milk to qty
            "uom": frappe.db.get_value("Item", self.milk_type, "stock_uom") or "Litre",
            "basic_rate": flt(frappe.db.get_value("Item", self.milk_type, "valuation_rate")) or 0.00,
			"allow_zero_valuation_rate": 1  
        })
        
        stock_entry.insert()
        stock_entry.submit()
        
        frappe.msgprint(_("Stock Entry {0} has been posted for {1} liters of {2} into {3}.").format(
            stock_entry.name,
            self.total_milk,
            self.milk_type,
            target_warehouse
        ))

    def on_cancel(self):
        target_warehouse = "Stores - MF"
        
        linked_se = frappe.get_all("Stock Entry Detail", 
            filters={"item_code": self.milk_type, "t_warehouse": target_warehouse, "qty": flt(self.total_milk)},
            fields=["parent"], limit=1)
            
        if linked_se:
            se_doc = frappe.get_doc("Stock Entry", linked_se[0].parent)
            if se_doc.docstatus == 1:
                se_doc.cancel()
                frappe.msgprint(_("Linked Stock Entry {0} has been cancelled.").format(se_doc.name))