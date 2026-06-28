# import frappe
# from frappe.model.mapper import get_mapped_doc

# def purchase_receipt(doc, method=None):
#     """
#     Automatically creates and submits a Purchase Receipt 
#     whenever a Purchase Order is submitted.
#     """
#     try:
#         # 1. Use Frappe's built-in mapper to port all items, taxes, and supplier data safely
#         pr_doc = get_mapped_doc("Purchase Order", doc.name, {
#             "Purchase Order": {
#                 "doctype": "Purchase Receipt",
#                 "field_map": {
#                     "name": "purchase_order"
#                 }
#             },
#             "Purchase Order Item": {
#                 "doctype": "Purchase Receipt Item",
#                 "field_map": {
#                     "name": "po_detail",
#                     "parent": "purchase_order"
#                 }
#             }
#         }, ignore_permissions=True)
        
#         # 2. Insert the receipt into the database
#         pr_doc.insert(ignore_permissions=True)
        
#         # 3. Automatically submit the Purchase Receipt to update inventory stock
#         pr_doc.submit()
        
#         # 4. Optional: Post a message back to the user's timeline log
#         frappe.msgprint(f"Automated Stock Update: Purchase Receipt <a href='/app/purchase-receipt/{pr_doc.name}'>{pr_doc.name}</a> created successfully.")
        
#     except Exception as e:
#         frappe.log_error(title="Auto Purchase Receipt Failure", message=frappe.get_traceback())
#         frappe.throw(f"Purchase Order submitted, but automated Purchase Receipt failed. Check Error Logs. Error: {str(e)}")