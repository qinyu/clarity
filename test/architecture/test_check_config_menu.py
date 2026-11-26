"""Run the architecture lint entry point against isolated source and build fixtures."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from check_config_menu import PANEL, PROBE_MARKERS, PROBE_SOURCES, VIEW

CHECKER = Path(__file__).with_name("check_config_menu.py")


class ConfigMenuCheckTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.write(PANEL[0], '#include "interfaces/i_configuration_manager.h"\n')
        self.write(PANEL[1], 'manager->GetConfigSection(name);\nmanager->UpdateConfig(key, value);\n')
        self.write(VIEW[0], '#include "interfaces/i_style_manager.h"\n')
        self.write(VIEW[1], 'void ConfigComponent::SetCurrentIndex(size_t index) { /* render */ }\n')

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def check(self, *args):
        return subprocess.run(
            [sys.executable, str(CHECKER), "--root", str(self.root), *args],
            capture_output=True, text=True, check=False,
        )

    def test_existing_panel_and_rendering_entries_are_allowed(self):
        self.write("src/components/unrelated.cpp", '#include <nvs_flash.h>\n')
        run = self.check()
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn("four source files", run.stdout)

    def test_direct_persistence_headers_are_blocked_in_both_classes(self):
        self.write(PANEL[0], '#include "providers/storage_provider.h"\n')
        self.write(PANEL[1], '# include /* header */ <nvs_flash.h>\n')
        self.write(VIEW[0], '#include <Preferences.h>\n')
        self.write(VIEW[1], '#include \\\n <nvs.h>\n')
        run = self.check()
        self.assertEqual(run.returncode, 1)
        for file, header in zip((*PANEL, *VIEW), ("storage_provider.h", "nvs_flash.h", "Preferences.h", "nvs.h")):
            self.assertRegex(run.stderr, rf"{file}:1:\d+: \[config-persistence\].*{header}.*GetConfigSection\(\)")

    def test_direct_config_types_and_theme_key_are_blocked_in_the_view(self):
        self.write(VIEW[0], '#include "interfaces/i_configuration_manager.h"\nclass IConfigurationManager;\n')
        self.write(VIEW[1], 'auto key = UIStrings::ConfigKeys::STYLE_MANAGER_THEME;\n')
        run = self.check()
        self.assertEqual(run.returncode, 1)
        self.assertRegex(run.stderr, rf"{VIEW[0]}:1:\d+: \[config-view\].*i_configuration_manager.h")
        self.assertRegex(run.stderr, rf"{VIEW[0]}:2:\d+: \[config-view\].*IConfigurationManager")
        self.assertRegex(run.stderr, rf"{VIEW[1]}:1:\d+: \[config-view\].*STYLE_MANAGER_THEME.*SetCurrentIndex\(\)")

    def test_comment_and_string_spellings_do_not_count_as_dependencies(self):
        self.write(VIEW[1], '''
// #include "providers/storage_provider.h" IConfigurationManager \\
#include <Preferences.h>
/*
#include <nvs_flash.h>
STYLE_MANAGER_THEME
*/
const char* name = "IConfigurationManager and \\"STYLE_MANAGER_THEME\\"";
const char* raw = u8R"test(
#include <nvs.h>
#include "interfaces/i_configuration_manager.h"
STYLE_MANAGER_THEME
)test";
''')
        run = self.check()
        self.assertEqual(run.returncode, 0, run.stderr)

    def mock_builds(self, release_flags=(), release_probe=False):
        evidence = self.root / "evidence"
        for profile in ("test-wokwi", "release"):
            flags = ("-D", "WOKWI_EMULATOR=1", "-DTEST_LOGS") if profile == "test-wokwi" else release_flags
            commands = [
                {"directory": str(self.root), "file": file, "arguments": ["g++", *flags, "-c", file]}
                for file in PROBE_SOURCES
            ]
            self.write(f"evidence/{profile}-compile_commands.json", json.dumps(commands))
            firmware = evidence / "build" / profile / "firmware.bin"
            firmware.parent.mkdir(parents=True)
            markers = PROBE_MARKERS if profile == "test-wokwi" or release_probe else ()
            firmware.write_bytes(b"\xe9" + b"\0".join(markers))
        return evidence

    def test_both_builds_enforce_expanded_flags_and_linked_markers(self):
        suspicious = self.mock_builds(release_flags=("-DTEST_LOGS",), release_probe=True)
        run = self.check("--build-evidence", str(suspicious))
        self.assertEqual(run.returncode, 1)
        self.assertIn("release-compile_commands.json", run.stderr)
        self.assertIn("ThemeMenu probe leaked into release", run.stderr)

    def test_build_check_accepts_separated_define_and_undef_options(self):
        valid = self.mock_builds(release_flags=("-DTEST_LOGS", "-U", "TEST_LOGS"))
        run = self.check("--build-evidence", str(valid))
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn("probe isolation passed", run.stdout)


if __name__ == "__main__":
    unittest.main()
