"""
Phase 2 GUI Tests:
- HistoryDialog initialization and record display
"""
import os
import sys
import unittest
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
import database
from history_dialog import HistoryDialog

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)


class TestPhase2GUI(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db = database.Database(Path(self.tmpdir.name) / "gui_test.db")
        self.db.initialize()
        self.dialog = HistoryDialog(db=self.db)
        self.dialog.show()

    def tearDown(self):
        self.dialog.close()
        self.dialog.deleteLater()
        self.db.close()
        self.tmpdir.cleanup()
        app.processEvents()

    def test_history_dialog_creation(self):
        """Verify dialog title and empty state."""
        self.assertIn("History", self.dialog.windowTitle())
        self.assertFalse(self.dialog.lbl_empty.isHidden())

    def test_history_dialog_with_records(self):
        """Verify dialog lists added records."""
        self.db.history.add_record(
            job_id="j-1",
            title="GUI Test Video",
            url="https://youtube.com/watch?v=123",
            file_path="C:/Downloads/video.mp4"
        )
        self.dialog.load_history()
        self.assertTrue(self.dialog.lbl_empty.isHidden())
        self.assertFalse(self.dialog.list_widget.isHidden())
        self.assertEqual(self.dialog.list_widget.count(), 1)


if __name__ == "__main__":
    unittest.main()
