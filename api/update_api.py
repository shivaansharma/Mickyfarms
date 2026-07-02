import os
import subprocess
import frappe

@frappe.whitelist()
def update_app():
    if "System Manager" not in frappe.get_roles():
        frappe.throw("Not permitted")

    bench_path = frappe.utils.get_bench_path()

    script = os.path.join(
        bench_path,
        "apps",
        "assignment",
        "shell",
        "update_assignment.sh"
    )

    result = subprocess.run(
        [script, frappe.local.site],
        capture_output=True,
        text=True
    )

    return {
        "success": result.returncode == 0,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }