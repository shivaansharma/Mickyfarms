# Copyright (c) 2026, shivaan and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class Animal(Document):
    def validate(self):
        if self.gender == "Male" and self.lactation_status in ["Milking", "Dry"]:
            frappe.throw(
                _("A male animal cannot have a lactation status of '{0}'.").format(self.lactation_status)
            )