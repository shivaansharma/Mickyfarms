# Copyright (c) 2026, shivaan and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import nowdate, flt
from erpnext.accounts.party import get_party_account


class SupplierSettlement(Document):
    def on_submit(self):
        # 0. Cast the incoming string payload to a safe float
        safe_payment_amount = flt(self.payment_amount)

        # Ensure payment amount is valid
        if safe_payment_amount <= 0:
            frappe.throw("Payment Amount must be greater than zero.")

        if not self.supplier:
            frappe.throw("Supplier is mandatory.")

        if not self.payment_account:
            frappe.throw("Payment Account is mandatory.")

        # 1. Initialize a new native Payment Entry
        pe = frappe.new_doc("Payment Entry")
        pe.payment_type = "Pay"
        pe.party_type = "Supplier"
        pe.party = self.supplier
        pe.company = self.company
        pe.paid_from = self.payment_account
        pe.paid_amount = safe_payment_amount
        pe.received_amount = safe_payment_amount
        pe.mode_of_payment = self.mode_of_payment
        pe.reference_no = self.name  # Link back to this custom document
        pe.reference_date = self.posting_date if getattr(self, "posting_date", None) else nowdate()

        # Fetch the correct payable account for this supplier/company
        pe.paid_to = get_party_account("Supplier", self.supplier, self.company)

        # 2. Fetch all outstanding Purchase Invoices for this Supplier (FIFO Order)
        outstanding_invoices = frappe.get_all(
            "Purchase Invoice",
            filters={
                "supplier": self.supplier,
                "company": self.company,
                "docstatus": 1,
                "outstanding_amount": (">", 0),
            },
            fields=["name", "outstanding_amount", "posting_date"],
            order_by="posting_date asc",  # This enforces First-In, First-Out
        )
        
        # Tag doctype for the merged list below
        for d in outstanding_invoices: d["doctype"] = "Purchase Invoice"

        # --- NEW: ADD DOCTOR LOG SUPPORT ---
        # Fetch all outstanding Doctor Logs (Assumes you have an 'outstanding_amount' field)
        outstanding_doctor_logs = frappe.get_all(
            "Doctor Log",
            filters={
                "doctor": self.supplier, # Assuming doctor link matches the supplier ID
                "company": self.company,
                "docstatus": 1,
                # "outstanding_amount": (">", 0),
            },
            fields=["name", "posting_date"],
            order_by="posting_date asc",
        )
        
        # Tag doctype for the merged list
        for d in outstanding_doctor_logs: d["doctype"] = "Doctor Log"

        # Merge and sort both lists by posting_date to maintain true FIFO across both types
        all_outstanding = outstanding_invoices + outstanding_doctor_logs
        all_outstanding.sort(key=lambda x: x.posting_date if x.posting_date else nowdate())
        # -----------------------------------

        # 3. Allocate the lump sum to the invoices/logs
        allocated_amount = 0

        for inv in all_outstanding:
            if allocated_amount >= safe_payment_amount:
                break  # Money has run out

            remaining_funds = safe_payment_amount - allocated_amount
            amount_to_allocate = min(flt(inv.outstanding_amount), remaining_funds)

            pe.append("references", {
                "reference_doctype": inv.doctype, # Dynamic: Purchase Invoice or Doctor Log
                "reference_name": inv.name,
                "allocated_amount": amount_to_allocate,
            })

            allocated_amount += amount_to_allocate

        # 4. Save and Submit the standard Payment Entry
        try:
            pe.insert(ignore_permissions=True)
            pe.submit()
        except Exception:
            frappe.db.rollback()
            frappe.throw(
                f"Failed to create the Payment Entry for this settlement: {frappe.get_traceback()}"
            )

        # Store the link directly in the DB (this doc is already submitted
        # at this point in the save lifecycle, so we use db_set rather than
        # re-saving the whole document)
        self.db_set("payment_entry", pe.name, update_modified=False)

        frappe.msgprint(
            f"Success! A native Payment Entry ({pe.name}) was created and allocated automatically.",
            alert=True,
        )

    def on_cancel(self):
        # Prefer the stored link; fall back to a lookup by reference_no for
        # any settlements submitted before the payment_entry field existed
        payment_entry_name = self.payment_entry or frappe.db.get_value(
            "Payment Entry",
            {
                "reference_no": self.name,
                "party_type": "Supplier",
                "party": self.supplier,
            },
            "name",
        )

        if not payment_entry_name:
            frappe.msgprint(
                "No linked Payment Entry was found for this settlement; nothing to cancel.",
                alert=True,
            )
            return

        pe = frappe.get_doc("Payment Entry", payment_entry_name)

        if pe.docstatus == 2:
            # Already cancelled (e.g. manually, outside this flow) - nothing more to do
            return

        try:
            pe.cancel()
        except Exception:
            frappe.db.rollback()
            frappe.throw(
                f"Could not cancel the linked Payment Entry {pe.name}: {frappe.get_traceback()}"
            )

        frappe.msgprint(
            f"Linked Payment Entry ({pe.name}) was cancelled along with this settlement.",
            alert=True,
        )

@frappe.whitelist()
def get_aggregated_outstanding(supplier, company):
    inv_total = frappe.db.sql("""
        SELECT SUM(outstanding_amount) 
        FROM `tabPurchase Invoice` 
        WHERE supplier=%s AND company=%s AND docstatus=1
    """, (supplier, company))[0][0] or 0

    con_total = frappe.db.sql("""
        SELECT SUM(net_payable_amount) 
        FROM `tabEmployee Contract` 
        WHERE employee=%s AND company=%s AND docstatus=1
    """, (supplier, company))[0][0] or 0

    # --- NEW: ADD DOCTOR LOG SUPPORT ---
    # doc_total = frappe.db.sql("""
    #     SELECT SUM(outstanding_amount) 
    #     FROM `tabDoctor Log` 
    #     WHERE doctor=%s AND company=%s AND docstatus=1
    # """, (supplier, company))[0][0] or 0
    # -----------------------------------
    doc_total = 0
    return inv_total + con_total + doc_total