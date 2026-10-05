import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from bleak import BleakClient, BleakScanner

OUTPUT = Path(__file__).resolve().parent / "scan_result.json"
KEYWORDS = (
    "xiaomi",
    "mi band",
    "band",
    "redmi",
    "watch",
)


def is_candidate(name: str, address: str) -> bool:
    blob = f"{name} {address}".lower()
    return any(word in blob for word in KEYWORDS)


async def main() -> None:
    print("Scanning for Xiaomi / Redmi wearable BLE devices for 10 seconds...")
    discovered = await BleakScanner.discover(timeout=10.0, return_adv=True)

    matches = []
    for device, adv in discovered.values():
        name = (device.name or adv.local_name or "").strip()
        if not is_candidate(name, device.address):
            continue
        matches.append(
            {
                "name": name,
                "address": device.address,
                "rssi": getattr(adv, "rssi", None),
            }
        )

    matches.sort(key=lambda item: item["rssi"] if item["rssi"] is not None else -999, reverse=True)

    print(f"Found {len(matches)} possible wearable device(s).")
    for index, item in enumerate(matches, 1):
        print(
            f"[{index}] {item['name'] or '(no name)'} | "
            f"{item['address']} | RSSI {item['rssi']}"
        )

    result = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "matches": matches,
        "selected": None,
        "gatt": [],
    }

    if not matches:
        OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nNo matching device found. Saved: {OUTPUT}")
        return

    choice = input("\nEnter device number to inspect GATT (Enter to skip): ").strip()
    if not choice:
        OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Saved: {OUTPUT}")
        return

    try:
        selected = matches[int(choice) - 1]
    except (ValueError, IndexError):
        print("Invalid selection. No connection attempted.")
        OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return

    result["selected"] = selected

    print(f"\nConnecting to {selected['name'] or selected['address']}...")
    try:
        async with BleakClient(selected["address"], timeout=15.0) as client:
            print(f"Connected: {client.is_connected}")
            for service in client.services:
                service_item = {
                    "uuid": str(service.uuid),
                    "description": getattr(service, "description", ""),
                    "characteristics": [],
                }
                for char in service.characteristics:
                    service_item["characteristics"].append(
                        {
                            "uuid": str(char.uuid),
                            "description": getattr(char, "description", ""),
                            "properties": list(char.properties),
                        }
                    )
                result["gatt"].append(service_item)
            print(f"Discovered {len(result['gatt'])} GATT service(s).")
    except Exception as exc:
        result["gatt_error"] = f"{type(exc).__name__}: {exc}"
        print(f"GATT connection/discovery failed: {result['gatt_error']}")

    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved result to: {OUTPUT}")


if __name__ == "__main__":
    asyncio.run(main())
