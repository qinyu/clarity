#!/usr/bin/env python3
"""Check the Clarity configuration menu's direct dependencies and probe isolation."""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shlex
import sys

ROOT = Path(__file__).resolve().parents[2]
PANEL = ("include/panels/config_panel.h", "src/panels/config_panel.cpp")
VIEW = ("include/components/config_component.h", "src/components/config_component.cpp")
PROBE_SOURCES = (
    "src/handlers/action_handler.cpp",
    "src/providers/storage_provider.cpp",
    "src/components/config_component.cpp",
    "src/managers/style_manager.cpp",
    "src/main.cpp",
)
PROBE_MACROS = {"WOKWI_EMULATOR", "TEST_LOGS"}
PROFILES = ("test-wokwi", "release")
PROBE_MARKERS = (
    b"ThemeMenu action ",
    b"ThemeMenu write ",
    b"ThemeMenu menu palette ",
    b"ThemeMenu shared palette ",
    b"ThemeMenu restart requested",
)
CPP_NOISE = re.compile(
    r'(?P<raw>(?:u8|u|U|L)?R"(?P<delimiter>[^\s()\\]{0,16})\(.*?\)(?P=delimiter)")'
    r"|(?P<comment>//[^\n]*|/\*.*?(?:\*/|$))"
    r'''|"(?:(?:\\.)|[^"\\\n])*"'''
    r"|(?<!\w)(?:u8|u|U|L)?'(?:(?:\\.)|[^'\\\n])*'",
    re.DOTALL,
)
INCLUDE = re.compile(r"^[ \t]*#[ \t]*include\b", re.MULTILINE)
HEADER = re.compile(r'[ \t]*(?:"([^"\n]+)"|<([^>\n]+)>)')
VIEW_SYMBOL = re.compile(r"\b(?:IConfigurationManager|STYLE_MANAGER_THEME)\b")
PERSISTENCE_ENTRY = "Use IConfigurationManager::GetConfigSection() and UpdateConfig() in ConfigPanel."
VIEW_ENTRY = "Use ConfigPanel for configuration and pass the focus to ConfigComponent::SetCurrentIndex()."


def without_line_splices(source):
    parts = []
    offsets = []
    start = 0
    for match in re.finditer(r"\\\n", source):
        parts.append(source[start:match.start()])
        offsets.extend(range(start, match.start()))
        start = match.end()
    parts.append(source[start:])
    offsets.extend(range(start, len(source)))
    return "".join(parts), offsets


def source_errors(root):
    for relative in (*PANEL, *VIEW):
        path = root / relative
        if not path.is_file():
            yield f"{relative}: check input is missing"
            continue

        source = path.read_text()
        logical, offsets = without_line_splices(source)
        directives = list(logical)
        code = list(logical)
        for item in CPP_NOISE.finditer(logical):
            blank = ["\n" if char == "\n" else " " for char in item.group()]
            code[item.start():item.end()] = blank
            if item.lastgroup == "comment":
                directives[item.start():item.end()] = blank
        code = "".join(code)
        directives = "".join(directives)

        def location(index):
            position = offsets[index]
            line = source.count("\n", 0, position) + 1
            column = position - source.rfind("\n", 0, position)
            return f"{relative}:{line}:{column}"

        for directive in INCLUDE.finditer(code):
            match = HEADER.match(directives, directive.end())
            if match is None:
                continue
            header = match.group(1) or match.group(2)
            stem = PurePosixPath(header).stem.lower()
            dependency = stem.replace("_", "")
            if dependency in {"storageprovider", "istorageprovider", "preferences"} or re.match(
                r"^(?:esp_)?nvs(?:_|$)", stem
            ):
                yield f"{location(directive.start())}: [config-persistence] direct include {header}. {PERSISTENCE_ENTRY}"
            if relative in VIEW and dependency == "iconfigurationmanager":
                yield f"{location(directive.start())}: [config-view] direct include {header}. {VIEW_ENTRY}"

        if relative in VIEW:
            for match in VIEW_SYMBOL.finditer(code):
                yield f"{location(match.start())}: [config-view] direct reference {match.group()}. {VIEW_ENTRY}"


def defined_macros(args):
    active = set()
    arguments = iter(args)
    for option in arguments:
        if not option.startswith(("-D", "-U")):
            continue
        operand = option[2:] or next(arguments, "")
        if not operand:
            raise ValueError("preprocessor option is missing its operand")
        name = operand.split("=", 1)[0]
        if option.startswith("-D"):
            active.add(name)
        else:
            active.discard(name)
    return active


def build_fingerprints(evidence):
    files = [f"{profile}-compile_commands.json" for profile in PROFILES]
    files.extend(f"build/{profile}/firmware.bin" for profile in PROFILES)
    return {file: hashlib.sha256((evidence / file).read_bytes()).hexdigest() for file in files}


def build_errors(root, evidence):
    receipt = evidence / "probe-build-sha256.json"
    if json.loads(receipt.read_text()) != build_fingerprints(evidence):
        yield f"{receipt}: [probe-isolation] files do not match the paired build fingerprints."
        return
    expected_files = {(root / name).resolve(): name for name in PROBE_SOURCES}
    for profile in PROFILES:
        database = evidence / f"{profile}-compile_commands.json"
        matching_files = set()
        for item in json.loads(database.read_text()):
            path = (Path(item["directory"]) / item["file"]).resolve()
            if path not in expected_files:
                continue
            matching_files.add(path)
            arguments = item["arguments"] if "arguments" in item else shlex.split(item["command"])
            actual = defined_macros(arguments) & PROBE_MACROS
            expected = PROBE_MACROS if profile == "test-wokwi" else set()
            if actual != expected:
                yield f"{database}: [probe-isolation] {expected_files[path]} defines {sorted(actual)}, expected {sorted(expected)}."
        for path in expected_files.keys() - matching_files:
            yield f"{database}: [probe-isolation] no compile command for {expected_files[path]}."

        firmware = evidence / "build" / profile / "firmware.bin"
        image = firmware.read_bytes()
        if not image or image[0] != 0xE9:
            yield f"{firmware}: [probe-isolation] expected an ESP32 application image."
        elif profile == "test-wokwi":
            for marker in PROBE_MARKERS:
                if marker not in image:
                    yield f"{firmware}: [probe-isolation] missing {marker.decode().strip()}."
        elif b"ThemeMenu " in image:
            yield f"{firmware}: [probe-isolation] ThemeMenu probe leaked into release."


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="check this checkout or an isolated fixture")
    parser.add_argument("--build-evidence", type=Path, help="directory with both PlatformIO profiles, commands and images")
    args = parser.parse_args()
    try:
        errors = list(source_errors(args.root.resolve()))
        if args.build_evidence:
            errors.extend(build_errors(args.root.resolve(), args.build_evidence.resolve()))
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"Config menu architecture check input error: {error}", file=sys.stderr)
        return 2
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("Config menu dependency checks passed (four source files).")
    if args.build_evidence:
        print("ThemeMenu probe isolation passed (test-wokwi and release compile commands and BINs).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
