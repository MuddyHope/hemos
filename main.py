from machine import ADC, Pin
import time
import network
import urequests
import ujson
import onewire
import ds18x20

# BROWNOUT
import machine

RTC_CNTL_BROWN_OUT_REG = 0x3FF480D4
machine.mem32[RTC_CNTL_BROWN_OUT_REG] = 0

# ---------- WiFi ----------
SSID = "SpectrumSetup-A3"
PASSWORD = "reviewbakery586"
SERVER_URL = "http://192.168.1.231:8000/api/vitals"


def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if not wlan.isconnected():
        print("Connecting to WiFi...")
        wlan.connect(SSID, PASSWORD)

        timeout = 15
        while not wlan.isconnected() and timeout > 0:
            print(".")
            time.sleep(1)
            timeout -= 1

    if wlan.isconnected():
        print("Connected:", wlan.ifconfig())
        return wlan
    else:
        print("WiFi failed")
        return None


# ---------- Pulse sensor setup ----------
pulse = ADC(Pin(36))
pulse.atten(ADC.ATTN_11DB)

samples = []
SAMPLE_SIZE = 8
baseline = 0
alpha = 0.95

last_peak_time = 0
MIN_PEAK_INTERVAL = 450
ibi_list = []
bpm = 0

prev_above = False
dynamic_offset = 120

# ---------- Temperature sensor setup ----------
ds_pin = Pin(4)
ow = onewire.OneWire(ds_pin)
ds = ds18x20.DS18X20(ow)
roms = ds.scan()

if not roms:
    print("No DS18B20 found")
else:
    print("DS18B20 found")

last_temp_request = time.ticks_ms()
last_temp_read = time.ticks_ms()
temp_c = None

if roms:
    ds.convert_temp()

# ---------- Start WiFi ----------
wlan = connect_wifi()

# ---------- Send timer ----------
last_send_time = time.ticks_ms()
SEND_INTERVAL = 3000

while True:
    current_time = time.ticks_ms()

    # =========================
    # Heartbeat section
    # =========================
    raw = pulse.read()

    samples.append(raw)
    if len(samples) > SAMPLE_SIZE:
        samples.pop(0)

    smooth = sum(samples) // len(samples)

    if baseline == 0:
        baseline = smooth
    else:
        baseline = int(alpha * baseline + (1 - alpha) * smooth)

    threshold = baseline + dynamic_offset
    above = smooth > threshold

    if above and not prev_above:
        if time.ticks_diff(current_time, last_peak_time) > MIN_PEAK_INTERVAL:
            ibi = time.ticks_diff(current_time, last_peak_time)

            if last_peak_time != 0 and 400 <= ibi <= 1500:
                ibi_list.append(ibi)
                if len(ibi_list) > 8:
                    ibi_list.pop(0)

                avg_ibi = sum(ibi_list) / len(ibi_list)
                bpm = int(60000 / avg_ibi)

            last_peak_time = current_time

    prev_above = above

    # =========================
    # Temperature section
    # =========================
    if roms:
        if time.ticks_diff(current_time, last_temp_read) >= 1000:
            try:
                temp_c = ds.read_temp(roms[0])
            except Exception as e:
                print("Temp read error:", e)
                temp_c = None
            last_temp_read = current_time

        if time.ticks_diff(current_time, last_temp_request) >= 1000:
            ds.convert_temp()
            last_temp_request = current_time

    # =========================
    # Serial output
    # =========================
    if temp_c is not None:
        print("BPM:", bpm, "| Temp: {:.2f} C".format(temp_c))
    else:
        print("BPM:", bpm, "| Temp: --")

    # =========================
    # Send to server every 3 sec
    # =========================
    if time.ticks_diff(current_time, last_send_time) >= SEND_INTERVAL:
        if wlan is None or not wlan.isconnected():
            wlan = connect_wifi()

        if wlan and wlan.isconnected():
            payload = {
                "device_id": "esp32_01",
                "heart_rate": bpm,
                "body_temperature": temp_c
            }
            print("payload", payload)
            print("bpm type: ", type(bpm))
            print("body temp type :", type(temp_c))

            try:
                response = urequests.post(
                    SERVER_URL,
                    data=ujson.dumps(payload),
                    headers={"Content-Type": "application/json"}
                )
                print("Status:", response.status_code)
                print("Response:", response.text)
                response.close()
            except Exception as e:
                print("POST failed:", e)

        last_send_time = current_time

    time.sleep_ms(20)
