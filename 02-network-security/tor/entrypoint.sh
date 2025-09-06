#!/usr/bin/env sh
# Path: 02-network-security/tor/entrypoint.sh
# Extended entrypoint for lucid_tor container
# Ensures Tor starts and always provides an onion address.

set -eu

log() { printf '[tor-entrypoint] %s\n' "$*"; }

TOR_CONFIG="/etc/tor/torrc"
ONION_FILE="/var/lib/tor/hidden_service/hostname"
COOKIE_FILE="/var/lib/tor/control_auth_cookie"

# Ensure config exists
if [ ! -f "$TOR_CONFIG" ]; then
    log "Missing torrc at $TOR_CONFIG"
    exit 1
fi

# Ensure data directory exists with correct permissions
if [ ! -d /var/lib/tor ]; then
    log "Creating /var/lib/tor..."
    mkdir -p /var/lib/tor
    chown tor:tor /var/lib/tor
    chmod 700 /var/lib/tor
fi

# Start Tor in background
log "Starting Tor..."
tor -f "$TOR_CONFIG" &
TOR_PID=$!

# Wait for Tor to bootstrap
log "Waiting for Tor bootstrap..."
BOOTSTRAP_OK=0
for i in $(seq 1 30); do
    if grep -q "Bootstrapped 100%" <<EOF
$(tail -n 100 /proc/$TOR_PID/fd/1 2>/dev/null || true)
EOF
    then
        BOOTSTRAP_OK=1
        break
    fi
    sleep 2
done

if [ "$BOOTSTRAP_OK" -eq 1 ]; then
    log "Tor bootstrapped successfully."
else
    log "Tor did not bootstrap within timeout."
fi

# Persistent onion service
if [ -f "$ONION_FILE" ]; then
    ONION_ADDR=$(tr -d '\r\n' < "$ONION_FILE")
    log "Persistent onion service available at: $ONION_ADDR"
else
    log "No persistent onion service found, creating ephemeral onion..."

    if [ ! -f "$COOKIE_FILE" ]; then
        log "Tor control cookie not found at $COOKIE_FILE"
        wait $TOR_PID
        exit 1
    fi

    COOKIE=$(xxd -p -c 256 "$COOKIE_FILE" | tr -d '\n')
    CMD="ADD_ONION NEW:BEST Flags=DiscardPK Port=80 127.0.0.1:8080"

    REPLY=$(echo -e "AUTHENTICATE $COOKIE\n$CMD\nQUIT" | nc 127.0.0.1 9051 || true)

    SERVICE_ID=$(echo "$REPLY" | grep "250-ServiceID" | awk '{print $2}' || true)

    if [ -n "$SERVICE_ID" ]; then
        ONION_ADDR="${SERVICE_ID}.onion"
        log "Ephemeral onion service created at: $ONION_ADDR"
        echo "$ONION_ADDR" > "$ONION_FILE"
    else
        log "Failed to create ephemeral onion. ControlPort reply:"
        echo "$REPLY"
    fi
fi

# Keep Tor in foreground
wait $TOR_PID
