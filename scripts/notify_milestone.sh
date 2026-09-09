#!/usr/bin/env bash
set -euo pipefail
TITLE=${1:?title}; BODY=${2:?body}
printf '%s\n\n%s\n' "$TITLE" "$BODY" | moneypenny --table
