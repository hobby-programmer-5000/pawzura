import unittest
from pawzura.windows import ordinary_app_window


class WindowFilterTests(unittest.TestCase):
    def test_regular_window_with_system_menu_remains_eligible(self):
        self.assertTrue(ordinary_app_window(0x14CF0000,0x100))

    def test_overlay_noactivate_tool_and_child_surfaces_are_rejected(self):
        # Full-screen transparent GPU overlay; embedded renderer child surface.
        self.assertFalse(ordinary_app_window(0x94000000,0x08080080))
        self.assertFalse(ordinary_app_window(0x5C000000,0x08280080))
        for extended in (0x80,0x08000000,0x20):
            self.assertFalse(ordinary_app_window(0x14CF0000,extended))
        self.assertFalse(ordinary_app_window(0x54CF0000,0))
        self.assertFalse(ordinary_app_window(0,0))
