import asyncio
from bleak import BleakScanner


async def scan(timeout=5.0):
    print("Scanning for BLE devices...\n")

    seen = {}  # address -> (name, rssi)

    def cb(device, adv):
        # adv.local_name is the real advertised name (when available)
        name = adv.local_name or device.name or "UNKNOWN"
        rssi = adv.rssi

        # Save latest observation
        seen[device.address] = (name, rssi)

    scanner = BleakScanner(detection_callback=cb)
    await scanner.start()
    await asyncio.sleep(timeout)
    await scanner.stop()

    # Print results
    for addr, (name, rssi) in sorted(seen.items(), key=lambda x: (x[1][0], x[0])):
        print(f"Name: {name}")
        print(f"Address (CoreBluetooth UUID): {addr}")
        print(f"RSSI: {rssi}")
        print("-" * 40)

asyncio.run(scan(6.0))
