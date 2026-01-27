import urllib.request
import gzip
import io
import re
import json
import sys

# Configuration mapping for setup scripts.
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

# Ubuntu Mirror Configuration
UBUNTU_MIRROR = "http://archive.ubuntu.com/ubuntu"
DIST = "noble"
COMPONENTS = ["main", "restricted", "universe", "multiverse"]
ARCH = "amd64"

PACKAGES_DB = {}
PROVIDERS_DB = {}

def fetch_package_indices():
    """Downloads and parses Packages.gz for all components."""
    print("Fetching Ubuntu package indices (this may take a few seconds)...")
    
    for comp in COMPONENTS:
        url = f"{UBUNTU_MIRROR}/dists/{DIST}/{comp}/binary-{ARCH}/Packages.gz"
        print(f"  Downloading {url}...")
        try:
            with urllib.request.urlopen(url) as response:
                with gzip.GzipFile(fileobj=response) as f:
                    content = f.read().decode('utf-8', errors='ignore')
                    parse_packages_content(content)
        except Exception as e:
            print(f"  Error fetching {comp}: {e}")

def parse_packages_content(content):
    """Parses the content of a Packages file and updates the DB."""
    # Packages are separated by blank lines
    entries = content.split('\n\n')
    for entry in entries:
        if not entry.strip():
            continue
        
        pkg_data = {}
        current_key = None
        
        # Simple line-based parsing
        for line in entry.split('\n'):
            if line.startswith(' '):
                # Continuation line (not handling for Depends/Provides complex split for now, 
                # usually Depends is on one line or we accept truncation if it wraps weirdly 
                # but standard Packages format usually keeps field on one line or handled simply)
                if current_key == 'Depends':
                    pkg_data['Depends'] += line.strip()
                continue
            
            if ':' in line:
                key, val = line.split(':', 1)
                current_key = key
                pkg_data[key] = val.strip()
        
        if 'Package' in pkg_data:
            name = pkg_data['Package']
            size = int(pkg_data.get('Installed-Size', 0)) * 1024 # KB to Bytes
            
            depends = []
            if 'Depends' in pkg_data:
                # Remove version constraints like (>= 1.0)
                # Split by comma
                raw_deps = pkg_data['Depends']
                # Clean up versions
                depends = [d.strip() for d in raw_deps.split(',')]

            pre_depends = []
            if 'Pre-Depends' in pkg_data:
                raw_pre = pkg_data['Pre-Depends']
                pre_depends = [d.strip() for d in raw_pre.split(',')]

            all_deps = depends + pre_depends
            
            PACKAGES_DB[name] = {
                'size': size,
                'depends': all_deps
            }
            
            if 'Provides' in pkg_data:
                provides = [p.strip().split()[0] for p in pkg_data['Provides'].split(',')]
                for p in provides:
                    if p not in PROVIDERS_DB:
                        PROVIDERS_DB[p] = []
                    PROVIDERS_DB[p].append(name)

def resolve_dependencies(root_packages):
    """Recursively resolves dependencies and returns a set of package names."""
    installed = set()
    queue = list(root_packages)
    
    # Basic system packages that are usually present and might cause circles or noise
    # We'll just resolve everything provided.
    
    while queue:
        pkg_name = queue.pop(0)
        
        # Clean name (just in case)
        pkg_name = pkg_name.strip()
        if not pkg_name: 
            continue

        if pkg_name in installed:
            continue
            
        # Resolve virtual
        real_pkg = pkg_name
        if pkg_name not in PACKAGES_DB:
            if pkg_name in PROVIDERS_DB:
                # Pick the first provider
                # Heuristic: Prefer a provider that is already installed?
                found = False
                for p in PROVIDERS_DB[pkg_name]:
                    if p in installed:
                        real_pkg = p
                        found = True
                        break
                if not found:
                    # Pick first available in DB
                    for p in PROVIDERS_DB[pkg_name]:
                        if p in PACKAGES_DB:
                            real_pkg = p
                            found = True
                            break
                if not found:
                    # print(f"Warning: No provider found for {pkg_name}")
                    continue
            else:
                # print(f"Warning: Package {pkg_name} not found in DB.")
                continue
        
        if real_pkg in installed:
            continue
            
        installed.add(real_pkg)
        
        # Add dependencies
        if real_pkg in PACKAGES_DB:
            for dep_str in PACKAGES_DB[real_pkg]['depends']:
                # Handle OR: "debconf | debconf-2.0"
                options = dep_str.split('|')
                chosen = None
                
                for opt in options:
                    opt = opt.strip()
                    # Strip version: "libc6 (>= 2.34)" -> "libc6"
                    opt_name = re.split(r'[\s(]', opt)[0]
                    
                    if opt_name in PACKAGES_DB or opt_name in PROVIDERS_DB:
                        chosen = opt_name
                        break
                
                # If no option found, just pick the first one's name to try (might be virtual)
                if not chosen:
                    chosen = re.split(r'[\s(]', options[0].strip())[0]
                
                queue.append(chosen)

    return installed

def get_quarto_size(version_type):
    """Fetches Quarto installer size from GitHub."""
    print(f"Fetching Quarto {version_type} info...")
    try:
        if version_type == "latest":
            url = "https://api.github.com/repos/quarto-dev/quarto-cli/releases/latest"
        else:
            url = "https://api.github.com/repos/quarto-dev/quarto-cli/releases"
            
        with urllib.request.urlopen(url) as response:
            data = json.load(response)
            
        if version_type == "prerelease":
            # Data is a list, find first prerelease
            if isinstance(data, list):
                for release in data:
                    if release.get('prerelease'):
                        data = release
                        break
                else:
                    # Fallback if no prerelease found
                    data = data[0]

        # Find asset
        for asset in data.get('assets', []):
            name = asset.get('name', '')
            if name.endswith('.deb') and 'linux-amd64' in name:
                size = asset.get('size', 0)
                # Estimate installed size (deb is compressed ar/tar.xz). 
                # 3.5x is a reasonable heuristic for binaries.
                # Previous hardcoded value: 381MB. Deb size is usually ~100MB.
                return size * 3.5 
                
    except Exception as e:
        print(f"Warning: Could not fetch Quarto size: {e}")
        
    # Fallback to hardcoded
    if version_type == "latest":
        return 381 * 1024 * 1024
    return 388 * 1024 * 1024

def main():
    fetch_package_indices()
    
    # Cache Quarto sizes
    quarto_sizes = {}
    quarto_sizes["latest"] = get_quarto_size("latest")
    quarto_sizes["prerelease"] = get_quarto_size("prerelease")
    
    print("\nCalculating sizes...")
    results = {}
    
    for script, config in SCRIPTS.items():
        apt_packages = config["apt"]
        
        if apt_packages:
            resolved = resolve_dependencies(apt_packages)
            apt_size = sum(PACKAGES_DB[p]['size'] for p in resolved if p in PACKAGES_DB)
        else:
            apt_size = 0
            
        q_size = 0
        if config["quarto"]:
            q_size = quarto_sizes[config["quarto"]]
            
        total = apt_size + q_size
        results[script] = total
        print(f"{script}: {total / (1024*1024):.2f} MB")

    print("\n\n### Markdown Table ###\n")
    print("| Setup Script | R | Quarto | Tex | Estimated Installation Size |")
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

if __name__ == "__main__":
    main()
