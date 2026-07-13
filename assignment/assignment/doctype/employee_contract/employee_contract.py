# Copyright (c) 2026, shivaan and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, nowdate

class EmployeeContract(Document):
    def on_submit(self):
        """Triggered automatically when the Employee Contract is submitted."""
        self.create_advance_payment()

    def create_advance_payment(self):
        """Creates and submits a Payment Entry automatically if an advance exists."""
        if flt(self.pay_advance) <= 0:
            return

        # Double-check prevention: avoid creating duplicate payments
        if frappe.db.exists("Payment Entry", {"reference_no": self.name, "docstatus": ["<", 2]}):
            return

        # Fetch the company's base currency
        company_currency = frappe.get_cached_value('Company', self.company, 'default_currency') or "INR"

        # Initialize the Payment Entry document structure
        payment_entry = frappe.get_doc({
            "doctype": "Payment Entry",
            "payment_type": "Pay",
            "party_type": "Supplier",
            "party": self.employee,
            "company": self.company,
            "posting_date": self.posting_date or nowdate(),
            
            # Balances
            "paid_amount": flt(self.pay_advance),
            "received_amount": flt(self.pay_advance),
            
            # Accounts Setup
            "paid_from": "Cash - MF",
            "paid_to": "Creditors - MF",
            "paid_from_account_currency": company_currency,
            "paid_to_account_currency": company_currency,
            
            # Reference metadata
            "reference_no": self.name,
            "reference_date": self.posting_date or nowdate(),
            "remarks": f"Automated Pay Advance for Employee Contract: {self.name}"
        })

        # Insert to DB and Submit the Payment Entry
        # NOTE: We removed the .append("references") block because 
        # custom Doctypes are not valid references for Payment Entry.
        payment_entry.insert(ignore_permissions=True)
        payment_entry.submit()

        frappe.msgprint(
            msg=f"Advance Payment Entry <b><a href='/app/payment-entry/{payment_entry.name}'>{payment_entry.name}</a></b> has been processed.",
            title="Payment Auto-Generated",
            indicator="green"
        )