"""Compare explicit saves with the T1 baseline and check same-flash restart."""

import json
from pathlib import Path
import re
import tempfile

from menu_scenarios import ENTER_THEME, SAVE_DAY, assert_trace, run_scenario, scenario_document
from scenario_controls import EXIT_SETTINGS, LIGHT_ON, SAVE_NIGHT, assert_browser_hold, set_light
from runner import SUITE

BOOT = "SPI_FAST_FLASH_BOOT"
READY = "[T] OemOilPanel loaded successfully"
RESTART = "[T] ThemeMenu restart requested"
ROM_BOOT = re.compile(r"^rst:0x[0-9a-f]+ \(([^)]+)\),boot:0x[0-9a-f]+ \(([^)]+)\)", re.MULTILINE)


def reset_wiring(path):
    circuit = json.loads((SUITE.parent / "diagram_automated.json").read_text())
    circuit["parts"].append({"type": "wokwi-pushbutton", "id": "reset_btn", "top": 200, "left": -88,
                             "attrs": {"bounce": "0", "label": "Test restart"}})
    circuit["connections"].extend([
        ["reset_btn:1.l", "esp:21", "orange", []],
        ["reset_btn:2.r", "esp:GND.1", "black", []],
    ])
    path.write_text(json.dumps(circuit, indent=2) + "\n")


def reset_moves():
    return (
        {"delay": "500ms"},
        {"set-control": {"part-id": "reset_btn", "name": "pressed", "value": 1}},
        {"delay": "100ms"},
        {"set-control": {"part-id": "reset_btn", "name": "pressed", "value": 0}},
        {"wait-serial": RESTART},
        {"wait-serial": BOOT},
        {"wait-serial": READY},
        {"delay": "600ms"},
        *ENTER_THEME, "A4-reopen.png",
    )


def palette_window(serial, confirm, target):
    begin = f"[T] ThemeMenu action {confirm} start LONG_PRESS"
    end = f"[T] ThemeMenu action {confirm} end LONG_PRESS"
    window = serial.split(begin, 1)[1]
    action = window.split(end, 1)[0]
    save_and_refresh = (rf"\[T\] ThemeMenu write 2 success style_manager\.theme={target}\b"
                        rf"[\s\S]*?\[T\] ThemeMenu menu palette \d+ {target}\b")
    if not re.search(save_and_refresh, action):
        raise ValueError(f"A4 did not confirm and immediately refresh the menu to {target}")
    return re.findall(r"\[T\] ThemeMenu shared palette \d+ (\S+)", window)


def split_software_restart(serial, name):
    boots = list(ROM_BOOT.finditer(serial))
    if any(boot.group(2) != BOOT for boot in boots):
        raise ValueError(f"{name} did not boot from flash throughout the scenario")
    reasons = [boot.group(1) for boot in boots]
    expected = ["POWERON_RESET", "SW_CPU_RESET"]
    if reasons == [*expected, "TG1WDT_SYS_RESET"]:
        # The Wokwi ROM may retry once before any application output.
        if "[T]" in serial[boots[1].end():boots[2].start()]:
            raise ValueError(f"{name} reset again after application output")
    elif reasons != expected:
        raise ValueError(f"{name} has an unexpected ROM boot sequence: {reasons}")
    before, after = serial[:boots[1].start()], serial[boots[-1].end():]
    if before.count(RESTART) != 1 or RESTART in after:
        raise ValueError(f"{name} did not restart exactly once through the simulator input")
    if READY not in after.split("[T] ThemeMenu action 1 start", 1)[0]:
        raise ValueError(f"{name} did not boot again before entering Theme")
    return before, after


def run_direction(args, original, target, diagram):
    initial_save = SAVE_DAY if original == "Day" else SAVE_NIGHT
    origin = (*initial_save, "long")
    if original == "Night":
        origin = (*initial_save, *EXIT_SETTINGS, *set_light(True), *ENTER_THEME)
    palettes = {}
    for reference in (True, False):
        phase = "reference" if reference else "candidate"
        name = f"A4-{original}-to-{target}-{phase}"
        select = ("short",) if target == "Night" else (() if reference else ("short", "short"))
        before_reset = (*origin, "A4-initial.png", *select, "long", "A4-display.png")
        after_reset = () if reference else reset_moves()
        serial = run_scenario(args, scenario_document(name, (*before_reset, *after_reset)),
                              build_dir=args.reference_build_dir if reference else args.build_dir, diagram=diagram)
        if serial is None:
            continue
        assert_browser_hold(args, name, "A4-display.png", "finish" if reference else "reset")
        if reference:
            if ROM_BOOT.findall(serial) != [("POWERON_RESET", BOOT)]:
                raise ValueError(f"{name} has the wrong number of ROM startups")
        else:
            serial, after = split_software_restart(serial, name)
            assert_trace(after, ENTER_THEME, ())
        confirmation = sum(move in ("short", "long") for move in before_reset)
        assert_trace(serial, before_reset, ((len(initial_save), f"style_manager.theme={original}"),
                                            (confirmation, f"style_manager.theme={target}")))
        if not reference and RESTART not in serial.split(f"[T] ThemeMenu action {confirmation} end LONG_PRESS", 1)[1]:
            raise ValueError(f"{name} restarted before confirmation completed")
        setup = serial.split(f"[T] ThemeMenu action {confirmation} start LONG_PRESS", 1)[0]
        shared = re.findall(r"\[T\] ThemeMenu shared palette \d+ (\S+)", setup)
        if not shared or shared[-1] != original:
            raise ValueError(f"{name} did not start the confirmation with shared palette {original}")
        if original == "Night" and not re.search(re.escape(LIGHT_ON) + r"[\s\S]*?ThemeMenu shared palette \d+ Night\b", setup):
            raise ValueError(f"{name} did not establish Night through GPIO33 before confirmation")
        palettes[phase] = palette_window(serial, confirmation, target)
    if palettes and palettes["reference"] != palettes["candidate"]:
        raise ValueError(f"A4 {original} to {target} changed the shared palette events: {palettes}")
    if palettes:
        print(f"A4 {original} to {target} saved, compared with T1 and recovered from reset. Review the LCD frames.")


def run(args):
    with tempfile.TemporaryDirectory() as directory:
        diagram = Path(directory) / "A4-diagram.json"
        reset_wiring(diagram)
        for original, target in (("Day", "Night"), ("Night", "Day")):
            run_direction(args, original, target, diagram)
