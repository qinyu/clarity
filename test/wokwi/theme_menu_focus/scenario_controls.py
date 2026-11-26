"""Shared GPIO33 controls and simulator timing checks for acceptance scenarios."""

import json

from menu_scenarios import ENTER_THEME

SAVE_NIGHT = (*ENTER_THEME, "short", "long")
EXIT_SETTINGS = ("short", "short", "long", *(["short"] * 6), "long")
LIGHT_ON = "LightsOnActivate() - Setting NIGHT theme"
LIGHT_OFF = "LightsOffActivate() - Setting DAY theme"


def set_light(on):
    return (
        {"set-control": {"part-id": "trigger_btn4", "name": "pressed", "value": int(on)}},
        {"wait-serial": LIGHT_ON if on else LIGHT_OFF},
        {"delay": "600ms"},
    )


def assert_browser_hold(args, name, frame, boundary="finish"):
    if args.check_capture:
        receipt = json.loads((args.out.resolve() / name / "capture.json").read_text())
        times = receipt.get("simulator_ms", {})
        start = times.get(frame)
        end = times.get(boundary)
        if type(start) is not int or type(end) is not int or start < 0 or end - start < 500:
            raise ValueError(f"{name} does not record 500ms of simulator idle time after {frame}")
