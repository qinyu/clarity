"""Prepare an isolated PlatformIO config for a Clarity oil-temperature build."""
import argparse
from pathlib import Path
import re


def prepare_config(source, variant):
    config, replacements = re.subn(r"(?m)^(\s*lvgl/lvgl\s*@\s*)\^9\.2\.0$", r"\g<1>9.2.2", source)
    if replacements != 1:
        raise ValueError("Expected one LVGL 9.2.0 dependency to pin for the rehearsal.")

    section = re.search(r"(?m)^\[env:test-wokwi\]\n[^\[]*", config)
    if section is None:
        raise ValueError("The test-wokwi environment is missing.")
    if variant == "acceptance":
        enable = "\t-D WOKWI_EMULATOR\n"
        original = section.group()
        if original.count(enable) != 1:
            raise ValueError("Expected one WOKWI_EMULATOR flag in test-wokwi.")
        updated = original.replace(enable, enable + "\t-D OIL_TEMP_ACCEPTANCE\n")
        config = config[:section.start()] + updated + config[section.end():]
    return config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("variant", choices=("regular", "acceptance"))
    parser.add_argument("output_directory", type=Path)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[2]
    config = prepare_config((repo / "platformio.ini").read_text(), args.variant)
    args.output_directory.mkdir(parents=True, exist_ok=True)
    output = args.output_directory / "platformio.ini"
    if output.resolve() == (repo / "platformio.ini").resolve():
        parser.error("Choose a separate build directory.")
    output.write_text(config)


if __name__ == "__main__":
    main()
