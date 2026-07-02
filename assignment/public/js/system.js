frappe.ui.form.on("System Settings", {
    refresh(frm) {
        frm.add_custom_button(__("Update Application"), () => {
            frappe.call({
                method: "assignment.api.update_api.update_app",
                freeze: true,
                freeze_message: __("Updating..."),
                callback(r) {
                    if (!r.exc) {
                        frappe.msgprint({
                            title: __("Result"),
                            indicator: r.message.success ? "green" : "red",
                            message: `<pre>${r.message.output}</pre>`
                        });
                    }
                }
            });
        });
    }
});