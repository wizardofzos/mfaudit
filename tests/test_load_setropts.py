import tempfile
import unittest
from pathlib import Path

from mfaudit.cli import load_setropts


# Raw SETROPTS LIST capture (general/password options first, class lists last).
SETROPTS_LIST = """\
READY
  SETROPTS LIST
  ATTRIBUTES = INITSTATS NOCMDVIOL
  PASSWORD PROCESSING OPTIONS:
    PASSWORD CHANGE INTERVAL IS  180 DAYS.
  ACTIVE CLASSES  =  DATASET FACILITY
  SETR RACLIST CLASSES  =  FACILITY
READY
"""

# The historical REXX/IRRXUTIL KEY:VALUE export.
KEY_VALUE = "INITSTAT:TRUE\nINTERVAL:180\nCLASSACT:DATASET\nCLASSACT:FACILITY\n"


class LoadSetroptsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _write(self, text):
        path = self.tmp / "SETROPTS"
        path.write_text(text)
        return str(path)

    def test_none_path_returns_none(self):
        self.assertIsNone(load_setropts(None))

    def test_loads_raw_setropts_list(self):
        s = load_setropts(self._write(SETROPTS_LIST))
        settings = s.fieldInfo.set_index("Setting")["Value"]
        self.assertEqual(settings["INTERVAL"], 180)
        self.assertEqual(settings["INITSTAT"], "TRUE")

    def test_loads_key_value_export(self):
        s = load_setropts(self._write(KEY_VALUE))
        settings = s.fieldInfo.set_index("Setting")["Value"]
        self.assertEqual(settings["INTERVAL"], 180)
        self.assertEqual(settings["INITSTAT"], "TRUE")


if __name__ == "__main__":
    unittest.main()
