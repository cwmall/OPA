"""CP referanslarının SRP seçimi ilə düzgün ayrılması üçün testlər."""

import unittest

from reference_comparison import (
    DEFAULT_REFERENCE_DATASET_ID,
    SECOND_REFERENCE_DATASET_ID,
    load_reference_scenario,
    reference_dataset_has_scenario,
)


class ReferenceSrpDataTests(unittest.TestCase):

    def test_cp_and_non_cp_references_are_distinct(self):
        for dataset_id in (
            DEFAULT_REFERENCE_DATASET_ID,
            SECOND_REFERENCE_DATASET_ID,
        ):
            for include_moon in (False, True):
                self.assertTrue(
                    reference_dataset_has_scenario(
                        dataset_id,
                        include_moon,
                        include_srp=True,
                    )
                )
                normal = load_reference_scenario(
                    include_moon,
                    dataset_id,
                    include_srp=False,
                )
                cp = load_reference_scenario(
                    include_moon,
                    dataset_id,
                    include_srp=True,
                )
                self.assertNotEqual(normal["path"], cp["path"])
                self.assertTrue(cp["include_srp"])
                self.assertEqual(cp["states"].shape, (25, 6))
                self.assertEqual(cp["ignored_terminal_rows"], 0)
                self.assertEqual(cp["satellite_name"], "SYNTHETIC GEO DEMO")


if __name__ == "__main__":
    unittest.main()
