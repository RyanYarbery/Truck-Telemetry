#!/usr/bin/env bash
# Restores the truck Pi's Wi-Fi profile on its SD card, using the credentials
# already stored in the card's own boot/network-config. Never prints the password.
set -euo pipefail

R=/run/media/ryan/rootfs
B=/run/media/ryan/bootfs
CONN="$R/etc/NetworkManager/system-connections/THE-WIFI.nmconnection"
EMPTY="$R/etc/netplan/90-NM-75a1216a-9d1a-30cd-8aca-ace5526ec021.yaml"

[ "$(id -u)" = 0 ] || { echo "run with sudo"; exit 1; }
[ "$(cat "$R/etc/hostname")" = truckpi ] || { echo "card is not truckpi, stopping"; exit 1; }

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

umask 077
cat > "$CONN" <<EOF
[connection]
id=THE WIFI
uuid=$(cat /proc/sys/kernel/random/uuid)
type=wifi
interface-name=wlan0
autoconnect=true

[wifi]
mode=infrastructure
ssid=THE WIFI

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

# Only ever move the broken profile aside if it really is empty.
if [ -f "$EMPTY" ] && [ ! -s "$EMPTY" ]; then
  mv "$EMPTY" "$EMPTY.empty-bak"
  echo "moved the empty netplan profile aside"
fi

sync
ls -la --time-style=long-iso "$CONN" "$R/etc/netplan/"
echo "done. Eject the card, put it back in the Pi, and power it on."
