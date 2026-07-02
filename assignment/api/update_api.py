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
    site = frappe.local.site

    commands = [
        f"bench --site {site} backup",
        "git -C apps/assignment pull upstream main",
    ]

    output = ""

    for cmd in commands:
        result = run_command(cmd, bench)

        output += f"\n$ {cmd}\n"
        output += result["output"]

        if not result["success"]:
            return {
                "success": False,
                "output": output,
            }

    return {
        "success": True,
        "output": output
        + "\n\nCode updated successfully.\n"
        + "Please run:\n"
        + f"bench --site {site} migrate\n"
        + "bench build\n"
        + "bench restart",
    }

    #this is a test to see if my api works 