#!/usr/bin/env python3
"""Power the Pi off after the truck's key has been OFF for a while.

Ignition sense is on BCM GPIO17 (physical pin 11): LOW = key ON, HIGH = key OFF.
The level is read with `pinctrl` because it does not touch the pin's pull setting.
GPIO17's default pull-down means a loose sense wire reads as key ON, so the Pi
stays up rather than shutting down during a drive.

To keep the Pi up with the key off, for example to work on it: systemctl stop truck-ignition
"""

import subprocess
import time

GPIO = "17"
OFF_DELAY_S = 45
POLL_S = 1


def key_is_off():
    """Return True for key OFF. A failed read counts as key ON, so it never shuts down."""
    try:
        result = subprocess.run(
            ["pinctrl", "lev", GPIO],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
    except (OSError, subprocess.SubprocessError) as error:
        print(f"GPIO{GPIO} read failed, treating as key ON: {error}", flush=True)
        return False
    return result.stdout.strip() == "1"


def main():
    print(f"Watching GPIO{GPIO}, power off after {OFF_DELAY_S} s of key OFF", flush=True)
    off_since = None
    while True:
        if key_is_off():
            now = time.monotonic()
            if off_since is None:
                off_since = now
                print(f"Key OFF, powering off in {OFF_DELAY_S} s unless it comes back", flush=True)
            elif now - off_since >= OFF_DELAY_S:
                print("Key still OFF, powering off", flush=True)
                subprocess.run(["systemctl", "poweroff"], check=False)
                return
        elif off_since is not None:
            off_since = None
            print("Key ON again, shutdown cancelled", flush=True)
        time.sleep(POLL_S)


if __name__ == "__main__":
    main()
