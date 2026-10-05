#!/bin/sh
# Fix volume ownership, then run the app unprivileged.
#
# Docker creates named volumes owned by root, and a volume that already exists
# keeps whatever ownership it had. Without this an upgrade from a root-running
# image leaves the queue database unwritable ("attempt to write a readonly
# database") and the only fix would be deleting the volume, which throws away
# downloaded videos and queue history.
#
# Runs as root for the chown only; the application process is uid 10001.
set -e

APP_UID=10001
STATE_DIRS="/tmp/tiktok_queue /app/data"

if [ "$(id -u)" = "0" ]; then
    for dir in $STATE_DIRS; do
        [ -d "$dir" ] || mkdir -p "$dir"
        owner=$(stat -c '%u' "$dir")
        if [ "$owner" != "$APP_UID" ]; then
            chown -R savetok:savetok "$dir"
        fi
    done
    exec setpriv --reuid=savetok --regid=savetok --init-groups "$@"
fi

exec "$@"
