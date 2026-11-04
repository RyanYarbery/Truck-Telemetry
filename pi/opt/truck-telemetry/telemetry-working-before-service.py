#!/usr/bin/env python3

import argparse
import json
import os
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

STATE_DIR = "/var/lib/truck-telemetry"
STATE_FILE = os.path.join(STATE_DIR, "trip.json")

SAVE_INTERVAL_SECONDS = 5.0


def default_state():
    return {
        "trip_miles": 0.0,
        "raw_fuel_gallons": 0.0,
        "engine_runtime_seconds": 0.0,
        "fuel_calibration": 1.0,
    }


def load_state():
    state = default_state()

    try:
        with open(STATE_FILE, "r") as f:
            loaded = json.load(f)

        for key in state:
            if key in loaded:
                state[key] = float(loaded[key])

    except FileNotFoundError:
        pass

    except (json.JSONDecodeError, ValueError, TypeError, OSError) as exc:
        print(f"Warning: could not load trip state: {exc}")

    return state


def save_state(state):
    os.makedirs(STATE_DIR, exist_ok=True)

    temp_file = STATE_FILE + ".tmp"

    data = {
        "trip_miles": state["trip_miles"],
        "raw_fuel_gallons": state["raw_fuel_gallons"],
        "engine_runtime_seconds": state["engine_runtime_seconds"],
        "fuel_calibration": state["fuel_calibration"],
        "last_saved": time.time(),
    }

    with open(temp_file, "w") as f:
        json.dump(data, f, indent=2)
        f.flush()
        os.fsync(f.fileno())

    os.replace(temp_file, STATE_FILE)


def reset_trip(state):
    state["trip_miles"] = 0.0
    state["raw_fuel_gallons"] = 0.0
    state["engine_runtime_seconds"] = 0.0


def format_runtime(seconds):
    total = max(0, int(seconds))

    hours = total // 3600
    minutes = (total % 3600) // 60
    secs = total % 60

    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def clean_response(text):
    text = text.replace("\r", " ").replace("\n", " ")
    text = text.replace(">", " ")
    return " ".join(text.split())


def send_command(ser, command, wait=0.15):
    ser.reset_input_buffer()
    ser.write((command + "\r").encode())
    ser.flush()

    if wait > 0:
        time.sleep(wait)

    # ELM327/vLinker terminates each completed response
    # with a ">" prompt. Read only until that prompt
    # instead of waiting for the serial timeout.
    response = ser.read_until(b">", 4096)

    return clean_response(
        response.decode(errors="replace")
    )


def compact_hex(response):
    return "".join(
        re.findall(r"[0-9A-Fa-f]", response)
    ).upper()


def set_header(ser, header):
    response = send_command(
        ser,
        f"ATSH{header}",
        0.10,
    )

    if "OK" not in response:
        raise RuntimeError(
            f"Failed setting header {header}: {response}"
        )


def decode_generic_u8(response, pid):
    data = compact_hex(response)

    match = re.search(
        rf"41{pid}([0-9A-F]{{2}})",
        data,
    )

    if not match:
        return None

    return int(match.group(1), 16)


def decode_rpm(response):
    data = compact_hex(response)

    match = re.search(
        r"410C([0-9A-F]{4})",
        data,
    )

    if not match:
        return None

    return int(match.group(1), 16) / 4.0


def decode_speed(response):
    raw = decode_generic_u8(response, "0D")

    if raw is None:
        return None

    return raw * 0.621371


def decode_map(response):
    raw = decode_generic_u8(response, "0B")

    if raw is None:
        return None

    return float(raw)


def decode_voltage(response):
    match = re.search(
        r"([0-9]+(?:\.[0-9]+)?)V",
        response,
    )

    if not match:
        return None

    return float(match.group(1))


def enhanced_payload(response, pid):
    data = compact_hex(response)

    match = re.search(
        rf"62{pid}([0-9A-F]+)",
        data,
    )

    if not match:
        return None

    return match.group(1)


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

    celsius = (raw / 100.0) - 40.0

    return (
        celsius * 9.0 / 5.0
    ) + 32.0


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


def calculate_raw_fuel_rate(mfdes_mg, rpm):
    if (
        mfdes_mg is None
        or rpm is None
        or rpm <= 0
    ):
        return 0.0

    # 7.3L Power Stroke:
    #
    # 8-cylinder four-stroke engine.
    # Across the entire engine there are
    # 4 injection events per crank revolution.
    mg_per_min = (
        mfdes_mg
        * rpm
        * 4.0
    )

    g_per_hour = (
        mg_per_min
        / 1000.0
    ) * 60.0

    liters_per_hour = (
        g_per_hour
        / DIESEL_DENSITY_G_PER_L
    )

    gallons_per_hour = (
        liters_per_hour
        / LITERS_PER_GALLON
    )

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
        response = send_command(
            ser,
            command,
            wait,
        )

        print(
            f"{command}: {response}"
        )

    protocol = send_command(
        ser,
        "ATDP",
        0.3,
    )

    print(
        f"Protocol: {protocol}"
    )

    if "J1850 PWM" not in protocol:
        raise RuntimeError(
            f"Unexpected protocol: {protocol}"
        )


def fmt(value, spec, missing="---"):
    if value is None:
        return missing

    return format(value, spec)


def run():
    state = load_state()

    calibration = state["fuel_calibration"]

    print(
        "Loaded trip: "
        f"{state['trip_miles']:.2f} mi | "
        f"{state['raw_fuel_gallons'] * calibration:.3f} gal | "
        f"{format_runtime(state['engine_runtime_seconds'])} | "
        f"fuel calibration {calibration:.5f}"
    )

    last_sample_time = time.monotonic()
    last_save_time = time.monotonic()

    try:
        while True:
            try:
                print(
                    f"Opening {PORT}..."
                )

                with serial.Serial(
                    PORT,
                    BAUD,
                    timeout=1,
                ) as ser:

                    time.sleep(0.5)

                    initialize(ser)

                    last_sample_time = time.monotonic()

                    while True:
                        # Generic OBD-II
                        set_header(
                            ser,
                            GENERIC_HEADER,
                        )

                        rpm = decode_rpm(
                            send_command(
                                ser,
                                "010C",
                            )
                        )

                        speed = decode_speed(
                            send_command(
                                ser,
                                "010D",
                            )
                        )

                        map_kpa = decode_map(
                            send_command(
                                ser,
                                "010B",
                            )
                        )

                        # Ford enhanced PIDs
                        set_header(
                            ser,
                            FORD_PCM_HEADER,
                        )

                        icp = decode_icp(
                            send_command(
                                ser,
                                "221446",
                            )
                        )

                        ipr = decode_ipr(
                            send_command(
                                ser,
                                "221434",
                            )
                        )

                        eot = decode_eot_f(
                            send_command(
                                ser,
                                "221310",
                            )
                        )

                        tft = decode_tft_f(
                            send_command(
                                ser,
                                "221674",
                            )
                        )

                        mfdes = decode_mfdes(
                            send_command(
                                ser,
                                "221412",
                            )
                        )

                        fuelpw = decode_fuelpw(
                            send_command(
                                ser,
                                "221410",
                            )
                        )

                        voltage = decode_voltage(
                            send_command(
                                ser,
                                "ATRV",
                            )
                        )

                        now = time.monotonic()

                        elapsed_seconds = (
                            now
                            - last_sample_time
                        )

                        last_sample_time = now

                        # Prevent a reconnect or pause from
                        # adding a huge false interval.
                        if (
                            elapsed_seconds < 0
                            or elapsed_seconds > 10
                        ):
                            elapsed_seconds = 0.0

                        elapsed_hours = (
                            elapsed_seconds
                            / 3600.0
                        )

                        raw_gph = calculate_raw_fuel_rate(
                            mfdes,
                            rpm,
                        )

                        calibration = state[
                            "fuel_calibration"
                        ]

                        calibrated_gph = (
                            raw_gph
                            * calibration
                        )

                        # Distance accumulation.
                        if (
                            speed is not None
                            and speed >= 0
                        ):
                            state[
                                "trip_miles"
                            ] += (
                                speed
                                * elapsed_hours
                            )

                        # Fuel and engine-time accumulation only
                        # while the engine is actually running.
                        if (
                            rpm is not None
                            and rpm > 0
                        ):
                            state[
                                "raw_fuel_gallons"
                            ] += (
                                raw_gph
                                * elapsed_hours
                            )

                            state[
                                "engine_runtime_seconds"
                            ] += elapsed_seconds

                        calibrated_fuel_used = (
                            state[
                                "raw_fuel_gallons"
                            ]
                            * calibration
                        )

                        if (
                            speed is not None
                            and speed > 1.0
                            and calibrated_gph > 0
                        ):
                            instant_mpg = (
                                speed
                                / calibrated_gph
                            )
                        else:
                            instant_mpg = None

                        if (
                            calibrated_fuel_used
                            > 0.00001
                        ):
                            trip_mpg = (
                                state["trip_miles"]
                                / calibrated_fuel_used
                            )
                        else:
                            trip_mpg = None

                        runtime = format_runtime(
                            state[
                                "engine_runtime_seconds"
                            ]
                        )

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
                            f"GPH {fmt(calibrated_gph, '4.2f'):>4} | "
                            f"MPG {fmt(instant_mpg, '5.1f'):>5} | "
                            f"Trip {state['trip_miles']:6.2f} mi | "
                            f"Fuel {calibrated_fuel_used:5.3f} gal | "
                            f"Avg {fmt(trip_mpg, '5.1f'):>5} MPG | "
                            f"Run {runtime}"
                        )

                        if (
                            now
                            - last_save_time
                            >= SAVE_INTERVAL_SECONDS
                        ):
                            save_state(state)
                            last_save_time = now

                        time.sleep(0.2)

            except (
                SerialException,
                OSError,
                RuntimeError,
            ) as exc:

                save_state(state)

                print(
                    f"Telemetry connection error: {exc}"
                )

                print(
                    "Retrying in 3 seconds..."
                )

                time.sleep(3)

                last_sample_time = (
                    time.monotonic()
                )

    except KeyboardInterrupt:
        print("\nStopping...")

    finally:
        save_state(state)

        calibrated_fuel_used = (
            state["raw_fuel_gallons"]
            * state["fuel_calibration"]
        )

        if calibrated_fuel_used > 0:
            average_mpg = (
                state["trip_miles"]
                / calibrated_fuel_used
            )
        else:
            average_mpg = None

        print(
            "Trip saved: "
            f"{state['trip_miles']:.2f} mi | "
            f"{calibrated_fuel_used:.3f} gal | "
            f"Avg {fmt(average_mpg, '.1f')} MPG | "
            f"Runtime "
            f"{format_runtime(state['engine_runtime_seconds'])}"
        )


def main():
    parser = argparse.ArgumentParser(
        description="7.3 Power Stroke telemetry"
    )

    parser.add_argument(
        "--reset-trip",
        action="store_true",
        help="Reset trip miles, fuel and runtime",
    )

    parser.add_argument(
        "--set-calibration",
        type=float,
        metavar="FACTOR",
        help="Set fuel calibration multiplier",
    )

    parser.add_argument(
        "--show-trip",
        action="store_true",
        help="Show saved trip state and exit",
    )

    args = parser.parse_args()

    if (
        args.reset_trip
        or args.set_calibration is not None
        or args.show_trip
    ):
        state = load_state()

        if args.set_calibration is not None:
            if args.set_calibration <= 0:
                raise SystemExit(
                    "Calibration factor must be greater than zero."
                )

            state["fuel_calibration"] = (
                args.set_calibration
            )

            save_state(state)

            print(
                "Fuel calibration set to "
                f"{args.set_calibration:.5f}"
            )

        if args.reset_trip:
            reset_trip(state)
            save_state(state)

            print(
                "Trip miles, fuel, and runtime reset."
            )

        if args.show_trip:
            calibration = state[
                "fuel_calibration"
            ]

            fuel = (
                state[
                    "raw_fuel_gallons"
                ]
                * calibration
            )

            if fuel > 0:
                mpg = (
                    state["trip_miles"]
                    / fuel
                )
            else:
                mpg = None

            print(
                f"Trip miles:       "
                f"{state['trip_miles']:.2f} mi"
            )

            print(
                f"Fuel used:        "
                f"{fuel:.3f} gal"
            )

            print(
                f"Average MPG:      "
                f"{fmt(mpg, '.1f')}"
            )

            print(
                f"Engine runtime:   "
                f"{format_runtime(state['engine_runtime_seconds'])}"
            )

            print(
                f"Fuel calibration: "
                f"{calibration:.5f}"
            )

        return

    run()


if __name__ == "__main__":
    main()
