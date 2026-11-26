#!/usr/bin/env python3
"""Build both firmware profiles and check the linked ThemeMenu probe."""

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from check_config_menu import PROFILES, build_fingerprints

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ("bootloader.bin", "firmware.bin", "firmware.elf", "partitions.bin")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="new directory for builds and evidence")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)

    metadata = output / "compiledb_path.py"
    metadata.write_text(
        'Import("env")\nimport os\n'
        'env.Replace(COMPILATIONDB_PATH=os.path.join(os.environ["CLARITY_PROBE_EVIDENCE"], '
        'env.subst("$PIOENV") + "-compile_commands.json"))\n'
    )
    config = (ROOT / "platformio.ini").read_text()
    old_lvgl = "lvgl/lvgl @ ^9.2.0"
    if config.count(old_lvgl) != 1:
        raise ValueError("PlatformIO LVGL dependency changed. Check the pinned build preflight in AGENTS.md.")
    config = config.replace(old_lvgl, "lvgl/lvgl @ 9.2.2")
    project_config = output / "platformio.ini"
    project_config.write_text(f"[env]\nextra_scripts = pre:{metadata}\n\n{config}")

    environment = os.environ.copy()
    environment.setdefault("PLATFORMIO_LIBDEPS_DIR", str(output / "libdeps"))
    environment["CLARITY_PROBE_EVIDENCE"] = str(output)
    for profile in PROFILES:
        build_dir = output / "work" / profile
        environment["PLATFORMIO_BUILD_DIR"] = str(build_dir)
        command = ["pio", "run", "-d", str(ROOT), "-c", str(project_config), "-e", profile, "-j", "2"]
        print(f"Building {profile} into {build_dir}", flush=True)
        subprocess.run(command, env=environment, check=True)
        subprocess.run([*command, "-t", "compiledb"], env=environment, check=True)
        target = output / "build" / profile
        target.mkdir(parents=True)
        for name in ARTIFACTS:
            shutil.copyfile(build_dir / profile / name, target / name)

    (output / "probe-build-sha256.json").write_text(json.dumps(build_fingerprints(output), indent=2) + "\n")
    subprocess.run(
        [sys.executable, str(Path(__file__).with_name("check_config_menu.py")), "--build-evidence", str(output)],
        check=True,
    )
    print(f"Paired profile evidence: {output}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"Probe profile build failed: {error}", file=sys.stderr)
        sys.exit(1)
