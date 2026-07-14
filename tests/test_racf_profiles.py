import unittest
from pathlib import Path

import pandas as pd
import yaml

from mfaudit.cli import run_control
from mfaudit.racf_profiles import DatasetProfileIndex, dataset_profile_regex


class DatasetProfileIndexTests(unittest.TestCase):
    def test_generic_qualifier_matching(self):
        self.assertIsNotNone(dataset_profile_regex("SYS1.**").fullmatch("SYS1"))
        self.assertIsNotNone(dataset_profile_regex("SYS1.**").fullmatch("SYS1.PARMLIB"))
        self.assertIsNotNone(dataset_profile_regex("APP.*.DATA").fullmatch("APP.TEST.DATA"))
        self.assertIsNone(dataset_profile_regex("APP.*.DATA").fullmatch("APP.A.B.DATA"))
        self.assertIsNotNone(dataset_profile_regex("USER%.**").fullmatch("USER1.DATA"))

    def test_discrete_profile_precedes_generic_profile(self):
        profiles = pd.DataFrame([
            {
                "DSBD_NAME": "SYS1.**", "DSBD_GENERIC": "YES",
                "DSBD_VOL": "", "DSBD_UACC": "READ",
            },
            {
                "DSBD_NAME": "SYS1.PARMLIB", "DSBD_GENERIC": "NO",
                "DSBD_VOL": "VOL001", "DSBD_UACC": "NONE",
            },
        ])
        index = DatasetProfileIndex(profiles)

        self.assertEqual(index.match("SYS1.PARMLIB", "VOL001")["DSBD_UACC"], "NONE")
        self.assertEqual(index.match("SYS1.LINKLIB", "VOL001")["DSBD_UACC"], "READ")

    def test_more_specific_generic_profile_wins(self):
        profiles = pd.DataFrame([
            {"DSBD_NAME": "APP.**", "DSBD_GENERIC": "YES"},
            {"DSBD_NAME": "APP.PROD.**", "DSBD_GENERIC": "YES"},
        ])
        index = DatasetProfileIndex(profiles)

        self.assertEqual(index.match("APP.PROD.DATA")["DSBD_NAME"], "APP.PROD.**")


class OptionalDCOLLECTControlTests(unittest.TestCase):
    def test_new_controls_skip_without_dcollect(self):
        controls_path = Path(__file__).parents[2] / "my_custom_controls.yaml"
        controls = yaml.safe_load(controls_path.read_text(encoding="utf-8"))["controls"]
        controls = [c for c in controls if c["control_id"].startswith("CUSTOM-DS-")]

        for control in controls:
            status, detail, findings = run_control(
                control, setropts=object(), irrdbu00=object(), dcollect=None,
            )
            self.assertEqual(status, "SKIP")
            self.assertIn("DCOLLECT not provided", detail)
            self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
