frappe.ui.form.on("Employee Attendance Tool", {
    refresh: function(frm) {
        show_last_attendance_banner(frm);
    },
    company: function(frm) {
        show_last_attendance_banner(frm);
    }
});

function show_last_attendance_banner(frm) {
    // Clear any active banner immediately to prevent visual duplicate stacks
    frm.dashboard.clear_headline();

    if (!frm.doc.company) {
        return;
    }

    // Only filter by company — we want the latest attendance_date overall,
    // not restricted to whatever date happens to be selected on the form.
    frappe.db.get_list("Attendance", {
        filters: { company: frm.doc.company },
        fields: ["creation", "owner", "attendance_date"],
        order_by: "attendance_date desc", // latest work date marked, not entry time
        limit: 1
    }).then(records => {
        if (records && records.length > 0) {
            const last_log = records[0];

            const datetime_parts = last_log.creation.split(" ");
            const log_date = frappe.datetime.str_to_user(datetime_parts[0]);
            const log_time = datetime_parts[1].substring(0, 5);
            const latest_marked_date = frappe.datetime.str_to_user(last_log.attendance_date);

            const banner_html = `
                <div style="
                    display: flex; 
                    align-items: center; 
                    gap: 8px; 
                    font-size: 13px; 
                    color: var(--text-color);
                ">
                    <span>📢</span>
                    <div>
                        <b>Latest Attendance Marked For:</b> 
                        <span class="text-primary" style="font-weight: 600;">${latest_marked_date}</span>
                        (entered on ${log_date} at ${log_time} by <b>${last_log.owner}</b>).
                    </div>
                </div>
            `;

            frm.dashboard.set_headline(banner_html, "blue");
        } else {
            frm.dashboard.set_headline(
                `<div style="font-size:13px;">No attendance records found for this company.</div>`,
                "orange"
            );
        }
    });
}