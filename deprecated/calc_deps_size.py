import os
import sys
import json
from importlib.metadata import version, requires, files
from pathlib import Path

def get_all_deps(pkg_name, visited=None):
    if visited is None:
        visited = set()
    
    if pkg_name in visited:
        return visited
    
    visited.add(pkg_name)
    
    try:
        reqs = requires(pkg_name)
        if reqs:
            for req in reqs:
                # Basic parsing of requirement string (e.g. "requests (>=2.28.0)")
                dep = req.split()[0].split(';')[0].split('[')[0].split('<')[0].split('>')[0].split('=')[0].strip().replace(',', '')
                if dep:
                    get_all_deps(dep, visited)
    except Exception:
        pass
    
    return visited

def get_package_size(pkg_name):
    try:
        total_size = 0
        pkg_files = files(pkg_name)
        if pkg_files:
            for f in pkg_files:
                # Path(f).locate() gives the absolute path
                full_path = f.locate()
                if full_path and os.path.exists(full_path):
                    total_size += os.path.getsize(full_path)
        return total_size
    except Exception as e:
        return 0

main_packages = ['python-dotenv', 'google-genai', 'requests']
all_packages = set()
for pkg in main_packages:
    get_all_deps(pkg, all_packages)

# Clean up package names (some might be case insensitive or vary)
# but importlib.metadata usually handles it if they exist.

report = []
total_all = 0

for pkg in sorted(all_packages):
    size = get_package_size(pkg)
    if size > 0:
        report.append({
            "name": pkg,
            "size_kb": round(size / 1024, 2),
            "size_mb": round(size / (1024 * 1024), 2)
        })
        total_all += size

print(json.dumps({
    "packages": report,
    "total_size_mb": round(total_all / (1024 * 1024), 2),
    "total_size_gb": round(total_all / (1024 * 1024 * 1024), 4)
}, indent=2))
