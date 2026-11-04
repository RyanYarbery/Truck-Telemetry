#!/usr/bin/env python3

import re
import time
import serial
from serial import SerialException

PORT = "/dev/rfcomm0"
BAUD = 115200

GENERIC_HEADER = "616AF1"
FORD_PCM_HEADER = "C410F1"

DIESEL_DENSITY_G_PER_L = 840.0
LITERS_PER_GALLON = 3.785411784


def clean_response(text):
    text = text.replace("\r", " ").replace("\n", " ")
    text = text.replace(">", " ")
    return " ".join(text.split())


def send_command(ser, command, wait=0.15):
    ser.reset_input_buffer()
    ser.write((command + "\r").encode())
    ser.flush()
    time.sleep(wait)
    return clean_response(ser.read(4096).decode(errors="replace"))


def compact_hex(response):
    return "".join(re.findall(r"[0-9A-Fa-f]", response)).upper()


def set_header(ser, header):
    response = send_command(ser, f"ATSH{header}", 0.10)
    if "OK" not in response:
        raise RuntimeError(f"Failed setting header {header}: {response}")


def decode_generic_u8(response, pid):
    data = compact_hex(response)
    m = re.search(rf"41{pid}([0-9A-F]{{2}})", data)
    return int(m.group(1), 16) if m else None


def decode_rpm(response):
    data = compact_hex(response)
    m = re.search(r"410C([0-9A-F]{4})", data)
    return int(m.group(1), 16) / 4.0 if m else None


def decode_speed(response):
    raw = decode_generic_u8(response, "0D")
    return raw * 0.621371 if raw is not None else None


def decode_map(response):
    raw = decode_generic_u8(response, "0B")
    return float(raw) if raw is not None else None


def decode_voltage(response):
    m = re.search(r"([0-9]+(?:\.[0-9]+)?)V", response)
    return float(m.group(1)) if m else None


def enhanced_payload(response, pid):
    data = compact_hex(response)
    m = re.search(rf"62{pid}([0-9A-F]+)", data)
    return m.group(1) if m else None


def decode_icp(response):
    payload = enhanced_payload(response, "1446")
    if not payload or len(payload) < 4:
        return None
    return int(payload[:4], 16) * 0.57


def decode_ipr(response):
    payload = enhanced_payload(response, "1434")
    if not payload or len(payload) < 2:
        return None
    return int(payload[:2], 16) * 0.390625


def decode_eot_f(response):
    payload = enhanced_payload(response, "1310")
    if not payload or len(payload) < 4:
        return None
    raw = int(payload[:4], 16)
    c = (raw / 100.0) - 40.0
    return c * 9.0 / 5.0 + 32.0


def decode_tft_f(response):
    payload = enhanced_payload(response, "1674")
    if not payload or len(payload) < 4:
        return None
    return int(payload[:4], 16) / 8.0


def decode_mfdes(response):
    payload = enhanced_payload(response, "1412")
    if not payload or len(payload) < 4:
        return None
    raw = int(payload[:4], 16)
    return raw * 0.0625


def decode_fuelpw(response):
    payload = enhanced_payload(response, "1410")
    if not payload or len(payload) < 4:
        return None
    raw = int(payload[:4], 16)
    return raw * 0.008


def calculate_fuel_rate(mfdes_mg, rpm):
    if mfdes_mg is None or rpm is None:
        return None

    # 7.3L Power Stroke:
    # 8 cylinders, 4-stroke engine
    # => 4 injection events per crankshaft revolution
    mg_per_min = mfdes_mg * rpm * 4.0

    g_per_hour = (mg_per_min / 1000.0) * 60.0
    liters_per_hour = g_per_hour / DIESEL_DENSITY_G_PER_L
    gallons_per_hour = liters_per_hour / LITERS_PER_GALLON

    return gallons_per_hour


def initialize(ser):
    commands = [
        ("ATZ", 1.5),
        ("ATE0", 0.2),
        ("ATL0", 0.2),
        ("ATS0", 0.2),
        ("ATH0", 0.2),
        ("ATSP1", 0.3),
    ]

    for command, wait in commands:
        response = send_command(ser, command, wait)
        print(f"{command}: {response}")

    protocol = send_command(ser, "ATDP", 0.3)
    print(f"Protocol: {protocol}")

    if "J1850 PWM" not in protocol:
        raise RuntimeError(f"Unexpected protocol: {protocol}")


def fmt(value, spec, missing="---"):
    return format(value, spec) if value is not None else missing


def run():
    while True:
        try:
            print(f"Opening {PORT}...")

            with serial.Serial(PORT, BAUD, timeout=1) as ser:
                time.sleep(0.5)
                initialize(ser)

                while True:
                    # Generic OBD-II
                    set_header(ser, GENERIC_HEADER)

                    rpm = decode_rpm(send_command(ser, "010C"))
                    speed = decode_speed(send_command(ser, "010D"))
                    map_kpa = decode_map(send_command(ser, "010B"))

                    # Ford enhanced PCM data
                    set_header(ser, FORD_PCM_HEADER)

                    icp = decode_icp(send_command(ser, "221446"))
                    ipr = decode_ipr(send_command(ser, "221434"))
                    eot = decode_eot_f(send_command(ser, "221310"))
                    tft = decode_tft_f(send_command(ser, "221674"))
                    mfdes = decode_mfdes(send_command(ser, "221412"))
                    fuelpw = decode_fuelpw(send_command(ser, "221410"))

                    # Adapter voltage
                    voltage = decode_voltage(send_command(ser, "ATRV"))

                    # Derived fuel rate / MPG
                    gph = calculate_fuel_rate(mfdes, rpm)

                    if (
                        speed is not None
                        and gph is not None
                        and speed > 1.0
                        and gph > 0.0
                    ):
                        mpg = speed / gph
                    else:
                        mpg = None

                    print(
                        f"RPM {fmt(rpm, '5.0f'):>5} | "
                        f"Speed {fmt(speed, '5.1f'):>5} mph | "
                        f"ICP {fmt(icp, '6.0f'):>6} psi | "
                        f"IPR {fmt(ipr, '4.1f'):>4}% | "
                        f"EOT {fmt(eot, '5.1f'):>5} F | "
                        f"TFT {fmt(tft, '5.1f'):>5} F | "
                        f"MAP {fmt(map_kpa, '4.0f'):>4} kPa | "
                        f"V {fmt(voltage, '4.1f'):>4} | "
                        f"MFDES {fmt(mfdes, '5.2f'):>5} mg | "
                        f"PW {fmt(fuelpw, '4.2f'):>4} ms | "
                        f"GPH {fmt(gph, '4.2f'):>4} | "
                        f"MPG {fmt(mpg, '5.1f'):>5}"
                    )

                    time.sleep(0.2)

        except KeyboardInterrupt:
            print("\nStopped.")
            break

        except (SerialException, OSError, RuntimeError) as exc:
            print(f"Telemetry connection error: {exc}")
            print("Retrying in 3 seconds...")
            time.sleep(3)


if __name__ == "__main__":
    run()
