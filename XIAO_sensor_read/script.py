import asyncio
from bleak import BleakScanner


async def main():
    print("Scanning for 6 seconds...")
    results = await BleakScanner.discover(timeout=6.0, return_adv=True)

    if not results:
        print("No devices found. Is Bluetooth on?")
        return

    print(f"\nFound {len(results)} device(s):\n")
    for addr, (device, adv) in results.items():
        print(f"  Name:    {device.name!r}")
        print(f"  Address: {addr}")
        print(f"  RSSI:    {adv.rssi} dBm")
        print(f"  UUIDs:   {adv.service_uuids}")
        print()

asyncio.run(main())
