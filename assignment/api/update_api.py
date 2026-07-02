import subprocess
import frappe


@frappe.whitelist()
def update_app():

    bench = frappe.utils.get_bench_path()
    site = frappe.local.site

    commands = [
        f"cd {bench}",
        f"bench --site {site} backup",
        "git -C apps/assignment pull upstream main",
        f"bench --site {site} migrate",
        "bench build",
        "bench restart"
    ]

    command = " && ".join(commands)

    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True
    )

    return {
        "success": result.returncode == 0,
        "output": result.stdout + "\n" + result.stderr,
    }