"""tests/test_paths.py — Tests pour tracker/paths.py en mode frozen (PyInstaller)."""
import sys
from unittest.mock import patch

import tracker.paths as paths


class TestGetDataDirFrozen:
    def test_get_data_dir_frozen(self, tmp_path):
        fake_exe = str(tmp_path / "pokemon-tcg-tracker.exe")
        with patch.object(sys, 'frozen', True, create=True), \
             patch.object(sys, 'executable', fake_exe, create=True):
            result = paths.get_data_dir()
        assert result == str(tmp_path / "data")

    def test_get_data_dir_frozen_env_takes_priority(self, tmp_path, monkeypatch):
        fake_exe = str(tmp_path / "pokemon-tcg-tracker.exe")
        custom_dir = str(tmp_path / "custom_data")
        monkeypatch.setenv("PTCG_DATA_DIR", custom_dir)
        with patch.object(sys, 'frozen', True, create=True), \
             patch.object(sys, 'executable', fake_exe, create=True):
            result = paths.get_data_dir()
        assert result == custom_dir

    def test_get_data_dir_dev(self, monkeypatch):
        monkeypatch.delenv("PTCG_DATA_DIR", raising=False)
        with patch.object(sys, 'frozen', False, create=True):
            result = paths.get_data_dir()
        assert result.endswith("data")
        assert "pokemon-tcg-tracker" in result

    def test_get_data_dir_dev_env_takes_priority(self, tmp_path, monkeypatch):
        custom_dir = str(tmp_path / "custom_data")
        monkeypatch.setenv("PTCG_DATA_DIR", custom_dir)
        with patch.object(sys, 'frozen', False, create=True):
            result = paths.get_data_dir()
        assert result == custom_dir


class TestGetProjectRootFrozen:
    def test_get_project_root_frozen(self, tmp_path):
        fake_exe = str(tmp_path / "pokemon-tcg-tracker.exe")
        with patch.object(sys, 'frozen', True, create=True), \
             patch.object(sys, 'executable', fake_exe, create=True):
            result = paths.get_project_root()
        assert result == str(tmp_path)

    def test_get_project_root_dev(self):
        with patch.object(sys, 'frozen', False, create=True):
            result = paths.get_project_root()
        assert result.endswith("pokemon-tcg-tracker")  # racine projet, pas sous-dossier tracker/
