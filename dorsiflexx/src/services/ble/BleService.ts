import { BleManager, Device, Subscription } from "react-native-ble-plx";
import { Platform, PermissionsAndroid } from "react-native";

import type {
  SensorReading,
  BleConnectionState,
  StreamingStats,
} from "./types";

// BLE UUIDs (matching firmware / Python ble_manager.py)
const UART_SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e";
const UART_TX_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e";

const EXPECTED_NAMES = ["IMU_1", "IMU_2"];
const SCAN_TIMEOUT_MS = 15_000;
const DRAIN_DELAY_MS = 300;
const STATS_INTERVAL_MS = 1_000;
const PKT_SIZE = 16; // <Ihhhhhh = uint32 + 6x int16

type StateListener = (state: BleConnectionState) => void;
type StatsListener = (stats: StreamingStats) => void;

class BleService {
  private manager: BleManager;
  private devices: Map<string, Device> = new Map(); // name -> device
  private subscriptions: Subscription[] = [];
  private readings: SensorReading[] = [];
  private buffers: Map<string, number[]> = new Map();
  private sampleCounts = { imu1: 0, imu2: 0 };
  private streamStartTime = 0;
  private statsTimer: ReturnType<typeof setInterval> | null = null;

  private state: BleConnectionState = "idle";
  private stateListeners: Set<StateListener> = new Set();
  private statsListeners: Set<StatsListener> = new Set();

  constructor() {
    this.manager = new BleManager();
  }

  // -----------------------------------------------------------------------
  // Event subscriptions
  // -----------------------------------------------------------------------

  onStateChange(listener: StateListener): () => void {
    this.stateListeners.add(listener);
    listener(this.state);
    return () => {
      this.stateListeners.delete(listener);
    };
  }

  onStatsUpdate(listener: StatsListener): () => void {
    this.statsListeners.add(listener);
    return () => {
      this.statsListeners.delete(listener);
    };
  }

  private setState(next: BleConnectionState) {
    this.state = next;
    this.stateListeners.forEach((l) => l(next));
  }

  private emitStats() {
    const stats: StreamingStats = {
      imu1Count: this.sampleCounts.imu1,
      imu2Count: this.sampleCounts.imu2,
      elapsedSeconds: Math.round((Date.now() - this.streamStartTime) / 1000),
    };
    this.statsListeners.forEach((l) => l(stats));
  }

  // -----------------------------------------------------------------------
  // Permissions
  // -----------------------------------------------------------------------

  async requestPermissions(): Promise<boolean> {
    if (Platform.OS === "ios") {
      // iOS permissions handled via Info.plist
      return true;
    }

    if (Platform.OS === "android") {
      const granted = await PermissionsAndroid.requestMultiple([
        PermissionsAndroid.PERMISSIONS.BLUETOOTH_SCAN,
        PermissionsAndroid.PERMISSIONS.BLUETOOTH_CONNECT,
        PermissionsAndroid.PERMISSIONS.ACCESS_FINE_LOCATION,
      ]);

      return Object.values(granted).every(
        (v) => v === PermissionsAndroid.RESULTS.GRANTED,
      );
    }

    return true;
  }

  // -----------------------------------------------------------------------
  // Scan + Connect
  // -----------------------------------------------------------------------

  async scanAndConnect(): Promise<void> {
    this.setState("scanning");

    const permOk = await this.requestPermissions();
    if (!permOk) {
      this.setState("error");
      throw new Error(
        "Bluetooth permissions not granted. Please enable them in Settings.",
      );
    }

    // Wait for BLE to be powered on
    await new Promise<void>((resolve, reject) => {
      const sub = this.manager.onStateChange((bleState) => {
        if (bleState === "PoweredOn") {
          sub.remove();
          resolve();
        }
      }, true);

      setTimeout(() => {
        sub.remove();
        reject(new Error("Bluetooth is not enabled. Please turn on Bluetooth."));
      }, 5_000);
    });

    const found = new Map<string, Device>();

    await new Promise<void>((resolve, reject) => {
      const timeout = setTimeout(() => {
        this.manager.stopDeviceScan();
        if (found.size < 2) {
          reject(
            new Error(
              `Scan timed out. Found ${found.size}/2 sensors. ` +
                "Make sure both IMU devices are powered on and nearby.",
            ),
          );
        } else {
          resolve();
        }
      }, SCAN_TIMEOUT_MS);

      this.manager.startDeviceScan(
        [UART_SERVICE_UUID],
        { allowDuplicates: false },
        (error, device) => {
          if (error) {
            clearTimeout(timeout);
            this.manager.stopDeviceScan();
            reject(new Error(`BLE scan error: ${error.message}`));
            return;
          }

          if (device?.name && EXPECTED_NAMES.includes(device.name)) {
            found.set(device.name, device);
            if (found.size === 2) {
              clearTimeout(timeout);
              this.manager.stopDeviceScan();
              resolve();
            }
          }
        },
      );
    });

    // Connect to both devices
    this.setState("connecting");
    this.devices.clear();

    for (const [name, device] of found.entries()) {
      const connected = await device.connect({ timeout: 12_000 });
      await connected.discoverAllServicesAndCharacteristics();
      this.devices.set(name, connected);
    }

    this.setState("connected");
  }

  // -----------------------------------------------------------------------
  // Streaming
  // -----------------------------------------------------------------------

  async startStreaming(): Promise<void> {
    if (this.devices.size < 2) {
      throw new Error("Not connected to both sensors.");
    }

    this.readings = [];
    this.buffers.set("imu1", []);
    this.buffers.set("imu2", []);
    this.sampleCounts = { imu1: 0, imu2: 0 };
    this.streamStartTime = Date.now();

    this.setState("streaming");

    // Subscribe to UART TX notifications on each device
    const imu1Device = this.devices.get("IMU_1");
    const imu2Device = this.devices.get("IMU_2");

    if (imu1Device) {
      const sub = imu1Device.monitorCharacteristicForService(
        UART_SERVICE_UUID,
        UART_TX_UUID,
        (error, characteristic) => {
          if (error || !characteristic?.value) return;
          this.handleNotification("imu1", characteristic.value);
        },
      );
      this.subscriptions.push(sub);
    }

    if (imu2Device) {
      const sub = imu2Device.monitorCharacteristicForService(
        UART_SERVICE_UUID,
        UART_TX_UUID,
        (error, characteristic) => {
          if (error || !characteristic?.value) return;
          this.handleNotification("imu2", characteristic.value);
        },
      );
      this.subscriptions.push(sub);
    }

    // Start stats emission timer
    this.statsTimer = setInterval(() => this.emitStats(), STATS_INTERVAL_MS);
  }

  private handleNotification(label: string, base64Value: string) {
    const bytes = base64ToBytes(base64Value);
    const buf = this.buffers.get(label);
    if (!buf) return;

    buf.push(...bytes);

    while (buf.length >= PKT_SIZE) {
      const pkt = buf.splice(0, PKT_SIZE);
      const dataView = new DataView(new Uint8Array(pkt).buffer);

      try {
        const timestamp_us = dataView.getUint32(0, true); // little-endian
        const ax_mg = dataView.getInt16(4, true);
        const ay_mg = dataView.getInt16(6, true);
        const az_mg = dataView.getInt16(8, true);
        const gx_cdeg = dataView.getInt16(10, true);
        const gy_cdeg = dataView.getInt16(12, true);
        const gz_cdeg = dataView.getInt16(14, true);

        this.readings.push({
          device: label,
          timestamp_us,
          ax: ax_mg / 1000.0,
          ay: ay_mg / 1000.0,
          az: az_mg / 1000.0,
          gx: gx_cdeg / 100.0,
          gy: gy_cdeg / 100.0,
          gz: gz_cdeg / 100.0,
        });

        if (label === "imu1") this.sampleCounts.imu1++;
        else this.sampleCounts.imu2++;
      } catch {
        // Malformed packet — clear buffer and break
        buf.length = 0;
        break;
      }
    }
  }

  // -----------------------------------------------------------------------
  // Stop Streaming
  // -----------------------------------------------------------------------

  async stopStreaming(): Promise<SensorReading[]> {
    this.setState("stopping");

    // Stop stats timer
    if (this.statsTimer) {
      clearInterval(this.statsTimer);
      this.statsTimer = null;
    }

    // Remove notification subscriptions
    for (const sub of this.subscriptions) {
      sub.remove();
    }
    this.subscriptions = [];

    // Drain delay for in-flight callbacks
    await new Promise((r) => setTimeout(r, DRAIN_DELAY_MS));

    // Capture readings
    const captured = [...this.readings];
    this.readings = [];

    // Disconnect devices
    for (const [, device] of this.devices) {
      try {
        await device.cancelConnection();
      } catch {
        // ignore disconnect errors
      }
    }
    this.devices.clear();

    this.setState("idle");
    return captured;
  }

  // -----------------------------------------------------------------------
  // Cancel (cleanup without returning readings)
  // -----------------------------------------------------------------------

  async cancelSession(): Promise<void> {
    if (this.statsTimer) {
      clearInterval(this.statsTimer);
      this.statsTimer = null;
    }

    for (const sub of this.subscriptions) {
      sub.remove();
    }
    this.subscriptions = [];
    this.readings = [];

    for (const [, device] of this.devices) {
      try {
        await device.cancelConnection();
      } catch {
        // ignore
      }
    }
    this.devices.clear();

    this.setState("idle");
  }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function base64ToBytes(base64: string): number[] {
  const binaryString = atob(base64);
  const bytes: number[] = new Array(binaryString.length);
  for (let i = 0; i < binaryString.length; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }
  return bytes;
}

export default new BleService();
