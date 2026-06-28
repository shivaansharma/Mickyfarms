frappe.query_reports["Weekly Wage"] = {

    filters: [
        {
            fieldname: "employee",
            label: __("Employee"),
            fieldtype: "Link",
            options: "Employee"
        },
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date"
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date"
        }
    ],

    onload: function(report) {
        // ── "Process Unrecorded Attendance" toolbar button ─────────────────
        report.page.add_inner_button(__("Process Unrecorded Attendance"), function() {
            let employee = report.get_filter_value("employee") || null;
            let scope_label = employee
                ? __("this employee")
                : __("ALL active employees");

            frappe.confirm(
                __("This will scan unprocessed attendance for {0}, book wages as a GL entry, and auto-offset any existing advance balance. Continue?", [scope_label]),
                function() {
                    frappe.dom.freeze(__("Processing attendance records..."));

                    frappe.call({
                        method: "assignment.assignment.report.weekly_wage.weekly_wage.process_unrecorded_attendance",
                        args: { employee: employee },
                        callback: function(r) {
                            frappe.dom.unfreeze();

                            if (!r.message) {
                                frappe.msgprint(__("No response from server."));
                                return;
                            }

                            let { processed, skipped } = r.message;

                            // Build a readable summary dialog
                            let html = "";

                            if (processed.length > 0) {
                                html += `<h5 style="color:#137333">✓ Processed (${processed.length})</h5>`;
                                html += `<table class="table table-bordered table-sm">
                                    <thead><tr>
                                        <th>Employee</th>
                                        <th>Days</th>
                                        <th>Wages Booked</th>
                                        <th>Advance Offset</th>
                                        <th>Net Owed</th>
                                        <th>JE</th>
                                    </tr></thead><tbody>`;

                                processed.forEach(p => {
                                    html += `<tr>
                                        <td>${p.employee_name} (${p.employee})</td>
                                        <td>${p.days}</td>
                                        <td>${format_currency(p.wages_booked)}</td>
                                        <td>${format_currency(p.advance_offset)}</td>
                                        <td>${format_currency(p.net_owed)}</td>
                                        <td><a href="/app/journal-entry/${p.je}" target="_blank">${p.je}</a></td>
                                    </tr>`;
                                });

                                html += `</tbody></table>`;
                            }

                            if (skipped.length > 0) {
                                html += `<h5 style="color:#b06000;margin-top:12px">⚠ Skipped (${skipped.length})</h5>`;
                                html += `<ul>` + skipped.map(s => `<li>${s}</li>`).join("") + `</ul>`;
                            }

                            if (!processed.length && !skipped.length) {
                                html = "<p>Nothing to process.</p>";
                            }

                            frappe.msgprint({
                                title: __("Attendance Processing Complete"),
                                message: html,
                                wide: true
                            });

                            // Refresh report so balances update immediately
                            report.refresh();
                        },
                        error: function() {
                            frappe.dom.unfreeze();
                            frappe.msgprint({
                                title: __("Error"),
                                message: __("Something went wrong. Check the error log."),
                                indicator: "red"
                            });
                        }
                    });
                }
            );
        }).addClass("btn-primary");
    }
};

function format_currency(value) {
    return frappe.format(flt(value), { fieldtype: "Currency" });
}