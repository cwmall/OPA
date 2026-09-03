import os
from pathlib import Path
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_MODULE_TEST_ROOT = Path(tempfile.mkdtemp(prefix="opa-admin-gui-test-"))
os.environ["OPA_CONFIG_PATH"] = str(_MODULE_TEST_ROOT / "config.json")
os.environ["OPA_PROFILE_DIR"] = str(_MODULE_TEST_ROOT / "profiles")

from PyQt6.QtWidgets import QApplication
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from admin_security import (
    AdminSecurityError,
    AdminSessionManager,
    build_signed_package,
    enroll_device,
)
from gui.main_window import MainWindow
from eclipse_references import (
    available_eclipse_reference_specs,
    load_eclipse_reference_dataset,
)
from orbit_determination import load_dataset
from reference_comparison import get_reference_dataset
from test_admin_security import MemoryProtector, synthetic_content


class AdminGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    @classmethod
    def tearDownClass(cls):
        import shutil
        shutil.rmtree(_MODULE_TEST_ROOT, ignore_errors=True)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        os.environ["OPA_PROFILE_DIR"] = str(root / "profiles")
        self.window = MainWindow(application_config_path=root / "config.json")
        self.protector = MemoryProtector()
        self.signing_key = Ed25519PrivateKey.generate()
        self.enrollment_path = root / "enrollment.json"
        verification_key = self.signing_key.public_key().public_bytes(
            Encoding.Raw, PublicFormat.Raw
        )
        enrollment = enroll_device(
            verification_key,
            enrollment_path=self.enrollment_path,
            protector=self.protector,
        )
        self.package_path = root / "synthetic.opa-admin"
        self.package_path.write_bytes(
            build_signed_package(
                synthetic_content(),
                "gui test password",
                enrollment,
                self.signing_key,
                protector=self.protector,
            )
        )
        self.window.admin_session = AdminSessionManager(
            enrollment_path=self.enrollment_path,
            protector=self.protector,
        )

    def tearDown(self):
        self.window.close()
        self.app.processEvents()
        self.temp.cleanup()

    def test_unlock_installs_and_logout_removes_all_session_content(self):
        public_module_count = self.window.module_tabs.count()
        self.window.unlock_admin_package(self.package_path, "gui test password")
        self.assertTrue(self.window.admin_session.unlocked)
        self.assertTrue(self.window.profile_store.is_session_profile("admin-synthetic-demo"))
        self.assertEqual(
            get_reference_dataset("admin-synthetic-reference")["admin_session"],
            True,
        )
        eclipse_ids = {
            spec.dataset_id for spec in available_eclipse_reference_specs()
        }
        self.assertIn("admin-synthetic-eclipse", eclipse_ids)
        self.assertEqual(
            len(load_eclipse_reference_dataset("admin-synthetic-eclipse").events),
            1,
        )
        self.assertEqual(load_dataset().dataset_id, "synthetic-od-demo-v1")
        self.assertFalse(hasattr(self.window, "orbit_determination_page"))
        self.assertEqual(self.window.module_tabs.count(), public_module_count + 1)
        self.assertTrue(self.window.activate_profile("admin-synthetic-demo"))

        self.window.logout_admin_session()
        self.assertFalse(self.window.admin_session.unlocked)
        self.assertFalse(self.window.profile_store.is_session_profile("admin-synthetic-demo"))
        with self.assertRaises(Exception):
            get_reference_dataset("admin-synthetic-reference")
        eclipse_ids = {
            spec.dataset_id for spec in available_eclipse_reference_specs()
        }
        self.assertNotIn("admin-synthetic-eclipse", eclipse_ids)
        self.assertEqual(load_dataset().dataset_id, "synthetic-od-demo-v1")
        self.assertEqual(self.window.module_tabs.count(), public_module_count)
        self.assertEqual(self.window.active_profile_id, "synthetic_geo_demo")

    def test_settings_never_persists_password_package_or_unlock_state(self):
        settings = self.window.settings_overlay
        settings.admin_package_path.setText(str(self.package_path))
        settings.admin_password.setText("gui test password")
        self.assertTrue(settings._unlock_admin_package())
        self.assertEqual(settings.admin_password.text(), "")
        self.window.persist_configuration("normal", "en")
        config_text = Path(self.window.application_config_path).read_text(encoding="utf-8")
        self.assertNotIn("gui test password", config_text)
        self.assertNotIn("opa-admin", config_text)
        self.assertNotIn("unlocked", config_text)

    def test_standard_local_package_is_selected_automatically(self):
        installed = Path(os.environ["OPA_CONFIG_PATH"]).parent / "admin" / "private.opa-admin"
        installed.parent.mkdir(parents=True, exist_ok=True)
        installed.write_bytes(b"synthetic package placeholder")
        settings = self.window.settings_overlay
        settings.admin_package_path.clear()
        settings.sync_admin_status()
        self.assertEqual(settings.admin_package_path.text(), "")
        self.assertFalse(settings.admin_package_picker.isVisibleTo(settings))
        self.assertIn("OUTSIDE APPLICATION FOLDER", settings.admin_package_storage_status.text())

    def test_ready_admin_panel_hides_private_paths_and_setup_controls(self):
        installed = Path(os.environ["OPA_CONFIG_PATH"]).parent / "admin" / "private.opa-admin"
        installed.parent.mkdir(parents=True, exist_ok=True)
        installed.write_bytes(b"synthetic package placeholder")
        settings = self.window.settings_overlay
        settings.sync_admin_status()
        self.assertFalse(settings.admin_enrollment_group.isVisibleTo(settings))
        self.assertFalse(settings.admin_package_picker.isVisibleTo(settings))
        visible_text = " ".join(
            label.text() for label in settings.findChildren(type(settings.admin_status))
        )
        self.assertNotIn(str(installed.parent), visible_text)
        self.assertEqual(settings.admin_unlock_group.title(), "ADMIN PASSWORD")
        self.window.apply_language("az")
        settings.sync_admin_status()
        self.assertIn("HAZIRDIR", settings.admin_package_storage_status.text())
        self.assertEqual(settings.admin_unlock_group.title(), "ADMİN PAROLU")


if __name__ == "__main__":
    unittest.main()
