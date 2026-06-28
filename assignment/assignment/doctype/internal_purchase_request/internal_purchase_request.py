import frappe
from frappe.model.document import Document
from frappe.utils import getdate, nowdate

class InternalPurchaseRequest(Document):
    def validate(self):
        if self.require_by_date and getdate(self.require_by_date) < getdate(nowdate()):
            frappe.throw("Required date cannot be in the past.")
        for item in self.items:
            if item.quantity <= 0:
                frappe.throw(f"Quantity must be greater than 0 for row {item.idx}")
            if item.estimated_rate <= 0:
                frappe.throw(f"Estimated rate must be greater than 0 for row {item.idx}")
            item.amount = item.quantity * item.estimated_rate
            
        if self.status == 'Rejected' and not self.approval_remarks:
            frappe.throw("Approval remarks are mandatory when rejecting a request.")

    def before_submit(self):
        self.status = "Pending Approval"

@frappe.whitelist()
def update_status(name, status, remarks=""):
    doc = frappe.get_doc("Internal Purchase Request", name)
    doc.db_set('status', status)
    if remarks:
        doc.db_set('approval_remarks', remarks)
    frappe.msgprint(f"Request {status}")

@frappe.whitelist()
def create_material_request(source_name):
    source_doc = frappe.get_doc("Internal Purchase Request", source_name)
    mr = frappe.new_doc("Material Request")
    mr.material_request_type = "Purchase"
    mr.transaction_date = nowdate()
    mr.schedule_date = source_doc.require_by_date
    
    for item in source_doc.items:
        mr.append("items", {
            "item_code": item.item_code,
            "qty": item.quantity,
            "schedule_date": source_doc.require_by_date
        })
        
    mr.insert()
    source_doc.db_set('material_request', mr.name)
    source_doc.db_set('status', 'Converted')
    
    frappe.msgprint(f"Material Request {mr.name} created successfully.")
    return mr.name