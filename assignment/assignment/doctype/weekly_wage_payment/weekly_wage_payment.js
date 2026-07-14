// ─── Helpers ──────────────────────────────────────────────────────────────────

function calculate_row_totals(frm, cdt, cdn) {
    let row = locals[cdt][cdn];

    // Always read from the saved snapshot fields (set by fetch_employees_and_metrics)
    // _base_* are local JS mirrors so we don't re-read on every keystroke
    if (row._base_advance === undefined)     row._base_advance     = flt(row.advance_snapshot || 0);
    if (row._base_what_we_owe === undefined) row._base_what_we_owe = flt(row.outstanding_snapshot || 0);

    let base_advance     = flt(row._base_advance);
    let base_what_we_owe = flt(row._base_what_we_owe);

    let current_cycle_earnings = flt(row.days_worked) * flt(row.daily_wage_rate);

    // Total wages now owed = prior unpaid wages + this cycle's earnings
    let total_wages_owed = base_what_we_owe + current_cycle_earnings;

    // ── Auto-offset advance against total wages owed ──────────────────────────
    // If employee already has an advance balance, it nets against wages earned.
    // e.g. advance=5000, wages_earned=3000 → deduct 3000, advance_remaining=2000
    let advance_deduction = 0;
    if (base_advance > 0 && total_wages_owed > 0) {
        advance_deduction = Math.min(base_advance, total_wages_owed);
    }

    let net_wages_after_offset  = total_wages_owed - advance_deduction;
    let remaining_advance       = base_advance - advance_deduction;

    // ── Apply cash payout if any ──────────────────────────────────────────────
    let final_net_payout     = flt(row.final_net_payout);
    let final_advance_balance = remaining_advance;
    let final_what_we_owe     = net_wages_after_offset;

    if (final_net_payout > 0) {
        let overpayment = final_net_payout - net_wages_after_offset;

        if (overpayment > 0.01) {
            // Paid more than wages owed — excess becomes a new advance debt
            final_advance_balance = remaining_advance + overpayment;
            final_what_we_owe     = 0;
        } else {
            // Partial or exact payment — reduce wages owed, advance unchanged
            final_what_we_owe     = net_wages_after_offset - final_net_payout;
            final_advance_balance = remaining_advance;
        }
    }

    frappe.model.set_value(cdt, cdn, {
        'payment':            current_cycle_earnings,
        'gross_wage':         total_wages_owed,
        'advance_deduction':  advance_deduction,
        'total_advance_owed': final_advance_balance,
        'what_we_owe':        final_what_we_owe
    });

    _show_payout_indicator(
        frm, cdt, cdn,
        net_wages_after_offset, final_advance_balance, final_what_we_owe, final_net_payout
    );
    update_total_payout(frm);
}

function _show_payout_indicator(frm, cdt, cdn, net_wages_after_offset, final_advance_balance, final_what_we_owe, final_net_payout) {
    let row = locals[cdt][cdn];
    if (final_net_payout <= 0) return;

    let difference = final_net_payout - net_wages_after_offset;
    if (Math.abs(difference) < 0.01) return;

    let emp_label = row.employee_name || row.employee;

    if (difference > 0) {
        frappe.show_alert({
            message: __('{0}: Excess cash ₹{1} added to advance debt.', [emp_label, format_currency(difference)]),
            indicator: 'orange'
        }, 5);
    } else {
        frappe.show_alert({
            message: __('{0}: Partial payment. Remaining Owed: {1} | Advance Balance: {2}', [
                emp_label,
                format_currency(final_what_we_owe),
                format_currency(final_advance_balance)
            ]),
            indicator: 'blue'
        }, 5);
    }
}

function format_currency(value) {
    return frappe.format(value, { fieldtype: 'Currency' });
}

function update_total_payout(frm) {
    let total = 0;
    (frm.doc.wage_details || []).forEach(row => {
        total += flt(row.final_net_payout);
    });
    frm.set_value('total_payout_amount', total);
}

function refresh_existing_rows(frm) {
    let rows = frm.doc.wage_details || [];
    if (!rows.length) return;

    let pending = rows.length;

    rows.forEach(function(row) {
        frappe.call({
            method: 'assignment.assignment.doctype.weekly_wage_payment.weekly_wage_payment.fetch_employees_and_metrics',
            args: {
                to_date:  frm.doc.to_date,
                company:  frm.doc.company || "Micky Farms",
                employee: row.employee
            },
            callback: function(r) {
                if (r.message && r.message.length > 0) {
                    let data = r.message[0];

                    // Reset JS mirrors so calculate_row_totals picks up fresh values
                    row._base_advance     = flt(data.advance_snapshot);
                    row._base_what_we_owe = flt(data.outstanding_snapshot);

                    frappe.model.set_value(row.doctype, row.name, {
                        'advance_snapshot':      data.advance_snapshot,
                        'outstanding_snapshot':  data.outstanding_snapshot,
                        'daily_wage_rate':       data.daily_wage_rate,
                        'days_worked':           data.days_worked,
                        'final_net_payout':      0
                    });

                    calculate_row_totals(frm, row.doctype, row.name);
                }
                pending--;
                if (pending === 0) {
                    frm.refresh_field("wage_details");
                    update_total_payout(frm);
                    frappe.show_alert({ message: __('Metrics refreshed.'), indicator: 'green' });
                }
            }
        });
    });
}

function fetch_and_populate(frm) {
    if (!frm.doc.to_date) {
        frappe.msgprint(__('Please select the Payment Date first.'));
        return;
    }

    frappe.call({
        method: 'assignment.assignment.doctype.weekly_wage_payment.weekly_wage_payment.fetch_employees_and_metrics',
        args: {
            to_date: frm.doc.to_date,
            company: frm.doc.company || "Micky Farms"
        },
        freeze: true,
        freeze_message: __('Compiling employee metrics...'),
        callback: function(r) {
            if (r.message) {
                frm.clear_table("wage_details");

                r.message.forEach(data => {
                    let row = frm.add_child("wage_details");

                    row.employee             = data.employee;
                    row.employee_name        = data.employee_name;
                    row.daily_wage_rate      = data.daily_wage_rate;
                    row.days_worked          = data.days_worked;
                    row.advance_snapshot     = data.advance_snapshot;
                    row.outstanding_snapshot = data.outstanding_snapshot;
                    // row.final_net_payout     = 0;

                    // Seed JS mirrors
                    row._base_advance     = flt(data.advance_snapshot);
                    row._base_what_we_owe = flt(data.outstanding_snapshot);

                    calculate_row_totals(frm, row.doctype, row.name);
                });

                frm.refresh_field("wage_details");
                update_total_payout(frm);
                frappe.show_alert({ message: __('Employee metrics compiled successfully!'), indicator: 'green' });
            }
        }
    });
}

// ─── Parent form ──────────────────────────────────────────────────────────────

frappe.ui.form.on('Weekly Wage Payment', {
    refresh: function(frm) {
        if (frm.doc.docstatus === 0) {
            frm.remove_custom_button(__('Get Employees'));
            frm.add_custom_button(__('Get Employees'), function() {
                fetch_and_populate(frm);
            });
        }

        frappe.dom.set_style(`
            [data-fieldname="wage_details"] .grid-static-col[data-fieldname="final_net_payout"] {
                background-color: #e6f4ea !important;
                color: #137333 !important;
                font-weight: bold !important;
            }
            [data-fieldname="wage_details"] .grid-static-col[data-fieldname="total_advance_owed"] {
                background-color: #fef7e0 !important;
                color: #b06000 !important;
            }
            [data-fieldname="wage_details"] .grid-static-col[data-fieldname="what_we_owe"] {
                background-color: #fce8e6 !important;
                color: #c5221f !important;
            }
        `);
    },

    to_date: function(frm) {
        if (frm.doc.docstatus !== 0 || !frm.doc.to_date) return;
        if (!frm.doc.wage_details || frm.doc.wage_details.length === 0) return;

        frappe.confirm(
            __('Payment date changed. Refresh metrics for existing rows?'),
            function() { refresh_existing_rows(frm); }
        );
    }
});

// ─── Child table ──────────────────────────────────────────────────────────────

frappe.ui.form.on('Weekly Wage Line Item', {
    employee: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (!frm.doc.to_date) {
            frappe.msgprint(__('Please select the Payment Date first.'));
            frappe.model.set_value(cdt, cdn, 'employee', '');
            return;
        }
        if (!row.employee) return;

        frappe.call({
            method: 'assignment.assignment.doctype.weekly_wage_payment.weekly_wage_payment.fetch_employees_and_metrics',
            args: {
                to_date:  frm.doc.to_date,
                company:  frm.doc.company || "Micky Farms",
                employee: row.employee
            },
            freeze: true,
            freeze_message: __('Fetching metrics for employee...'),
            callback: function(r) {
                if (r.message && r.message.length > 0) {
                    let data = r.message[0];

                    row._base_advance     = flt(data.advance_snapshot);
                    row._base_what_we_owe = flt(data.outstanding_snapshot);

                    frappe.model.set_value(cdt, cdn, {
                        'employee_name':         data.employee_name,
                        'daily_wage_rate':        data.daily_wage_rate,
                        'days_worked':            data.days_worked,
                        'advance_snapshot':       data.advance_snapshot,
                        'outstanding_snapshot':   data.outstanding_snapshot,
                        'final_net_payout':       0
                    });

                    calculate_row_totals(frm, cdt, cdn);
                }
            }
        });
    },

    daily_wage_rate:     (frm, cdt, cdn) => calculate_row_totals(frm, cdt, cdn),
    days_worked:         (frm, cdt, cdn) => calculate_row_totals(frm, cdt, cdn),
    final_net_payout:    (frm, cdt, cdn) => calculate_row_totals(frm, cdt, cdn),
    wage_details_remove: (frm) => update_total_payout(frm)
});