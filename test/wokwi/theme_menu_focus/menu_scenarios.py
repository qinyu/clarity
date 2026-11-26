"""Exercise the real GPIO32 menu flow and verify its write trace."""

import json
import re
import subprocess

from runner import APP_OFFSET, FLASH_SIZE, check_png, digest, prepare_simulation

ENTER_DISPLAY = ("long", "short", "long")
ENTER_THEME = (*ENTER_DISPLAY, "long")
SAVE_DAY = (*ENTER_THEME, "long")
SCENARIOS = {
    "A1": (
        ("A1", (*ENTER_THEME, "short", "long", "long", "A1-open.png", "long", "A1-confirm.png",
                "long", "A1-reopen.png"), ((6, "style_manager.theme=Night"), (8, "style_manager.theme=Night"))),
    ),
    "A2": (
        ("A2-fresh", (*ENTER_THEME, "A2-fresh.png"), ()),
        ("A2-saved", (*SAVE_DAY, "long", "A2-saved.png"), ((5, "style_manager.theme=Day"),)),
    ),
    "A3": (
        ("A3", (*SAVE_DAY, "long", "short", "A3-night.png", "short", "A3-back.png", "short",
                "A3-day.png", "short", "short", "long", "A3-configuration.png", "short",
                "long", "long", "A3-reopen.png"), ((5, "style_manager.theme=Day"),)),
    ),
    "A7": (
        ("A7", (*ENTER_DISPLAY, "short", "long", *(["short"] * 5), "long", "short", "long",
                "A7-initial.png", *(["short"] * 5), "A7-saved.png"), ((11, "style_manager.brightness=50"),)),
    ),
}


def scenario_document(name, moves):
    steps = [{"wait-serial": "[T] OemOilPanel loaded successfully"}, {"delay": "600ms"}]
    for move in moves:
        if isinstance(move, dict):
            steps.append(move)
            continue
        if move.endswith(".png"):
            steps.append({"take-screenshot": {"part-id": "lcd1", "save-to": move}})
            continue
        steps.extend([
            {"set-control": {"part-id": "btn1", "name": "pressed", "value": 1}},
            {"delay": {"short": "800ms", "long": "2000ms"}[move]},
            {"set-control": {"part-id": "btn1", "name": "pressed", "value": 0}},
            {"delay": "600ms"},
        ])
    steps.append({"delay": "500ms"})
    return {"name": name, "version": 1, "steps": steps}


def assert_trace(serial, moves, expected_writes):
    presses = [move.upper() + "_PRESS" for move in moves if move in ("short", "long")]
    actions = list(re.finditer(r"\[T\] ThemeMenu action (\d+) (start|end) (\w+)", serial))
    expected_actions = [(str(i), phase, press) for i, press in enumerate(presses, 1) for phase in ("start", "end")]
    if [entry.groups() for entry in actions] != expected_actions:
        raise ValueError("The GPIO32 press and completion trace does not match the scenario")

    write_pattern = r"\[T\] ThemeMenu write (\d+) (attempt|success) (\S+)"
    writes = re.findall(write_pattern, serial)
    expected = [(str(i), phase, target) for i, (_, target) in enumerate(expected_writes, 1)
                for phase in ("attempt", "success")]
    if writes != expected:
        raise ValueError(f"Expected writes {expected}, observed {writes}")
    for index, (action_number, _) in enumerate(expected_writes):
        begin, end = actions[(action_number - 1) * 2:action_number * 2]
        if re.findall(write_pattern, serial[begin.end():end.start()]) != expected[index * 2:index * 2 + 2]:
            raise ValueError(f"Action {action_number} did not perform its expected configuration write")
    if "A3-night.png" in moves:
        browse_start = serial.index("[T] ThemeMenu action 6 start")
        if re.search(r"\[T\] ThemeMenu (?:menu|shared) palette ", serial[browse_start:]):
            raise ValueError("Browsing or returning applied a theme palette")


def capture_files(scenario):
    return ["serial.log", *(step["take-screenshot"]["save-to"] for step in scenario["steps"] if "take-screenshot" in step)]


def assert_capture(run, names, build_dir):
    image = run / "firmware.full.bin"
    receipt = json.loads((run / "capture.json").read_text())
    manifest = json.loads((run / "sha256.json").read_text())
    if digest(image) != receipt.get("loaded_image_sha256") or receipt.get("loaded_image_sha256") != manifest.get(str(image)):
        raise ValueError("The capture does not match the prepared flash image")
    if build_dir is not None:
        flash = image.read_bytes()
        app = (build_dir / "firmware.bin").read_bytes()
        if len(flash) != FLASH_SIZE or not app or flash[APP_OFFSET:APP_OFFSET + len(app)] != app:
            raise ValueError(f"The capture firmware does not match the requested build: {run}")
    for name in names:
        if receipt.get("files", {}).get(name) != digest(run / name):
            raise ValueError(f"The captured file does not match its receipt: {name}")
        if name.endswith(".png"):
            check_png(run / name)
    return (run / "serial.log").read_text(errors="replace")


def run_scenario(args, scenario, *, build_dir=None, diagram=None, nvs_image=None):
    name = scenario["name"]
    run = args.out.resolve() / name
    build = build_dir or args.build_dir
    names = capture_files(scenario)
    if not args.check_capture:
        run.mkdir(parents=True)
        print(f"{name} artifacts: {run}", flush=True)
        prepare_simulation(build.resolve(), run, diagram=diagram, nvs_image=nvs_image)
        (run / "scenario.yaml").write_text(json.dumps(scenario, indent=2) + "\n")
        if args.prepare_only:
            return None
        image_sha = digest(run / "firmware.full.bin")
        subprocess.run(
            ["wokwi-cli", ".", "--scenario", "scenario.yaml", "--serial-log-file", "serial.log",
             "--timeout", "120000"], cwd=run, check=True, timeout=180,
        )
        receipt = {"loaded_image_sha256": image_sha, "files": {name: digest(run / name) for name in names}}
        (run / "capture.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return assert_capture(run, names, build)


def execute(case, args):
    for name, moves, expected_writes in SCENARIOS[case]:
        serial = run_scenario(args, scenario_document(name, moves))
        if serial is None:
            continue
        assert_trace(serial, moves, expected_writes)
        run = args.out.resolve() / name
        print(f"{name} trace and screenshots verified in {run}. Review the LCD frames.")
