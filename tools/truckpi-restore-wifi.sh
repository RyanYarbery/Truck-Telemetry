#!/usr/bin/env bash
# Restores the truck Pi's Wi-Fi profile on its SD card, using the credentials
# already stored in the card's own boot/network-config. Never prints the password.
#
# Run from a laptop with the Pi's SD card mounted:
#   sudo tools/truckpi-restore-wifi.sh
# Optional overrides (environment):
#   ROOTFS / BOOTFS  mount points of the card's partitions (default: /run/media/$SUDO_USER/...)
#   PI_HOSTNAME      hostname the card must have before anything is changed (default: truckpi)
#   WIFI_SSID        network name, if it can't be read from boot/network-config
set -euo pipefail

MEDIA="/run/media/${SUDO_USER:-$USER}"
R="${ROOTFS:-$MEDIA/rootfs}"
B="${BOOTFS:-$MEDIA/bootfs}"
PI_HOSTNAME="${PI_HOSTNAME:-truckpi}"

[ "$(id -u)" = 0 ] || { echo "run with sudo"; exit 1; }
[ "$(cat "$R/etc/hostname")" = "$PI_HOSTNAME" ] || { echo "card is not $PI_HOSTNAME, stopping"; exit 1; }

echo "=== read-only: evidence the card needs root to read"
ls -la "$R/var/spool/cron/crontabs" 2>/dev/null
for f in "$R"/var/spool/cron/crontabs/*; do [ -f "$f" ] && { echo "## $f"; grep -v '^#' "$f"; }; done
ls -la --time-style=long-iso "$R/var/lib/NetworkManager/"
grep -iE 'netplan|network-config|wifis|apply_network' "$R/var/log/cloud-init.log" \
  | grep -viE 'password|psk' | tail -12 | cut -c1-170

echo "=== restoring Wi-Fi"
PSK=$(sed -nE 's/^\s*password:\s*"?([^"]*)"?\s*$/\1/p' "$B/network-config" | head -1)
[ -n "$PSK" ] || { echo "no password found in network-config, nothing changed"; exit 1; }
PSK=${PSK//\\/\\\\}
PSK=${PSK//;/\\;}

# The SSID is the access-points key on the line after "access-points:" in network-config.
SSID="${WIFI_SSID:-$(sed -nE '/access-points:/{n;s/^\s*"?([^"]*[^":])"?:\s*$/\1/p}' "$B/network-config" | head -1)}"
[ -n "$SSID" ] || { echo "no SSID found in network-config; set WIFI_SSID, nothing changed"; exit 1; }
CONN="$R/etc/NetworkManager/system-connections/${SSID// /-}.nmconnection"

umask 077
cat > "$CONN" <<EOF
[connection]
id=$SSID
uuid=$(cat /proc/sys/kernel/random/uuid)
type=wifi
interface-name=wlan0
autoconnect=true

[wifi]
mode=infrastructure
ssid=$SSID

[wifi-security]
key-mgmt=wpa-psk
psk=$PSK

[ipv4]
method=auto

[ipv6]
method=auto
EOF
chown root:root "$CONN"
chmod 600 "$CONN"

# Only ever move a broken NetworkManager netplan profile aside if it really is empty.
for EMPTY in "$R"/etc/netplan/90-NM-*.yaml; do
  if [ -f "$EMPTY" ] && [ ! -s "$EMPTY" ]; then
    mv "$EMPTY" "$EMPTY.empty-bak"
    echo "moved the empty netplan profile $(basename "$EMPTY") aside"
  fi
done

sync
ls -la --time-style=long-iso "$CONN" "$R/etc/netplan/"
echo "done. Eject the card, put it back in the Pi, and power it on."
