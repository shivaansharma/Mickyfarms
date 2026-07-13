import frappe
from frappe.model.document import Document
from frappe.utils import nowdate

class DoctorLog(Document):
    def on_submit(self):
        self.create_purchase_invoice()

    def create_purchase_invoice(self):
        # Prevent duplicate invoices if one already exists
        if self.get("is_invoiced") or self.get("purchase_invoice"):
            return

        # 1. Initialize the new Purchase Invoice
        pi = frappe.new_doc("Purchase Invoice")
        pi.supplier = self.doctor
        pi.company = self.company
        pi.posting_date = self.posting_date or nowdate()
        pi.set_posting_time = 1
        pi.remarks = f"Auto-generated for Vet Services from Doctor Log: {self.name}"
        
        # 2. Add the service details as an item row
        pi.append("items", {
            "item_name": f"Vet Services for {self.animal}",
            "description": f"Health check/treatment for {self.animal}. Log Reference: {self.name}",
            "qty": 1,
            "rate": self.cost,
            "expense_account": self.expense_account
        })

        # 3. Save and submit the invoice to the general ledger
        pi.insert(ignore_permissions=True)
        pi.submit()

        # 4. Link the generated invoice back to this Doctor Log
        self.db_set("is_invoiced", 1)
        self.db_set("purchase_invoice", pi.name)

        # 5. Show a clickable success message to the user
        frappe.msgprint(
            f"Purchase Invoice <a href='/app/purchase-invoice/{pi.name}'><b>{pi.name}</b></a> created successfully.", 
            alert=True, 
            indicator="green"
        )

    def on_cancel(self):
        # Optional: Warn the user if they cancel a log that has an active invoice
        if self.purchase_invoice:
            pi_doc = frappe.get_doc("Purchase Invoice", self.purchase_invoice)
            if pi_doc.docstatus == 1:
                frappe.throw(f"You must cancel the linked Purchase Invoice ({self.purchase_invoice}) before canceling this log.")