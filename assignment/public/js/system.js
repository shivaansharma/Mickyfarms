frappe.ui.form.on("System Settings", {
    refresh(frm) {
        frm.add_custom_button(__("Update Application"), () => {
            frappe.confirm(
                __("This will update the application. Continue?"),
                () => {
                    frappe.call({
                        method: "assignment.api.update_api.update_app",
                        freeze: true,
                        freeze_message: __("Updating application..."),

                        callback(r) {
                            if (!r.exc && r.message) {
                                if (r.message.success) {
                                    frappe.msgprint({
                                        title: __("Success"),
                                        indicator: "green",
                                        message: `<pre>${frappe.utils.escape_html(r.message.stdout || "Update completed.")}</pre>`
                                    });
                                } else {
                                    frappe.msgprint({
                                        title: __("Update Failed"),
                                        indicator: "red",
                                        message: `<pre>${frappe.utils.escape_html(r.message.stderr || "Unknown error.")}</pre>`
                                    });
                                }
                            }
                        },

                        error(err) {
                            frappe.msgprint({
                                title: __("Server Error"),
                                indicator: "red",
                                message: __("Could not execute the update script.")
                            });
                            console.error(err);
                        }
                    });
                }
            );
        });
    }
});