"""Release-version policy tests."""

import re
import unittest

from app_version import APP_VERSION


class AppVersionTests(unittest.TestCase):

    def test_version_is_semantic_version(self):
        self.assertRegex(
            APP_VERSION,
            re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$"),
        )


if __name__ == "__main__":
    unittest.main()
