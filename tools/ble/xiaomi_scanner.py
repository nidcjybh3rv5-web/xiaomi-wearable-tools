import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from bleak import BleakClient, BleakScanner

OUTPUT = Path(__file__).resolve().parent / "scan_result.json"
KEYWORDS = ("xiaomi", "mi band", "redmi", "miband", "watch", "band")
MAX_SCAN_SECONDS = 10.0
CONNECT_TIMEOUT_SECONDS = 15.0


def is_candidate(name: str, address: str) -> bool:
    """Return True for likely Xiaomi/Redmi wearable advertisements."""
    blob = f"{name} {address}".casefold()
    return any(keyword in blob for keyword in KEYWORDS)


def sort_matches(matches: list[dict]) -> list[dict]:
    """Sort strongest RSSI first, while keeping unknown RSSI at the end."""
    return sorted(
        matches,
        key=lambda item: item["rssi"] if item["rssi"] is not None else -999,
        reverse=True,
    )


def save_result(result: dict) -> None:
    OUTPUT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


async def discover_devices() -> list[dict]:
    discovered = await BleakScanner.discover(
        timeout=MAX_SCAN_SECONDS,
        return_adv=True,
    )

    matches = []
    for device, advertisement in discovered.values():
        name = (advertisement.local_name or device.name or "").strip()
        address = str(device.address)
        if not is_candidate(name, address):
            continue

        matches.append(
            {
                "name": name,
                "address": address,
                "rssi": getattr(advertisement, "rssi", None),
            }
        )

    # Avoid duplicate advertisements that may be returned by a platform.
    unique = {item["address"]: item for item in matches}
    return sort_matches(list(unique.values()))


async def inspect_gatt(selected: dict, result: dict) -> None:
    print(f"\nConnecting to {selected['name'] or selected['address']}...")
    try:
        async with BleakClient(
            selected["address"],
            timeout=CONNECT_TIMEOUT_SECONDS,
        ) as client:
            result["connected"] = bool(client.is_connected)
            print(f"Connected: {client.is_connected}")

            for service in client.services:
                service_item = {
                    "uuid": str(service.uuid),
                    "description": getattr(service, "description", ""),
                    "characteristics": [],
                }

                for characteristic in service.characteristics:
                    service_item["characteristics"].append(
                        {
                            "uuid": str(characteristic.uuid),
                            "description": getattr(characteristic, "description", ""),
                            "properties": sorted(
                                str(prop) for prop in characteristic.properties
                            ),
                        }
                    )

                result["gatt"].append(service_item)

            print(f"Discovered {len(result['gatt'])} GATT service(s).")
    except Exception as exc:
        result["connected"] = False
        result["gatt_error"] = f"{type(exc).__name__}: {exc}"
        print(f"GATT connection/discovery failed: {result['gatt_error']}")


async def main() -> None:
    print(
        "Scanning for Xiaomi / Redmi wearable BLE devices "
        f"for {MAX_SCAN_SECONDS:.0f} seconds..."
    )

    result = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "matches": [],
        "selected": None,
        "connected": False,
        "gatt": [],
    }

    try:
        result["matches"] = await discover_devices()
    except Exception as exc:
        result["scan_error"] = f"{type(exc).__name__}: {exc}"
        save_result(result)
        print(f"BLE scan failed: {result['scan_error']}")
        print(f"Saved: {OUTPUT}")
        return

    print(f"Found {len(result['matches'])} possible wearable device(s).")
    for index, item in enumerate(result["matches"], 1):
        print(
            f"[{index}] {item['name'] or '(no name)'} | "
            f"{item['address']} | RSSI {item['rssi']}"
        )

    if not result["matches"]:
        save_result(result)
        print(f"\nNo matching device found. Saved: {OUTPUT}")
        return

    try:
        choice = input(
            "\nEnter device number to inspect GATT "
            "(Enter to skip): "
        ).strip()
    except (EOFError, KeyboardInterrupt):
        choice = ""

    if not choice:
        save_result(result)
        print(f"Saved: {OUTPUT}")
        return

    try:
        index = int(choice)
    except ValueError:
        print("Invalid selection. No connection attempted.")
        save_result(result)
        return

    if not 1 <= index <= len(result["matches"]):
        print("Selection is out of range. No connection attempted.")
        save_result(result)
        return

    selected = result["matches"][index - 1]
    result["selected"] = selected

    await inspect_gatt(selected, result)
    save_result(result)
    print(f"\nSaved result to: {OUTPUT}")


if __name__ == "__main__":
    asyncio.run(main())
