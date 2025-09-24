#!/usr/bin/env python3
import os
import subprocess
from pathlib import Path

PIHOLE_DIR = Path("/etc/pihole")

def read_file(path):
    try:
        return path.read_text().strip().splitlines()
    except Exception:
        return []

def run_cmd(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, text=True).strip().splitlines()
    except subprocess.CalledProcessError:
        return []

def section(title, icon="📌"):
    print(f"\n## {icon} {title}\n")

def main():
    print("# 🕳️ Pi-hole Configuration Report\n")
    print("_A human-readable dump of your current Pi-hole settings_\n")

    # Core Settings
    section("Core Settings", "⚙️")
    setup_vars = read_file(PIHOLE_DIR / "setupVars.conf")
    if setup_vars:
        print("```ini")
        for line in setup_vars:
            if line.strip() and not line.startswith("#"):
                print(line)
        print("```")
    else:
        print("_No setupVars.conf found_\n")

    # Adlists
    section("Adlists", "📚")
    adlists = read_file(PIHOLE_DIR / "adlists.list")
    if adlists:
        for line in adlists:
            print(f"- 🌐 {line}")
    else:
        print("_No adlists configured_\n")

    # Whitelist / Blacklist
    section("Whitelist", "✅")
    whitelist = read_file(PIHOLE_DIR / "whitelist.txt")
    if whitelist:
        for line in whitelist:
            print(f"- 🟢 {line}")
    else:
        print("_No whitelisted domains_\n")

    section("Blacklist", "⛔")
    blacklist = read_file(PIHOLE_DIR / "blacklist.txt")
    if blacklist:
        for line in blacklist:
            print(f"- 🔴 {line}")
    else:
        print("_No blacklisted domains_\n")

    # Gravity DB
    section("Gravity Database", "🌌")
    gravity_count = run_cmd("sqlite3 /etc/pihole/gravity.db 'SELECT COUNT(*) FROM gravity;'")
    print(f"**Total domains blocked:** {gravity_count[0] if gravity_count else 'Not available'}\n")

    # DNS Servers
    section("Upstream DNS Servers", "🛰️")
    dns_servers = read_file(PIHOLE_DIR / "dns-servers.conf")
    if dns_servers:
        for line in dns_servers:
            print(f"- 📡 {line}")
    else:
        print("_No custom upstream DNS servers_\n")

    # DHCP
    section("DHCP Settings", "📶")
    dhcp = run_cmd("pihole-FTL dhcp-discover || true")
    if dhcp:
        print("```")
        print("\n".join(dhcp))
        print("```")
    else:
        print("_DHCP appears disabled or requires root privileges_\n")

    # Status
    section("Pi-hole Status", "🟢")
    status = run_cmd("pihole status")
    if status:
        print("```")
        print("\n".join(status))
        print("```")
    else:
        print("_Status not available_\n")

if __name__ == "__main__":
    main()