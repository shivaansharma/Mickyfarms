import subprocess
import frappe
from frappe import _


def run_command(cmd, cwd):
    result = subprocess.run(
        cmd,
        cwd=cwd,
        shell=True,
        capture_output=True,
        text=True,
    )

    return {
        "success": result.returncode == 0,
        "output": result.stdout + result.stderr,
    }


@frappe.whitelist()
def update_app():

    if "System Manager" not in frappe.get_roles():
        frappe.throw(_("Not permitted"))

    bench = frappe.utils.get_bench_path()

    result = run_command(
        "git -C apps/assignment pull upstream main",
        bench,
    )

    return {
        "success": result["success"],
        "output": result["output"],
    }