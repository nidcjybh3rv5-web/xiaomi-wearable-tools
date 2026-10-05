"""
Xiaomi owner-side diagnostics CLI

This tool is intentionally limited to legal, owner-validated diagnostics on
Xiaomi / Redmi wearable devices you own or are authorized to inspect.

It does NOT:
- bypass pairing
- bypass authentication
- bypass encryption
- read or expose AuthKey material from someone else's device
- access data outside the owner's local machine or authorized backup files

It does:
- scan a user-selected Windows folder (such as a copied Mi Fit / Zepp backup)
- scan nearby BLE devices for Xiaomi / Redmi candidate advertisements
- summarize whether local owner-side artifacts are present
- export a structured JSON report for review
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

try:
    from bleak import BleakScanner
except Exception:  # pragma: no cover
    BleakScanner = None

OUTPUT = Path(__file__).resolve().parent / "authkey_result.json"

MARKERS = (
    "mifit",
    "mi fit",
    "zepp",
    "gadgetbridge",
    "xiaomi",
    "redmi",
    "wearable",
    "smart band",
)

FILE_PATTERNS = (
    "*.db",
    "*.sqlite",
    "*.json",
    "*.backup",
    "*.ab",
    "*.log",
    "*.xml",
    "*.bin",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Owner-side diagnostic tool for Xiaomi wearable backups and BLE metadata."
    )
    parser.add_argument(
        "--root",
        type=str,
        default=None,
        help="Optional root directory to inspect (for example D:/XiaomiBackup).",
    )
    parser.add_argument(
        "--consent",
        action="store_true",
        help="Require explicit owner consent before running any local inspection.",
    )
    parser.add_argument(
        "--ble",
        action="store_true",
        help="Enable BLE scan. Default is enabled when a compatible Bluetooth adapter is available.",
    )
    return parser.parse_args()


def print_banner() -> None:
    print("=" * 78)
    print("Xiaomi Owner-Side Diagnostic Tool")
    print("=" * 78)
    print("Safe mode: owner consent required. No pairing/auth/encryption bypass.")
    print("This tool only inspects your own device data and your own local backup files.")
    print("It does not expose AuthKey material from other users' devices.")
    print("=" * 78)


def default_roots() -> List[str]:
    roots = []
    for env_name in ("LOCALAPPDATA", "APPDATA", "USERPROFILE"):
        value = os.environ.get(env_name)
        if value:
            roots.append(value)
    roots.extend([
        r"C:\Users",
        r"D:\Users",
        r"E:\Users",
        str(Path.home()),
    ])
    return sorted(set(roots))


def is_local_owner_path(path: str) -> bool:
    lower = path.lower()
    return any(marker in lower for marker in MARKERS)


def inspect_directory(root: str) -> Dict[str, Any]:
    base = Path(root)
    result: Dict[str, Any] = {
        "root": str(base),
        "exists": base.exists(),
        "status": "not_found",
        "files": [],
        "directories": [],
        "notes": [],
    }

    if not base.exists():
        return result

    result["status"] = "ok"
    result["directories"] = []
    result["files"] = []

    try:
        for child in sorted(base.iterdir()):
            rel = child.name.lower()
            if child.is_dir():
                result["directories"].append({
                    "name": child.name,
                    "path": str(child),
                    "likely_owner_marker": any(marker in rel for marker in MARKERS),
                })
            else:
                result["files"].append({
                    "name": child.name,
                    "path": str(child),
                    "size_bytes": child.stat().st_size if child.exists() else 0,
                    "likely_owner_marker": any(marker in rel for marker in MARKERS),
                })
    except Exception as exc:  # pragma: no cover
        result["notes"].append(f"Failed to enumerate directory: {type(exc).__name__}: {exc}")
        return result

    # Recursive deep scan for common owner-side backup names
    matches: List[Dict[str, Any]] = []
    try:
        for pattern in FILE_PATTERNS:
            for match in base.rglob(pattern):
                text = str(match).lower()
                if any(marker in text for marker in MARKERS):
                    matches.append({
                        "path": str(match),
                        "name": match.name,
                        "size_bytes": match.stat().st_size if match.exists() else 0,
                    })
    except Exception as exc:  # pragma: no cover
        result["notes"].append(f"Recursive scan failed: {type(exc).__name__}: {exc}")

    result["files"].extend(matches)
    result["files"] = sorted(result["files"], key=lambda item: item["path"].lower())
    result["directories"] = sorted(result["directories"], key=lambda item: item["path"].lower())

    if matches or any(item["likely_owner_marker"] for item in result["directories"]) or any(item["likely_owner_marker"] for item in result["files"]):
        result["status"] = "owner_artifacts_found"
    else:
        result["status"] = "no_owner_artifacts_found"

    return result


async def scan_ble() -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "status": "not_checked",
        "devices": [],
        "warning": "BLE scan skipped or unsupported in this environment.",
    }

    if BleakScanner is None:
        return result

    try:
        discovered = await BleakScanner.discover(timeout=10.0, return_adv=True)
    except Exception as exc:  # pragma: no cover
        result["status"] = "error"
        result["warning"] = f"{type(exc).__name__}: {exc}"
        return result

    matches: List[Dict[str, Any]] = []
    for device, advertisement in discovered.values():
        name = (advertisement.local_name or device.name or "").strip()
        address = str(device.address)
        blob = f"{name} {address}".casefold()
        if not any(keyword in blob for keyword in ("xiaomi", "mi band", "miband", "redmi")):
            continue
        matches.append({
            "name": name,
            "address": address,
            "rssi": getattr(advertisement, "rssi", None),
        })

    result["status"] = "ok" if matches else "no_candidates_found"
    result["warning"] = "Diagnostic BLE scan only. No pairing/auth bypass attempted."
    result["devices"] = sorted(matches, key=lambda item: item["rssi"] if item["rssi"] is not None else -999, reverse=True)
    return result


def build_report(root: str | None, consent: bool) -> Dict[str, Any]:
    roots_to_check = [root] if root else default_roots()
    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "owner-side diagnostics only",
        "owner_consent": consent,
        "policy": {
            "no_pairing_bypass": True,
            "no_authentication_bypass": True,
            "no_encryption_bypass": True,
            "no_authkey_extraction": True,
            "requires_owner_authorization": True,
        },
        "roots_checked": roots_to_check,
        "local_artifacts": [],
        "authkey": {
            "status": "not_attempted",
            "reason": "This tool intentionally does not extract AuthKey material or bypass device security.",
            "value": None,
        },
    }
    return report


async def main() -> None:
    args = parse_args()
    print_banner()

    if not args.consent:
        print("Consent is required before running this diagnostic tool.")
        print("Use: --consent to acknowledge that you own or are authorized to inspect the device and local data.")
        print("This tool will not bypass pairing/auth/encryption or extract AuthKey material.")
        sys.exit(2)

    root = args.root
    if root:
        print(f"Owner-specified root: {root}")
    else:
        print("No root path supplied; checking common Windows directories instead.")

    report = build_report(root, args.consent)
    roots_to_check = [root] if root else default_roots()

    for candidate in roots_to_check:
        p = Path(candidate)
        if not p.exists():
            continue
        result = inspect_directory(str(p))
        report["local_artifacts"].append(result)

    if args.ble:
        print("\nScanning nearby BLE devices...")
        ble = await scan_ble()
        report["ble"] = ble
        if ble["status"] == "ok":
            for device in ble["devices"]:
                print(f"  - {device.get('name') or '(unnamed)'} | {device.get('address')} | RSSI {device.get('rssi')}")
        elif ble["status"] == "no_candidates_found":
            print("  No Xiaomi/Redmi BLE devices found nearby.")
        else:
            print(f"  BLE warning: {ble.get('warning')}")
    else:
        report["ble"] = {"status": "not_checked", "devices": [], "warning": "BLE scan disabled by command line."}

    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved diagnostic report to: {OUTPUT}")
    print("\nThis report is for owner-side diagnostics only. It does not attempt to bypass pairing/authentication/encryption.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        sys.exit(0)
