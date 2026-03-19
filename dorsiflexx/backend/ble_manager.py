"""
BLE connection and streaming manager for dorsiflexx backend.

Adapts the logic from XIAO_sensor_read/sensor_read.py into a start/stop
interface that buffers SensorReading objects in memory.
"""

import asyncio
import logging
import struct
import time
from typing import Optional

from bleak import BleakClient, BleakScanner

from sensor import SensorReading

log = logging.getLogger(__name__)

# BLE UUIDs (same as sensor_read.py)
UART_SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
UART_TX_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"
DEVICE_ID_CHAR_UUID = "12345678-1234-1234-1234-1234567890ac"

EXPECTED_ID_1 = "IMU_1"
EXPECTED_ID_2 = "IMU_2"

SCAN_SECONDS = 6.0

PKT_FMT = "<Ihhhhhh"
PKT_SIZE = struct.calcsize(PKT_FMT)  # 16 bytes


def _unpack_packet(pkt: bytes):
    t_us, ax_mg, ay_mg, az_mg, gx_cdeg, gy_cdeg, gz_cdeg = struct.unpack(PKT_FMT, pkt)
    return (
        t_us,
        ax_mg / 1000.0,
        ay_mg / 1000.0,
        az_mg / 1000.0,
        gx_cdeg / 100.0,
        gy_cdeg / 100.0,
        gz_cdeg / 100.0,
    )


async def _connect_and_check_nus(address: str) -> BleakClient:
    client = BleakClient(address, timeout=12.0)
    await client.connect()
    svc_uuids = [s.uuid.lower() for s in client.services]
    if UART_SERVICE_UUID not in svc_uuids:
        await client.disconnect()
        raise RuntimeError(f"No Nordic UART Service on device {address}")
    return client


async def _read_device_id(client: BleakClient) -> Optional[str]:
    try:
        raw = await client.read_gatt_char(DEVICE_ID_CHAR_UUID)
        return raw.decode("utf-8", errors="ignore").strip("\x00\r\n ").strip()
    except Exception:
        return None


async def _resolve_shank_only() -> str:
    """Auto-discover shank IMU (IMU_1) address only."""
    results = await BleakScanner.discover(timeout=SCAN_SECONDS, return_adv=True)
    if not results:
        raise RuntimeError("No BLE devices found. Is Bluetooth on?")

    nus_devices = []
    all_devices = []
    for address, (device, adv) in results.items():
        name = (adv.local_name or device.name or "").strip()
        all_devices.append((device, adv, name))
        uuids = [u.lower() for u in (adv.service_uuids or [])]
        if UART_SERVICE_UUID in uuids:
            nus_devices.append((device, adv, name))

    device_advs = nus_devices if nus_devices else all_devices
    device_advs.sort(key=lambda t: t[1].rssi if t[1].rssi is not None else -999, reverse=True)

    # First pass: match by advertised name (fast, no connection needed)
    for device, adv, name in device_advs:
        if name == EXPECTED_ID_1:
            return device.address

    # Second pass: connect and read GATT device-id characteristic (slow fallback)
    for device, adv, name in device_advs:
        try:
            client = await _connect_and_check_nus(device.address)
        except Exception:
            continue

        try:
            dev_id = await _read_device_id(client)
            if dev_id == EXPECTED_ID_1:
                return device.address
        finally:
            try:
                await client.disconnect()
            except Exception:
                pass

    raise RuntimeError(
        f"Could not find shank sensor ({EXPECTED_ID_1}). "
        "Make sure the shank sensor is powered on and nearby."
    )


class BLEManager:
    def __init__(self) -> None:
        self._client1: Optional[BleakClient] = None
        self._readings: list[SensorReading] = []
        self._is_streaming = False
        self._buf: dict[str, bytearray] = {"imu1": bytearray()}
        self._sample_counts: dict[str, int] = {"imu1": 0}

    @property
    def is_streaming(self) -> bool:
        return self._is_streaming

    @property
    def is_connected(self) -> bool:
        return self._client1 is not None

    @property
    def sample_counts(self) -> dict[str, int]:
        return dict(self._sample_counts)

    def clear_readings(self) -> None:
        """Discard all buffered readings so the next stop only returns new data."""
        self._readings = []
        self._sample_counts = {"imu1": 0}

    async def connect(self) -> None:
        """Scan for and connect to the shank IMU sensor (IMU_1) only."""
        try:
            imu1_addr = await asyncio.wait_for(
                _resolve_shank_only(), timeout=60.0
            )
        except asyncio.TimeoutError:
            raise RuntimeError(
                "Could not find shank sensor within 60 seconds. "
                "Make sure the IMU device is powered on and nearby."
            )
        log.info("Resolved IMU1 (shank)=%s", imu1_addr)
        self._client1 = await _connect_and_check_nus(imu1_addr)
        log.info("IMU1 connected: is_connected=%s", self._client1.is_connected)

    async def start_streaming(self) -> None:
        """Subscribe to BLE notifications and begin buffering readings."""
        if self._client1 is None:
            raise RuntimeError("Not connected. Call connect() first.")

        self._readings = []
        self._buf = {"imu1": bytearray()}
        self._sample_counts = {"imu1": 0}
        self._is_streaming = True

        log.info("IMU1 connected before notify: %s", self._client1.is_connected)

        log.info("Subscribing to notifications on IMU1...")
        await self._client1.start_notify(UART_TX_UUID, self._make_handler("imu1"))
        log.info("Streaming started, waiting for data...")

        log.info("IMU1 connected after notify: %s", self._client1.is_connected)

    def _make_handler(self, label: str):
        _notif_count = [0]

        def handler(_sender, data: bytearray):
            _notif_count[0] += 1
            if _notif_count[0] <= 3:
                log.info("[%s] notification #%d: %d bytes: %s", label, _notif_count[0], len(data), data.hex())

            buf = self._buf[label]
            buf.extend(data)

            while len(buf) >= PKT_SIZE:
                pkt = buf[:PKT_SIZE]
                del buf[:PKT_SIZE]

                try:
                    t_us, ax, ay, az, gx, gy, gz = _unpack_packet(pkt)
                except struct.error:
                    log.warning("[%s] struct unpack error, clearing buffer", label)
                    buf.clear()
                    break

                self._readings.append(
                    SensorReading(
                        device=label,
                        timestamp_us=t_us,
                        ax=ax, ay=ay, az=az,
                        gx=gx, gy=gy, gz=gz,
                    )
                )
                self._sample_counts[label] += 1

            if _notif_count[0] <= 3:
                log.info("[%s] after notification #%d: total readings=%d", label, _notif_count[0], self._sample_counts[label])

        return handler

    async def stop_streaming(self) -> list[SensorReading]:
        """Stop notifications and drain in-flight callbacks, then return all buffered readings.

        Sensors remain connected after this call. Call disconnect() separately when done.
        """
        log.info("stop_streaming: sample_counts before stop = %s, total readings = %d", self._sample_counts, len(self._readings))

        # 1. Stop notifications first (while _is_streaming is still True so
        #    any last in-flight callbacks can still append to self._readings)
        if self._client1 is not None:
            try:
                await self._client1.stop_notify(UART_TX_UUID)
            except Exception:
                pass

        # 2. Let any in-flight BLE callbacks drain
        await asyncio.sleep(0.5)

        # 3. Capture readings before clearing
        readings = self._readings
        self._readings = []
        log.info("stop_streaming: returning %d readings", len(readings))

        # 4. Mark streaming as stopped (clients remain connected)
        self._is_streaming = False

        return readings

    async def disconnect(self) -> None:
        """Disconnect from the shank sensor."""
        if self._client1 is not None:
            try:
                await self._client1.disconnect()
            except Exception:
                pass
            self._client1 = None
        log.info("BLE disconnected")
