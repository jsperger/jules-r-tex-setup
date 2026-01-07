import subprocess
import os
import re
import json

SCRIPTS = {
    "setup_quarto_latest.sh": {
        "apt": [],
        "quarto": "latest",
        "r": False
    },
    "setup_quarto_prerelease.sh": {
        "apt": [],
        "quarto": "prerelease",
        "r": False
    },
    "setup_r_only.sh": {
        "apt": ["r-base-core", "python3-dbus", "python3-gi", "python3-apt", "make"],
        "quarto": None,
        "r": True
    },
    "setup_r_quarto_tex.sh": {
        "apt": ["pandoc", "texlive-latex-extra", "texlive-luatex", "texlive-science",
                "r-base-core", "python3-dbus", "python3-gi", "python3-apt", "make"],
        "quarto": "prerelease",
        "r": True
    },
    "setup_r_tex_full.sh": {
        "apt": ["pandoc", "texlive-full",
                "r-base-core", "python3-dbus", "python3-gi", "python3-apt", "make"],
        "quarto": "prerelease",
        "r": True
    }
}

def exec_cmd(container_id, command):
    full_cmd = ["sudo", "docker", "exec", container_id, "bash", "-c", command]
    result = subprocess.run(full_cmd, capture_output=True, text=True)
    return result.stdout

def get_quarto_size(container_id, version_type):
    # Hardcoded sizes based on check of 1.8.26 and 1.9.16
    if version_type == "latest":
        return 381 * 1024 * 1024
    elif version_type == "prerelease":
        return 388 * 1024 * 1024
    return 0

def get_apt_size(container_id, packages):
    if not packages:
        return 0

    # Try parsing apt-get install -s output
    # Ubuntu 24.04 apt output for size: "After this operation, ... disk space will be used"
    cmd = f"apt-get install -s -y --no-install-recommends {' '.join(packages)}"
    res = exec_cmd(container_id, cmd)

    match = re.search(r"After this operation, ([\d\.]+) ([kMG]B) of additional disk space will be used", res)
    if match:
        val = float(match.group(1))
        unit = match.group(2)
        if unit == "kB":
            return val * 1024
        elif unit == "MB":
            return val * 1024 * 1024
        elif unit == "GB":
            return val * 1024 * 1024 * 1024

    # Fallback method: Calculate sum of Installed-Size for all packages to be installed
    bash_script = f"""
    apt-get install -s -y --no-install-recommends {' '.join(packages)} | \\
    grep '^Inst' | awk '{{print $2}}' | xargs apt-cache show | \\
    grep '^Installed-Size:' | awk '{{s+=$2}} END {{print s}}'
    """
    try:
        out = exec_cmd(container_id, bash_script)
        if out.strip():
            kb = int(out.strip())
            return kb * 1024
    except:
        pass

    return 0

def main():
    print("Starting container...")
    container_id = subprocess.check_output("sudo docker run -d -it --rm ubuntu:24.04 bash", shell=True, text=True).strip()

    try:
        print("Updating apt...")
        exec_cmd(container_id, "apt-get update")

        results = {}

        # Pre-calculated Quarto sizes
        quarto_sizes = {}
        quarto_sizes["latest"] = get_quarto_size(None, "latest")
        quarto_sizes["prerelease"] = get_quarto_size(None, "prerelease")

        for script, config in SCRIPTS.items():
            print(f"--- {script} ---")

            apt_packages = config["apt"]
            apt_size = get_apt_size(container_id, apt_packages)

            q_size = 0
            if config["quarto"]:
                q_size = quarto_sizes[config["quarto"]]

            total = apt_size + q_size
            results[script] = total
            print(f"Total: {total / (1024*1024):.2f} MB")

        print("\n\n### Markdown Table ###\n")
        print("| Setup Script | R | Quarto | Tex | Total Installation Size |")
        print("|---|---|---|---|---|")

        for script, config in SCRIPTS.items():
            r_str = "Yes" if config["r"] else "No"

            q_ver = config["quarto"]
            if q_ver:
                q_str = "Latest Stable" if q_ver == "latest" else "Prerelease"
            else:
                q_str = "No"

            # Tex column
            if "texlive-full" in config["apt"]:
                tex_str = "Full (texlive-full)"
            elif "texlive-latex-extra" in config["apt"]:
                tex_str = "Standard (latex-extra, luatex, science)"
            else:
                tex_str = "No"

            size_bytes = results[script]
            if size_bytes > 1024 * 1024 * 1024:
                size_str = f"{size_bytes / (1024*1024*1024):.1f} GB"
            else:
                size_str = f"{size_bytes / (1024*1024):.0f} MB"

            print(f"| `{script}` | {r_str} | {q_str} | {tex_str} | {size_str} |")

    finally:
        print("Stopping container...")
        subprocess.run(f"sudo docker stop {container_id}", shell=True)

if __name__ == "__main__":
    main()
