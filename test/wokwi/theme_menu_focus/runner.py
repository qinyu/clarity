#!/usr/bin/env python3
"""Prepare and verify the Clarity theme-menu simulation probe."""

import argparse
import hashlib
import importlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

SUITE = Path(__file__).resolve().parent
ACCEPTANCE_CASES = tuple(f"A{number}" for number in range(1, 9))
PROBE_FRAMES = ("probe-display.png", "probe-lights-on.png", "probe-lights-off.png")
PROBE_CAPTURE_FILES = ("serial.log", *PROBE_FRAMES)
FLASH_SIZE = 0x400000
NVS_OFFSET = 0x9000
NVS_SIZE = 0x3000
APP_OFFSET = 0x10000


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare_simulation(build, destination, *, diagram=None, nvs_image=None):
    """Use the built application bytes and the repository's actual partition table."""
    info = json.loads(subprocess.check_output(["pio", "system", "info", "--json-output"]))
    packages = Path(info["core_dir"]["value"]) / "packages"
    esptool = packages / "tool-esptoolpy" / "esptool.py"
    framework = packages / "framework-arduinoespressif32"
    boot_app = framework / "tools" / "partitions" / "boot_app0.bin"
    artifacts = [build / name for name in ("bootloader.bin", "partitions.bin", "firmware.bin", "firmware.elf")]
    bootloader, partitions, application, elf = artifacts
    for artifact in [*artifacts, esptool, boot_app]:
        if not artifact.is_file():
            raise ValueError(f"Required input is missing: {artifact}")

    image = destination / "firmware.full.bin"
    command = [
        info["python_exe"]["value"], str(esptool), "--chip", "esp32",
        "merge_bin", "--fill-flash-size", "4MB", "-o", str(image),
        "0x1000", str(bootloader), "0x8000", str(partitions),
    ]
    nvs_bytes = b"\xff" * NVS_SIZE
    if nvs_image is not None:
        nvs_bytes = nvs_image.read_bytes()
        if len(nvs_bytes) != NVS_SIZE:
            raise ValueError("NVS fixture must fill exactly the 0x3000-byte partition")
        command.extend([hex(NVS_OFFSET), str(nvs_image)])
        artifacts.append(nvs_image)
    command.extend(["0xe000", str(boot_app), hex(APP_OFFSET), str(application)])
    subprocess.run(command, check=True)

    image_bytes = image.read_bytes()
    app_bytes = application.read_bytes()
    if len(image_bytes) != FLASH_SIZE or image_bytes[APP_OFFSET:APP_OFFSET + len(app_bytes)] != app_bytes:
        raise ValueError("Merged image does not contain the exact application at 0x10000")
    if image_bytes[NVS_OFFSET:NVS_OFFSET + NVS_SIZE] != nvs_bytes:
        raise ValueError("Merged image does not contain the expected NVS bytes at 0x9000")

    circuit = destination / "diagram.json"
    shutil.copyfile(diagram or SUITE.parent / "diagram_automated.json", circuit)
    config = destination / "wokwi.toml"
    config.write_text(
        '[wokwi]\nversion = 1\nfirmware = "firmware.full.bin"\n'
        f"elf = {json.dumps(str(elf))}\n"
    )
    manifest = {str(path): digest(path) for path in [*artifacts, boot_app, image, circuit, config]}
    (destination / "sha256.json").write_text(json.dumps(manifest, indent=2) + "\n")


def check_probe(destination):
    manifest = json.loads((destination / "sha256.json").read_text())
    receipt = json.loads((destination / "capture.json").read_text())
    image = destination / "firmware.full.bin"
    if manifest.get(str(image)) != digest(image) or receipt.get("loaded_image_sha256") != digest(image):
        raise ValueError("Capture does not match the prepared flash image")
    for name in PROBE_CAPTURE_FILES:
        if receipt.get("files", {}).get(name) != digest(destination / name):
            raise ValueError(f"Capture file does not match its run receipt: {name}")

    serial_path = destination / "serial.log"
    if not serial_path.is_file():
        raise ValueError(f"Missing serial capture: {serial_path}")
    serial = serial_path.read_text(errors="replace")

    actions = list(re.finditer(r"\[T\] ThemeMenu action (\d+) (start|end) (\w+)", serial))
    expected_presses = [
        "LONG_PRESS", "SHORT_PRESS", "LONG_PRESS", "LONG_PRESS", "LONG_PRESS",
        "SHORT_PRESS", "SHORT_PRESS", "LONG_PRESS", *(["SHORT_PRESS"] * 6), "LONG_PRESS",
    ]
    expected_actions = [
        (str(number), phase, press)
        for number, press in enumerate(expected_presses, 1)
        for phase in ("start", "end")
    ]
    if [event.groups() for event in actions] != expected_actions:
        raise ValueError("Serial trace does not contain the ordered press and completion checkpoints")
    confirm_start, confirm_end = actions[8:10]
    confirmation = serial[confirm_start.end():confirm_end.start()]
    write = re.search(r"\[T\] ThemeMenu write (\d+) attempt style_manager\.theme=Day\b", confirmation)
    if write is None:
        raise ValueError("The confirm press did not attempt to save Day")
    positive = re.search(
        rf"\[T\] ThemeMenu write {write.group(1)} success style_manager\.theme=Day\b"
        r"[\s\S]*?\[T\] ThemeMenu menu palette \d+ Day\b",
        confirmation[write.end():],
    )
    if positive is None:
        raise ValueError("The confirm press did not save Day and refresh the menu palette")

    after_exit = serial[actions[-1].end():]
    lights = re.search(
        r"LightsOnActivate\(\) - Setting NIGHT theme"
        r"[\s\S]*?\[T\] ThemeMenu shared palette \d+ Night\b"
        r"[\s\S]*?LightsOffActivate\(\) - Setting DAY theme"
        r"[\s\S]*?\[T\] ThemeMenu shared palette \d+ Day\b",
        after_exit,
    )
    if lights is None:
        raise ValueError("The serial trace is missing ordered Night/Day light transitions")
    for name in PROBE_FRAMES:
        frame = destination / name
        data = frame.read_bytes()
        if (
            len(data) < 45
            or not data.startswith(b"\x89PNG\r\n\x1a\n\x00\x00\x00\x0dIHDR")
            or int.from_bytes(data[16:20], "big") == 0
            or int.from_bytes(data[20:24], "big") == 0
            or not data.endswith(b"\x00\x00\x00\x00IEND\xaeB\x60\x82")
        ):
            raise ValueError(f"Missing or invalid LCD capture: {frame}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=("probe", *ACCEPTANCE_CASES, "all"), default="probe")
    parser.add_argument("--build-dir", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--reference-build-dir", type=Path)
    parser.add_argument("--nvs-gen", type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--prepare-only", action="store_true", help="stage a project for a browser simulator")
    mode.add_argument("--check-capture", action="store_true", help="check serial.log and probe frames in --out")
    args = parser.parse_args()
    out = args.out.resolve()
    if args.case != "probe":
        if args.prepare_only or args.check_capture:
            parser.error("The standalone capture modes currently apply to --case probe")
        if args.build_dir is None:
            parser.error("--build-dir is required for acceptance cases")
        if args.case in ("A4", "all") and args.reference_build_dir is None:
            parser.error("A4 requires --reference-build-dir")
        if args.case in ("A8", "all") and args.nvs_gen is None:
            parser.error("A8 requires --nvs-gen")
        cases = ACCEPTANCE_CASES if args.case == "all" else (args.case,)
        for case in cases:
            if not (SUITE / f"{case}_check.py").is_file():
                raise ValueError(f"Acceptance case {case} has not been implemented")
        # Each case owns its fixtures and assertions. Adding a case needs no shared runner edit.
        for case in cases:
            importlib.import_module(f"{case}_check").run(args)
        return
    if args.check_capture:
        check_probe(out)
        print(f"Probe trace and PNG files verified in {out}. Review the three LCD frames.")
        return
    if args.build_dir is None:
        parser.error("--build-dir is required when preparing or running the simulation")
    out.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix="probe-", dir=out))
    print(f"Probe artifacts: {run}", flush=True)
    prepare_simulation(args.build_dir.resolve(), run)
    shutil.copyfile(SUITE / "probe.yaml", run / "probe.yaml")
    if args.prepare_only:
        print("Simulation project prepared. Firmware behavior is still unverified.")
        return
    command = [
        "wokwi-cli", ".", "--scenario", "probe.yaml",
        "--serial-log-file", "serial.log", "--timeout", "120000",
    ]
    image_sha = digest(run / "firmware.full.bin")
    subprocess.run(command, cwd=run, check=True, timeout=180)
    receipt = {
        "loaded_image_sha256": image_sha,
        "files": {name: digest(run / name) for name in PROBE_CAPTURE_FILES},
    }
    (run / "capture.json").write_text(json.dumps(receipt, indent=2) + "\n")
    check_probe(run)
    print("Probe trace and PNG files verified. Review the three LCD frames.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"Theme menu probe failed: {error}", file=sys.stderr)
        sys.exit(1)
