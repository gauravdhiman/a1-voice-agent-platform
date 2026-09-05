#!/bin/sh

set -eu

# Keep dependency installation out of the normal restart path. The anonymous
# node_modules volume survives container restarts, while this marker makes a
# package-lock change trigger one deliberate sync instead of an install on
# every boot.
package_hash="$(sha256sum /app/package.json /app/package-lock.json | sha256sum | awk '{print $1}')"
installed_hash="$(cat /app/node_modules/.package-lock.sha256 2>/dev/null || true)"

if [ ! -x /app/node_modules/.bin/next ] || [ "$package_hash" != "$installed_hash" ]; then
  npm install
  printf '%s\n' "$package_hash" > /app/node_modules/.package-lock.sha256
fi

# Preserve .next so Next.js can reuse its incremental cache after a restart.
exec npm run dev
