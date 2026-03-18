import asyncio
import csv
import time
import struct
from datetime import datetime

from bleak import BleakClient, BleakScanner

UART_SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
UART_TX_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"

EXPECTED_ID_1 = "IMU_1"
EXPECTED_ID_2 = "IMU_2"

# ---------------------------------------------------------
# ✅ Custom Device-ID characteristic UUIDs (YOU set in FW)
# ---------------------------------------------------------
# Replace these with the UUID(s) you implement on the XIAO.
DEVICE_ID_CHAR_UUID = "12345678-1234-1234-1234-1234567890ac"

SCAN_SECONDS = 6.0

PKT_FMT = "<Ihhhhhh"
PKT_SIZE = struct.calcsize(PKT_FMT)  # 16


def make_csv_filename(prefix="imu2_bin"):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{ts}.csv"


async def connect_and_check_nus(address: str):
    client = BleakClient(address, timeout=12.0)
    await client.connect()
    svc_uuids = [s.uuid.lower() for s in client.services]
    if UART_SERVICE_UUID not in svc_uuids:
        await client.disconnect()
        raise RuntimeError(f"No Nordic UART Service (NUS) on device {address}")
    return client


async def read_device_id(client: BleakClient) -> str | None:
    """
    Reads your custom Device ID characteristic (string).
    Returns None if missing/unreadable.
    """
    try:
        raw = await client.read_gatt_char(DEVICE_ID_CHAR_UUID)
        return raw.decode("utf-8", errors="ignore").strip("\x00\r\n ").strip()
    except Exception:
        return None


def unpack_packet(pkt: bytes):
    t_us, ax_mg, ay_mg, az_mg, gx_cdegps, gy_cdegps, gz_cdegps = struct.unpack(
        PKT_FMT, pkt)
    ax_g = ax_mg / 1000.0
    ay_g = ay_mg / 1000.0
    az_g = az_mg / 1000.0
    gx_dps = gx_cdegps / 100.0
    gy_dps = gy_cdegps / 100.0
    gz_dps = gz_cdegps / 100.0
    return t_us, ax_g, ay_g, az_g, gx_dps, gy_dps, gz_dps


async def scan_candidates(timeout=SCAN_SECONDS):
    """
    Scan BLE devices and return a list of candidates.
    Uses advertised local name rather than device.name.
    """
    results = await BleakScanner.discover(timeout=timeout, return_adv=True)
    nus = []
    all_devices = []

    for address, (device, adv) in results.items():
        # Use advertised local name first, fallback to device.name
        name = (adv.local_name or device.name or "").strip()
        all_devices.append((device, adv, name))

        uuids = [u.lower() for u in (adv.service_uuids or [])]
        if UART_SERVICE_UUID in uuids:
            nus.append((device, adv, name))

    return nus if nus else all_devices


async def resolve_two_imus():
    device_advs = await scan_candidates()
    if not device_advs:
        raise RuntimeError("No BLE devices found. Is Bluetooth on?")

    found_by_id = {}
    found_by_name = {}

    def rssi_key(pair):
        _, adv, _ = pair  # unpack device, adv, name
        return adv.rssi if adv.rssi is not None else -999

    device_advs = sorted(device_advs, key=rssi_key, reverse=True)

    for device, adv, name in device_advs:
        addr = device.address
        if name:
            found_by_name[name] = addr

        if EXPECTED_ID_1 in found_by_id and EXPECTED_ID_2 in found_by_id:
            break

        try:
            client = await connect_and_check_nus(addr)
        except Exception:
            continue

        try:
            dev_id = await read_device_id(client)
            if dev_id:
                found_by_id[dev_id] = addr
        finally:
            try:
                await client.disconnect()
            except Exception:
                pass

    # Preferred: custom device ID characteristic
    if EXPECTED_ID_1 in found_by_id and EXPECTED_ID_2 in found_by_id:
        return found_by_id[EXPECTED_ID_1], found_by_id[EXPECTED_ID_2]

    # Fallback: advertised name
    if EXPECTED_ID_1 in found_by_name and EXPECTED_ID_2 in found_by_name:
        return found_by_name[EXPECTED_ID_1], found_by_name[EXPECTED_ID_2]

    raise RuntimeError(
        "Could not resolve both IMUs.\n"
        f"Found IDs: {list(found_by_id.keys())}\n"
        f"Found names: {list(found_by_name.keys())}\n"
        "Make sure firmware exposes DEVICE_ID_CHAR_UUID and returns "
        f"'{EXPECTED_ID_1}' and '{EXPECTED_ID_2}', OR names match those exactly."
    )


async def stream_two_binary(dev1_addr: str, dev2_addr: str, csv_path: str):
    f = open(csv_path, "w", newline="", buffering=1024 * 1024)
    w = csv.writer(f)
    w.writerow(["t_host_s", "device", "t_dev_us", "ax_g",
               "ay_g", "az_g", "gx_dps", "gy_dps", "gz_dps"])
    f.flush()
    print(f"\n✅ Writing to: {csv_path}")
    print(f"Expecting {PKT_SIZE}-byte packets ({PKT_FMT}) from each IMU.\n")

    client1 = await connect_and_check_nus(dev1_addr)
    client2 = await connect_and_check_nus(dev2_addr)

    buf = {"imu1": bytearray(), "imu2": bytearray()}
    samp = {"imu1": 0, "imu2": 0}
    noti = {"imu1": 0, "imu2": 0}
    byt = {"imu1": 0, "imu2": 0}

    t0 = time.time()
    last_flush = time.time()

    def make_handler(label: str):
        def handler(sender, data: bytearray):
            nonlocal t0, last_flush

            noti[label] += 1
            byt[label] += len(data)

            b = buf[label]
            b.extend(data)

            while len(b) >= PKT_SIZE:
                pkt = b[:PKT_SIZE]
                del b[:PKT_SIZE]

                try:
                    t_us, ax_g, ay_g, az_g, gx_dps, gy_dps, gz_dps = unpack_packet(
                        pkt)
                except struct.error:
                    b.clear()
                    break

                t_host = time.time()
                w.writerow([
                    f"{t_host:.6f}",
                    label,
                    t_us,
                    f"{ax_g:.6f}", f"{ay_g:.6f}", f"{az_g:.6f}",
                    f"{gx_dps:.6f}", f"{gy_dps:.6f}", f"{gz_dps:.6f}",
                ])
                samp[label] += 1

            now = time.time()
            if now - t0 >= 1.0:
                dt = now - t0
                hz1 = samp["imu1"] / dt
                hz2 = samp["imu2"] / dt
                n1 = noti["imu1"] / dt
                n2 = noti["imu2"] / dt
                b1 = byt["imu1"] / dt
                b2 = byt["imu2"] / dt
                print(
                    f"Hz imu1={hz1:.1f} (notifs {n1:.1f}, {b1:.0f} B/s)  |  "
                    f"imu2={hz2:.1f} (notifs {n2:.1f}, {b2:.0f} B/s)"
                )
                for k in ("imu1", "imu2"):
                    samp[k] = noti[k] = byt[k] = 0
                t0 = now

            if now - last_flush >= 3.0:
                f.flush()
                last_flush = now

        return handler

    try:
        await client1.start_notify(UART_TX_UUID, make_handler("imu1"))
        await client2.start_notify(UART_TX_UUID, make_handler("imu2"))

        print(
            f"✅ Streaming both IMUs (binary). imu1={dev1_addr}  imu2={dev2_addr}")
        print("Ctrl+C to stop.\n")
        while True:
            await asyncio.sleep(1)

    finally:
        for client in (client1, client2):
            try:
                await client.stop_notify(UART_TX_UUID)
            except Exception:
                pass
            try:
                await client.disconnect()
            except Exception:
                pass
        f.flush()
        f.close()
        print("Stopped and closed CSV.")


async def main():
    csv_path = make_csv_filename()

    # ✅ NEW: automatically find the two devices each run
    imu1_addr, imu2_addr = await resolve_two_imus()

    await stream_two_binary(imu1_addr, imu2_addr, csv_path)

if __name__ == "__main__":
    asyncio.run(main())
