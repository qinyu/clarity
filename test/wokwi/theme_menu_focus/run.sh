#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$script_dir/../../architecture/check_config_menu.py"
exec python3 "$script_dir/runner.py" "$@"
