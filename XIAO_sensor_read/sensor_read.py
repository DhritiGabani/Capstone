import asyncio
import csv
import time
import struct
from datetime import datetime
from bleak import BleakClient

UART_SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
UART_TX_UUID      = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"

IMU1_ADDR = "262E0B1D-719B-95F2-FBEC-B7F5E634D7F6"
IMU2_ADDR = "C3B57F1E-FF3A-ED4D-0ED7-C951ECB14078"

PKT_FMT  = "<Ihhhhhh"
PKT_SIZE = struct.calcsize(PKT_FMT)  

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

def unpack_packet(pkt: bytes):
    t_us, ax_mg, ay_mg, az_mg, gx_cdegps, gy_cdegps, gz_cdegps = struct.unpack(PKT_FMT, pkt)
    ax_g = ax_mg / 1000.0
    ay_g = ay_mg / 1000.0
    az_g = az_mg / 1000.0
    gx_dps = gx_cdegps / 100.0
    gy_dps = gy_cdegps / 100.0
    gz_dps = gz_cdegps / 100.0
    return t_us, ax_g, ay_g, az_g, gx_dps, gy_dps, gz_dps

async def stream_two_binary(dev1_addr: str, dev2_addr: str, csv_path: str):
    
    f = open(csv_path, "w", newline="", buffering=1024 * 1024)
    w = csv.writer(f)
    w.writerow(["t_host_s", "device", "t_dev_us", "ax_g", "ay_g", "az_g", "gx_dps", "gy_dps", "gz_dps"])
    f.flush()
    print(f"\n Writing to: {csv_path}")
    print(f"Expecting {PKT_SIZE}-byte packets ({PKT_FMT}) from each IMU.\n")

    client1 = await connect_and_check_nus(dev1_addr)
    client2 = await connect_and_check_nus(dev2_addr)

    # Separate buffers + counters per device
    buf = {"imu1": bytearray(), "imu2": bytearray()}
    samp = {"imu1": 0, "imu2": 0}
    noti = {"imu1": 0, "imu2": 0}
    byt  = {"imu1": 0, "imu2": 0}

    t0 = time.time()
    last_flush = time.time()

    def make_handler(label: str):
        def handler(sender, data: bytearray):
            nonlocal t0, last_flush

            noti[label] += 1
            byt[label]  += len(data)

            b = buf[label]
            b.extend(data)

            # Unpack as many full packets as possible
            while len(b) >= PKT_SIZE:
                pkt = b[:PKT_SIZE]
                del b[:PKT_SIZE]

                try:
                    t_us, ax_g, ay_g, az_g, gx_dps, gy_dps, gz_dps = unpack_packet(pkt)
                except struct.error:
                    # If alignment ever breaks, clear buffer for this device
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

            # Print rates once per second (combined line)
            now = time.time()
            if now - t0 >= 1.0:
                dt = now - t0
                hz1 = samp["imu1"] / dt
                hz2 = samp["imu2"] / dt
                n1  = noti["imu1"] / dt
                n2  = noti["imu2"] / dt
                b1  = byt["imu1"] / dt
                b2  = byt["imu2"] / dt
                print(
                    f"Hz imu1={hz1:.1f} (notifs {n1:.1f}, {b1:.0f} B/s)  |  "
                    f"imu2={hz2:.1f} (notifs {n2:.1f}, {b2:.0f} B/s)"
                )
                # reset counters
                for k in ("imu1", "imu2"):
                    samp[k] = noti[k] = byt[k] = 0
                t0 = now

            # Flush every ~3s for speed
            if now - last_flush >= 3.0:
                f.flush()
                last_flush = now

        return handler

    try:
        await client1.start_notify(UART_TX_UUID, make_handler("imu1"))
        await client2.start_notify(UART_TX_UUID, make_handler("imu2"))

        print("Streaming both IMUs (binary). Ctrl+C to stop.\n")
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
    await stream_two_binary(IMU1_ADDR, IMU2_ADDR, csv_path)

if __name__ == "__main__":
    asyncio.run(main())
