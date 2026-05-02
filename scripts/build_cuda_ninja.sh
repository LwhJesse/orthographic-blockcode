#!/usr/bin/env bash
set -euo pipefail

if [[ ! -f config.ninja ]]; then
  scripts/configure_ninja.sh
fi

ninja
