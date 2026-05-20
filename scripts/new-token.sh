#!/usr/bin/env bash
# Generate a strong random `LOOVIE_API_TOKEN`.
#
# The token is a URL-safe base64 representation of 32 random bytes
# (256 bits of entropy), which is more than enough for a static bearer
# token. The output goes to stdout so you can pipe it into a clipboard
# tool or assign it to an environment variable in one line:
#
#   TOKEN=$(bash scripts/new-token.sh)
#   export LOOVIE_API_TOKEN="$TOKEN"

set -Eeuo pipefail

if ! command -v python3 >/dev/null 2>&1; then
  echo "scripts/new-token.sh: python3 not found on PATH." >&2
  exit 1
fi

python3 -c 'import secrets; print(secrets.token_urlsafe(32))'
