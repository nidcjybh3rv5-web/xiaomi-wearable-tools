"""
Xiaomi owner-side diagnostic tool

This tool is intentionally limited to legal, owner-operated diagnostics on
Xiaomi / Redmi wearables you own or are authorized to inspect.

It does NOT:
- bypass pairing
- bypass authentication
- bypass encryption
- read or expose AuthKey material from someone else's device
- access data outside the owner's local machine or authorized backup files

It does:
- scan local Windows folders for Mi Fit / Zepp / Gadgetbridge artifacts
- scan nearby BLE devices for Xiaomi/Redmi candidate advertisements
- report which owner-side files may exist for a local diagnostics workflow
- export a structured JSON report for review
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    from bleak import BleakScanner
except Exception:  # pragma: no cover
    BleakScanner = None

OUTPUT = Path(__file__).resolve().parent / "authkey_result.json"

COMMON_XIAOMI_DIR_NAMES = (
    "Mi Fit",
    "Mi Fitness",
    "MiFit",
    "Zepp",
    "Gadgetbridge",
    "Xiaomi",
    "Redmi",
)

COMMON_ANDROID_APP_MARKERS = (
    "mifit",
    "zepp",
    "gadgetbridge",
    "xiaomi",
    "redmi",
    "wearable",
)


def safe_join(root: str, *parts: str) -> str:
    return str(Path(root).joinpath(*parts))


def candidate_windows_roots() -> List[str]:
    roots: List[str] = []
    for env_name in ("LOCALAPPDATA", "APPDATA", "USERPROFILE"):
        value = os.environ.get(env_name)
        if value:
            roots.append(value)
    roots.extend([
        r"C:\Users",
        r"D:\Users",
        r"E:\Users",
    ])
    if os.name == "nt":
        roots.extend([
            r"C:\ProgramData",
            r"C:\Users\Public",
        ])
    return sorted(set(roots))


def windows_app_candidates() -> List[str]:
    candidates: List[str] = []
    for root in candidate_windows_roots():
        base = Path(root)
        if not base.exists():
            continue
        for name in COMMON_XIAOMI_DIR_NAMES:
            candidates.append(str(base / name))
        for sub in ("AppData/Local", "AppData/Roaming", "Packages"):
            p = Path(root) / sub
            if p.exists():
                for name in COMMON_XIAOMI_DIR_NAMES:
                    candidates.append(str(p / name))
    return sorted(set(candidates))


def inspect_local_filesystem() -> Dict[str, Any]:
    """Look for owner-side artifacts that may be useful for local diagnostics.

    This does not attempt to decrypt or extract secret values.
    """
    discovered: Dict[str, Any] = {
        "status": "no_owner_artifacts_found",
        "artifacts": [],
        "paths_checked": [],
    }

    seen: set[str] = set()
    for path in windows_app_candidates():
        p = Path(path)
        discovered["paths_checked"].append(path)
        if not p.exists():
            continue

        entries = []
        try:
            entries = list(p.iterdir())[:50]
        except Exception:
            entries = []

        if entries:
            artifact = {
                "path": str(p),
                "type": "directory",
                "name": p.name,
                "children": [child.name for child in entries[:10]],
            }
            discovered["artifacts"].append(artifact)
            seen.add(str(p))

    # Search for common backup/database-like file names and app directories
    search_roots = candidate_windows_roots() + [str(Path.home())]
    for root in search_roots:
        base = Path(root)
        if not base.exists():
            continue
        for search_name in ("*.db", "*.sqlite", "*.json", "*.backup", "*.ab", "*.log"):
            try:
                matches = list(base.rglob(search_name))[:40]
            except Exception:
                matches = []
            for match in matches:
                text = str(match).lower()
                if any(marker in text for marker in COMMON_ANDROID_APP_MARKERS):
                    visited = str(match)
                    if visited not in seen:
                        discovered["artifacts"].append({
                            "path": visited,
                            "type": "file",
                            "name": match.name,
                            "size_bytes": match.stat().st_size if match.exists() else 0,
                        })
                        seen.add(visited)

    if discovered["artifacts"]:
        discovered["status"] = "owner_artifacts_found"
    return discovered


async def scan_nearby_ble() -> Dict[str, Any]:
    """Scan for nearby BLE devices and list Xiaomi/Redmi candidates.

    This is diagnostic only and does not pair, authenticate, or decrypt.
    """
    result: Dict[str, Any] = {
        "status": "not_available",
        "devices": [],
        "warning": "No BLE scan was performed because the runtime does not expose a supported Bluetooth adapter.",
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
    result["warning"] = "Diagnostic BLE scan only. No pairing or auth bypass attempted."
    result["devices"] = sorted(
        matches,
        key=lambda item: item["rssi"] if item["rssi"] is not None else -999,
        reverse=True,
    )
    return result


def build_report() -> Dict[str, Any]:
    report: Dict[str, Any] = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "owner-side diagnostics only",
        "policy": {
            "no_pairing_bypass": True,
            "no_authentication_bypass": True,
            "no_encryption_bypass": True,
            "no_authkey_extraction": True,
            "requires_owner_authorization": True,
        },
        "local_artifacts": {
            "status": "pending",
            "artifacts": [],
        },
        "ble": {
            "status": "pending",
            "devices": [],
            "warning": "Waiting",
        },
        "authkey": {
            "status": "not_attempted",
            "reason": "This tool intentionally does not extract AuthKey material or bypass device security.",
            "value": None,
        },
    }
    return report


async def main() -> None:
    print("=" * 74)
    print("Xiaomi owner-side diagnostics")
    print("=" * 74)
    print("Purpose: inspect only data and device advertisements belonging to the owner.")
    print("This tool does NOT bypass pairing, authentication, encryption, or access control.")
    print("This tool does NOT extract AuthKey from other users' devices.")
    print()

    report = build_report()

    print("Scanning local filesystem for owner-side app artifacts...")
    local = inspect_local_filesystem()
    report["local_artifacts"] = local
    print(f"  local_artifacts.status = {local['status']}")
    for item in local["artifacts"][:10]:
        print(f"    - {item['path']}")

    print("\nScanning for nearby BLE candidates...")
    ble = await scan_nearby_ble()
    report["ble"] = ble
    print(f"  ble.status = {ble['status']}")
    if ble["devices"]:
        for item in ble["devices"]:
            print(f"    - {item.get('name') or '(unnamed)'} | {item.get('address')} | RSSI {item.get('rssi')}")
    else:
        print(f"    - {ble.get('warning')}")

    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved owner-only diagnostics to: {OUTPUT}")
    print("\nIf you own the device and have explicit authorization, you can review local app or backup data")
    print("without bypassing the device's security model.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        sys.exit(0)
