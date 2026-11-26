"""Exercise GPIO33 and verify the theme menu does not change its effect."""

import re

from menu_scenarios import ENTER_DISPLAY, SAVE_DAY, assert_trace, run_scenario, scenario_document
from scenario_controls import EXIT_SETTINGS, LIGHT_OFF, LIGHT_ON, SAVE_NIGHT, assert_browser_hold, set_light


def run_lights(args, saved_night):
    name = "A6" if saved_night else "A5"
    stored = "Night" if saved_night else "Day"
    save = SAVE_NIGHT if saved_night else SAVE_DAY
    start = (*save, *EXIT_SETTINGS)
    moves = (*start, *set_light(True), f"{name}-lights-on.png")
    if saved_night:
        moves += (*set_light(False), f"{name}-lights-off.png")
    moves += (*ENTER_DISPLAY, "long", f"{name}-open.png")
    final_frame = f"{name}-open.png"
    if not saved_night:
        final_frame = "A5-browse.png"
        moves += ("short", final_frame)
    serial = run_scenario(args, scenario_document(name, moves))
    if serial is None:
        return
    assert_browser_hold(args, name, final_frame)
    assert_trace(serial, moves, ((len(save), f"style_manager.theme={stored}"),))
    exit_marker = f"[T] ThemeMenu action {len(start)} end LONG_PRESS"
    open_marker = f"[T] ThemeMenu action {len(start) + len(ENTER_DISPLAY) + 1} start LONG_PRESS"
    before, during = serial.split(open_marker, 1)
    lights = before.split(exit_marker, 1)[1]
    expected = re.escape(LIGHT_ON) + r"[\s\S]*?ThemeMenu shared palette \d+ Night\b"
    if saved_night:
        expected += r"[\s\S]*?" + re.escape(LIGHT_OFF) + r"[\s\S]*?ThemeMenu shared palette \d+ Day\b"
    if len(re.findall(r"Lights(?:On|Off)Activate\(\)", lights)) != (2 if saved_night else 1) or not re.search(expected, lights):
        raise ValueError(f"{name} did not observe GPIO33 and the expected shared palette transitions")
    if re.search(r"Lights(?:On|Off)Activate\(\)|\[T\] ThemeMenu (?:write |(?:menu|shared) palette )", during):
        raise ValueError(f"{name} changed theme state while opening or browsing Theme")
    print(f"{name} GPIO33 and Theme window verified. Review the LCD frames.")
