#!/usr/bin/env python3
"""
Host LAN IPv4 Detection & Sync Utility for GDP Assistant
Detects the host machine's active physical LAN/Wi-Fi/Hotspot IPv4 address and publishes
it to a mounted volume path so Docker containers can generate accurate mobile QR URLs.
"""

import os
import sys
import json
import time
import socket
import logging
import argparse
import subprocess
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("host_ip_sync")

ROOT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_PATHS = [
    ROOT_DIR / "models" / "paraphrase-multilingual-MiniLM-L12-v2" / "host_network.json",
    ROOT_DIR / "backend" / "temp_cache" / "host_network.json",
]


def is_valid_lan_ipv4(ip: str) -> bool:
    """Validate that an IPv4 address is an actual reachable LAN host IP, not virtual or internal."""
    if not ip or not isinstance(ip, str):
        return False
    parts = ip.strip().split(".")
    if len(parts) != 4:
        return False
    try:
        nums = [int(p) for p in parts]
        if any(n < 0 or n > 255 for n in nums):
            return False
    except ValueError:
        return False

    # Filter out loopback (127.0.0.0/8)
    if nums[0] == 127 or ip == "0.0.0.0":
        return False

    # Filter out APIPA / Link-local (169.254.0.0/16)
    if nums[0] == 169 and nums[1] == 254:
        return False

    # Filter out Docker bridge subnets and WSL virtual interfaces (172.16.0.0/12)
    # 172.16.0.0 - 172.31.255.255
    if nums[0] == 172 and 16 <= nums[1] <= 31:
        return False

    # Filter out Docker Desktop internal NAT gateway subnet (192.168.65.0/24)
    if nums[0] == 192 and nums[1] == 168 and nums[2] == 65:
        return False

    return True


def detect_windows_active_adapters():
    """Detect active network interfaces on Windows using PowerShell."""
    results = []
    primary_ip = None

    # Method 1: Query default route for the interface connecting to default gateway
    try:
        ps_cmd = (
            "Get-NetRoute -DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue | "
            "Sort-Object RouteMetric | "
            "Select-Object -ExpandProperty InterfaceAlias"
        )
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=4
        ).strip()
        default_ifaces = [line.strip() for line in out.splitlines() if line.strip()]
    except Exception as e:
        logger.debug(f"Default route query notice: {e}")
        default_ifaces = []

    # Method 2: Query all IPv4 addresses
    try:
        ps_cmd = (
            "Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | "
            "Select-Object InterfaceAlias, IPAddress, InterfaceMetric | "
            "ConvertTo-Json"
        )
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=4
        ).strip()
        if out:
            data = json.loads(out)
            if isinstance(data, dict):
                data = [data]
            for item in data:
                alias = item.get("InterfaceAlias", "")
                ip = item.get("IPAddress", "")
                # Skip virtual, WSL, loopback
                if any(v in alias.lower() for v in ["vethernet", "loopback", "wsl", "virtual", "docker"]):
                    continue
                if is_valid_lan_ipv4(ip):
                    is_def = alias in default_ifaces
                    is_wifi = "wifi" in alias.lower() or "wireless" in alias.lower() or "wlan" in alias.lower()
                    is_eth = "ethernet" in alias.lower() or "local area" in alias.lower()
                    results.append({
                        "name": f"{alias} ({ip})",
                        "interface": alias,
                        "ip": ip,
                        "url": f"http://{ip}:8080",
                        "is_default": is_def,
                        "is_wifi": is_wifi,
                        "is_ethernet": is_eth,
                    })
    except Exception as e:
        logger.debug(f"NetIPAddress query notice: {e}")

    # Sort results: default route first, then Wi-Fi / Hotspot, then Ethernet
    results.sort(key=lambda x: (not x.get("is_default", False), not x.get("is_wifi", False), not x.get("is_ethernet", False)))

    if results:
        primary_ip = results[0]["ip"]

    # Method 3: Fallback using outbound socket probe
    if not primary_ip:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            sock_ip = s.getsockname()[0]
            s.close()
            if is_valid_lan_ipv4(sock_ip):
                primary_ip = sock_ip
                if not any(r["ip"] == sock_ip for r in results):
                    results.insert(0, {
                        "name": f"Active LAN ({sock_ip})",
                        "interface": "Active LAN",
                        "ip": sock_ip,
                        "url": f"http://{sock_ip}:8080",
                        "is_default": True
                    })
        except Exception:
            pass

    return primary_ip, results


def sync_once(port: int = 8080) -> bool:
    """Detects current LAN IP and writes host_network.json."""
    primary_ip, ifaces = detect_windows_active_adapters()
    if not primary_ip:
        logger.warning("No active physical LAN IPv4 interface detected.")
        return False

    payload = {
        "primaryIp": primary_ip,
        "primaryUrl": f"http://{primary_ip}:{port}",
        "port": port,
        "updatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "availableHosts": ifaces
    }

    content = json.dumps(payload, indent=2)
    updated = False
    for path in OUTPUT_PATHS:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            # Only write if changed to avoid unnecessary disk I/O
            if path.exists() and path.read_text(encoding="utf-8").strip() == content.strip():
                continue
            path.write_text(content, encoding="utf-8")
            updated = True
            logger.info(f"✓ Synchronized Host LAN IP -> {path} ({primary_ip}:{port})")
        except Exception as e:
            logger.warning(f"Could not write {path}: {e}")

    return updated or bool(primary_ip)


def watch_network(interval: float = 3.0, port: int = 8080):
    """Continuously monitors network state and updates host_network.json on changes."""
    logger.info(f"Starting host network LAN monitor (polling every {interval}s on port {port})...")
    sync_once(port)
    last_ip = None
    try:
        while True:
            time.sleep(interval)
            primary_ip, _ = detect_windows_active_adapters()
            if primary_ip != last_ip:
                logger.info(f"Network change detected: {last_ip} -> {primary_ip}")
                sync_once(port)
                last_ip = primary_ip
    except KeyboardInterrupt:
        logger.info("Host network LAN monitor stopped.")


def main():
    parser = argparse.ArgumentParser(description="Host LAN IP Detection & Docker Sync")
    parser.add_argument("--once", action="store_true", help="Perform single detection and exit")
    parser.add_argument("--watch", action="store_true", help="Run background monitor loop")
    parser.add_argument("--interval", type=float, default=3.0, help="Watch interval in seconds (default: 3.0)")
    parser.add_argument("--port", type=int, default=8080, help="External published port (default: 8080)")
    args = parser.parse_args()

    if args.watch:
        watch_network(interval=args.interval, port=args.port)
    else:
        sync_once(port=args.port)


if __name__ == "__main__":
    main()
