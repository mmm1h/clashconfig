#!/bin/sh
set -eu

# Zashboard updater for OpenClash (OpenWrt-friendly).
# Usage:
#   sh update_zashboard.sh            # run update now
#   sh update_zashboard.sh --install-cron

# ===================== Config =====================
# Zashboard release asset (latest dist.zip)
DOWNLOAD_URL="https://proxy.hmhi.ac.cn/https://github.com/Zephyruso/zashboard/releases/latest/download/dist.zip"
# Download tool preference: auto | uclient-fetch | wget | curl
DOWNLOAD_TOOL="wget"

# OpenClash UI directory and name
DASHBOARD_DIR="/usr/share/openclash/ui"
DASHBOARD_NAME="zashboard"

# Cron settings (OpenWrt uses /etc/crontabs/root)
CRON_SCHEDULE="0 5 * * *"
CRON_FILE="/etc/crontabs/root"
# Cron output redirection (set empty for normal output)
CRON_REDIRECT=">/dev/null 2>&1"
# Log control: 1 = silent, 0 = verbose
QUIET=1
# ==================================================

log() {
    if [ "${QUIET:-1}" -eq 0 ]; then
        printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
    fi
}

die() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

script_path() {
    cd "$(dirname "$0")" && printf '%s/%s\n' "$(pwd)" "$(basename "$0")"
}

install_cron() {
    local path
    path="$(script_path)"

    [ -f "$CRON_FILE" ] || touch "$CRON_FILE"

    if grep -Fq "$path" "$CRON_FILE"; then
        log "Cron entry already exists: $path"
        return 0
    fi

    if [ -n "$CRON_REDIRECT" ]; then
        printf '%s %s %s\n' "$CRON_SCHEDULE" "$path" "$CRON_REDIRECT" >> "$CRON_FILE"
    else
        printf '%s %s\n' "$CRON_SCHEDULE" "$path" >> "$CRON_FILE"
    fi
    log "Cron entry installed: $CRON_SCHEDULE $path"
    log "Ensure cron is running (e.g. /etc/init.d/cron enable && /etc/init.d/cron restart)."
}

if [ "${1:-}" = "--install-cron" ]; then
    install_cron
    exit 0
fi

case "$DOWNLOAD_TOOL" in
    auto)
        if command -v wget >/dev/null 2>&1; then
            DOWNLOAD_CMD="wget -q -O"
        elif command -v uclient-fetch >/dev/null 2>&1; then
            DOWNLOAD_CMD="uclient-fetch -L -O"
        elif command -v curl >/dev/null 2>&1; then
            DOWNLOAD_CMD="curl -fsSL -o"
        else
            die "No download tool found (uclient-fetch/wget/curl)."
        fi
        ;;
    wget)
        command -v wget >/dev/null 2>&1 || die "wget not found."
        DOWNLOAD_CMD="wget -q -O"
        ;;
    uclient-fetch)
        command -v uclient-fetch >/dev/null 2>&1 || die "uclient-fetch not found."
        DOWNLOAD_CMD="uclient-fetch -L -O"
        ;;
    curl)
        command -v curl >/dev/null 2>&1 || die "curl not found."
        DOWNLOAD_CMD="curl -fsSL -o"
        ;;
    *)
        die "Unknown DOWNLOAD_TOOL: $DOWNLOAD_TOOL"
        ;;
esac

if command -v unzip >/dev/null 2>&1; then
    UNZIP_CMD="unzip -q"
elif command -v busybox >/dev/null 2>&1 && busybox unzip >/dev/null 2>&1; then
    UNZIP_CMD="busybox unzip -q"
else
    die "unzip not found; install unzip or busybox unzip."
fi

TMP_DIR="$(mktemp -d /tmp/zashboard.XXXXXX)"
ZIP_FILE="$TMP_DIR/zashboard.zip"
EXTRACT_DIR="$TMP_DIR/extract"

cleanup() {
    rm -rf "$TMP_DIR"
}
trap cleanup EXIT

mkdir -p "$EXTRACT_DIR"

log "Downloading Zashboard: $DOWNLOAD_URL"
$DOWNLOAD_CMD "$ZIP_FILE" "$DOWNLOAD_URL" || die "Download failed."

if [ ! -s "$ZIP_FILE" ]; then
    die "Downloaded file is empty."
fi

log "Extracting package"
$UNZIP_CMD "$ZIP_FILE" -d "$EXTRACT_DIR" || die "Unzip failed."

if [ -d "$EXTRACT_DIR/dist" ]; then
    SRC_DIR="$EXTRACT_DIR/dist"
else
    SRC_DIR="$(find "$EXTRACT_DIR" -mindepth 1 -maxdepth 1 -type d | head -n 1 || true)"
    [ -n "$SRC_DIR" ] || SRC_DIR="$EXTRACT_DIR"
fi

TARGET_DIR="$DASHBOARD_DIR/$DASHBOARD_NAME"
STAGE_DIR="$DASHBOARD_DIR/.${DASHBOARD_NAME}.new"
BACKUP_DIR="$DASHBOARD_DIR/.${DASHBOARD_NAME}.bak"

if [ ! -d "$DASHBOARD_DIR" ]; then
    die "Dashboard base dir not found: $DASHBOARD_DIR"
fi
rm -rf "$STAGE_DIR" "$BACKUP_DIR"
mkdir -p "$STAGE_DIR"

log "Staging files to $STAGE_DIR"
cp -R "$SRC_DIR"/. "$STAGE_DIR"/ || die "Copy failed."

if [ -d "$TARGET_DIR" ]; then
    mv "$TARGET_DIR" "$BACKUP_DIR" || die "Backup failed."
fi

mv "$STAGE_DIR" "$TARGET_DIR" || {
    if [ -d "$BACKUP_DIR" ]; then
        mv "$BACKUP_DIR" "$TARGET_DIR" || true
    fi
    die "Deploy failed."
}

rm -rf "$BACKUP_DIR"
log "Zashboard update complete: $TARGET_DIR"

exit 0
