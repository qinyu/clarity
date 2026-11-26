"""Load and explicitly replace a legacy theme in real NVS."""

from pathlib import Path
import subprocess
import sys
import tempfile

from menu_scenarios import ENTER_DISPLAY, assert_trace, run_scenario, scenario_document
from runner import NVS_OFFSET, NVS_SIZE


def run(args):
    moves = (*ENTER_DISPLAY, "A8-display-first.png", "long", "A8-open-first.png", "short", "short", "long",
             "short", "long", "A8-display-second.png", "long", "A8-open-second.png",
             "short", "long", "A8-confirm.png", "long", "A8-reopen.png")
    scenario = scenario_document("A8", moves)
    fixture = Path(__file__).with_name("A8_legacy.csv")
    with tempfile.TemporaryDirectory() as directory:
        nvs = Path(directory) / "legacy.bin"
        subprocess.run([sys.executable, str(args.nvs_gen.resolve()), "generate", str(fixture), str(nvs),
                        hex(NVS_SIZE), "--version", "2"], check=True)
        serial = run_scenario(args, scenario, nvs_image=nvs)
        if serial is None:
            return
        image = (args.out.resolve() / "A8" / "firmware.full.bin").read_bytes()
        if image[NVS_OFFSET:NVS_OFFSET + NVS_SIZE] != nvs.read_bytes():
            raise ValueError("A8 did not preload the expected Legacy NVS fixture")
    assert_trace(serial, moves, ((12, "style_manager.theme=Night"),))
    print("A8 Legacy preload and explicit write verified. Review the LCD frames.")
