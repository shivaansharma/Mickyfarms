frappe.ui.form.on('Employee', {
    refresh: function(frm) {
        if (!frm.is_new()) {
            
            // FETCH AND DISPLAY LIVE DUES (Reads your liability balance)
            frappe.call({
                method: 'assignment.assignment.doctype.weekly_wage_payment.weekly_wage_payment.get_employee_wages_owed',
                args: {
                    employee: frm.doc.name,
                    company: frm.doc.company || "Micky Farms"
                },
                callback: function(r) {
                    if (r.message !== undefined) {
                        frm.set_intro(""); 
                        let amount = format_currency(r.message, frm.doc.currency || 'INR');
                        if (r.message > 0) {
                            frm.set_intro(__('<b>Company owes this employee:</b> {0}', [amount]), 'orange');
                        } else {
                            frm.set_intro(__('<b>All clear:</b> No outstanding wages owed to this employee.', [amount]), 'green');
                        }
                    }
                }
            });
            
            // BUTTON 1: Record Standalone Liability (Creates the "We Owe You" balance)
            frm.add_custom_button(__('Record Owed Amount'), function() {
                frappe.model.with_doctype('Journal Entry', function() {
                    let je = frappe.model.get_new_doc('Journal Entry');
                    je.voucher_type = 'Journal Entry';
                    je.company = frm.doc.company || "Micky Farms";
                    je.remark = `Manual wage/incentive liability accrued for ${frm.doc.employee_name}`;
                    
                    // Row 1: Debit the Expense (Increases what you're tracking as spent)
                    let row_expense = frappe.model.add_child(je, 'Journal Entry Account', 'accounts');
                    row_expense.account = 'Salary - MF'; // ⚠️ Change to your exact Salary Expense account
                    row_expense.debit_in_account_currency = 0; 
                    
                    // Row 2: Credit the Liability (Increases what you owe the employee)
                    let row_liability = frappe.model.add_child(je, 'Journal Entry Account', 'accounts');
                    row_liability.account = 'Salary Payable - MF'; // ⚠️ Change to your exact Liability account
                    row_liability.party_type = 'Employee';
                    row_liability.party = frm.doc.name;
                    row_liability.credit_in_account_currency = 0; 
                    
                    frappe.set_route('Form', 'Journal Entry', je.name);
                });
            }, __('Actions'));

            // BUTTON 2: Issue Advance Money (Asset)
            frm.add_custom_button(__('Pay Advance'), function() {
                frappe.model.with_doctype('Payment Entry', function() {
                    let pe = frappe.model.get_new_doc('Payment Entry');
                    pe.payment_type = 'Pay';
                    pe.party_type = 'Employee';
                    pe.party = frm.doc.name;
                    pe.party_name = frm.doc.employee_name;
                    pe.paid_to = 'Employee Advances - MF'; 
                    pe.remarks = `Upfront seasonal wage advance paid to ${frm.doc.employee_name}`;
                    
                    frappe.set_route('Form', 'Payment Entry', pe.name);
                });
            }, __('Actions'));

            // BUTTON 3: Clear Advance Lump-Sum (Asset Reduction)
            frm.add_custom_button(__('Recover Advance'), function() {
                frappe.model.with_doctype('Payment Entry', function() {
                    let pe = frappe.model.get_new_doc('Payment Entry');
                    pe.payment_type = 'Receive'; 
                    pe.party_type = 'Employee';
                    pe.party = frm.doc.name;
                    pe.party_name = frm.doc.employee_name;
                    pe.paid_from = 'Employee Advances - MF'; 
                    pe.remarks = `Lump-sum advance payback collected from ${frm.doc.employee_name}`;
                    
                    frappe.set_route('Form', 'Payment Entry', pe.name);
                });
            }, __('Actions'));

            // BUTTON 4: Pay Outstanding Dues / Clear Liability
            frm.add_custom_button(__('Pay Outstanding Dues'), function() {
                frappe.model.with_doctype('Payment Entry', function() {
                    let pe = frappe.model.get_new_doc('Payment Entry');
                    pe.payment_type = 'Pay';
                    pe.party_type = 'Employee';
                    pe.party = frm.doc.name;
                    pe.party_name = frm.doc.employee_name;
                    pe.paid_to = 'Salary Payable - MF'; 
                    pe.remarks = `Disbursed accumulated outstanding wage liability to ${frm.doc.employee_name}`;
                    
                    frappe.set_route('Form', 'Payment Entry', pe.name);
                });
            }, __('Actions'));
           
            
        }
    }
});