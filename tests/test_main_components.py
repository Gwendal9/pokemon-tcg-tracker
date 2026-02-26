"""Tests Story 1.3 — Application arrière-plan & System Tray.

Tous les tests GUI (pystray, pywebview) utilisent des mocks —
l'app est Windows-only et ne peut pas être lancée en WSL/CI.
"""
import asyncio
import logging
import logging.handlers
import os
import threading
import pytest
from unittest.mock import MagicMock, patch, call

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ---------------------------------------------------------------------------
# TrackerAPI — Task 1
# ---------------------------------------------------------------------------

class TestTrackerAPI:
    def test_init_stores_db_and_creates_models(self, tmp_path):
        from tracker.db.database import DatabaseManager
        from tracker.db.models import Models
        from tracker.api.api import TrackerAPI

        db = DatabaseManager(db_path=str(tmp_path / "test.db"))
        api = TrackerAPI(db)

        assert api._db is db
        assert isinstance(api._models, Models)

    def test_init_creates_threading_lock(self, tmp_path):
        from tracker.db.database import DatabaseManager
        from tracker.api.api import TrackerAPI

        db = DatabaseManager(db_path=str(tmp_path / "test.db"))
        api = TrackerAPI(db)

        assert hasattr(api, "_db_lock")
        # Vérifier que c'est utilisable comme lock
        acquired = api._db_lock.acquire(blocking=False)
        assert acquired
        api._db_lock.release()

    def test_get_capture_status_returns_stub(self, tmp_path):
        import sys
        from tracker.db.database import DatabaseManager
        from tracker.api.api import TrackerAPI

        db = DatabaseManager(db_path=str(tmp_path / "test.db"))
        api = TrackerAPI(db)

        # MUMU non détecté (FindWindow retourne 0)
        sys.modules["win32gui"].FindWindow.return_value = 0
        result = asyncio.run(api.get_capture_status())

        assert isinstance(result, dict)
        assert result["mumu_detected"] is False
        assert result["state"] == "idle"

    def test_get_capture_status_is_async(self, tmp_path):
        """get_capture_status doit être une coroutine async def."""
        import inspect
        from tracker.db.database import DatabaseManager
        from tracker.api.api import TrackerAPI

        db = DatabaseManager(db_path=str(tmp_path / "test.db"))
        api = TrackerAPI(db)

        assert inspect.iscoroutinefunction(api.get_capture_status)


# ---------------------------------------------------------------------------
# TrayManager — Task 2
# ---------------------------------------------------------------------------

class TestTrayManager:
    def test_init_stores_callbacks(self):
        from tracker.tray import TrayManager

        on_open = MagicMock()
        on_quit = MagicMock()
        tray = TrayManager(on_open_dashboard=on_open, on_quit=on_quit)

        assert tray._on_open_dashboard is on_open
        assert tray._on_quit is on_quit

    def test_init_icon_is_none_before_run(self):
        from tracker.tray import TrayManager

        tray = TrayManager(on_open_dashboard=lambda: None, on_quit=lambda: None)
        assert tray._icon is None

    def test_create_icon_image_returns_64x64(self):
        from tracker.tray import TrayManager

        tray = TrayManager(on_open_dashboard=lambda: None, on_quit=lambda: None)
        img = tray._create_icon_image((128, 128, 128))

        assert img.size == (64, 64)
        assert img.mode == "RGBA"

    def test_set_state_methods_are_noop_before_run(self):
        """set_state_* ne lèvent pas d'erreur si _icon est None."""
        from tracker.tray import TrayManager

        tray = TrayManager(on_open_dashboard=lambda: None, on_quit=lambda: None)
        tray.set_state_active()
        tray.set_state_inactive()
        tray.set_state_error()

    @patch("tracker.tray.pystray")
    def test_run_creates_and_starts_icon(self, mock_pystray):
        from tracker.tray import TrayManager

        on_open = MagicMock()
        on_quit = MagicMock()
        tray = TrayManager(on_open_dashboard=on_open, on_quit=on_quit)
        tray.run()

        mock_pystray.Icon.assert_called_once()
        mock_pystray.Icon.return_value.run.assert_called_once()

    @patch("tracker.tray.pystray")
    def test_run_menu_has_two_items(self, mock_pystray):
        from tracker.tray import TrayManager

        tray = TrayManager(on_open_dashboard=lambda: None, on_quit=lambda: None)
        tray.run()

        # Menu est créé avec 2 items
        menu_call_args = mock_pystray.Menu.call_args
        assert menu_call_args is not None
        assert len(menu_call_args.args) == 2  # 2 MenuItems

    @patch("tracker.tray.pystray")
    def test_stop_calls_icon_stop(self, mock_pystray):
        from tracker.tray import TrayManager

        tray = TrayManager(on_open_dashboard=lambda: None, on_quit=lambda: None)
        tray.run()
        tray.stop()

        mock_pystray.Icon.return_value.stop.assert_called_once()

    @patch("tracker.tray.pystray")
    def test_set_state_active_updates_icon(self, mock_pystray):
        from tracker.tray import TrayManager

        tray = TrayManager(on_open_dashboard=lambda: None, on_quit=lambda: None)
        tray.run()
        tray.set_state_active()

        # _icon.icon a été mis à jour
        assert mock_pystray.Icon.return_value.icon is not None


# ---------------------------------------------------------------------------
# setup_logging — Task 3
# ---------------------------------------------------------------------------

class TestSetupLogging:
    def test_creates_rotating_file_handler(self, tmp_path):
        import main

        log_path = str(tmp_path / "app.log")
        root = logging.getLogger()
        original_handlers = root.handlers[:]
        root.handlers.clear()
        try:
            main.setup_logging(log_path=log_path)
            handlers = root.handlers
            assert any(
                isinstance(h, logging.handlers.RotatingFileHandler)
                for h in handlers
            )
        finally:
            root.handlers = original_handlers

    def test_default_level_is_info(self, tmp_path, monkeypatch):
        import main

        monkeypatch.delenv("PTCG_DEBUG", raising=False)
        log_path = str(tmp_path / "app.log")
        root = logging.getLogger()
        original_handlers = root.handlers[:]
        root.handlers.clear()
        try:
            main.setup_logging(log_path=log_path)
            assert root.level == logging.INFO
        finally:
            root.handlers = original_handlers

    def test_debug_level_when_ptcg_debug_set(self, tmp_path, monkeypatch):
        import main

        monkeypatch.setenv("PTCG_DEBUG", "1")
        log_path = str(tmp_path / "app.log")
        root = logging.getLogger()
        original_handlers = root.handlers[:]
        root.handlers.clear()
        try:
            main.setup_logging(log_path=log_path)
            assert root.level == logging.DEBUG
        finally:
            root.handlers = original_handlers

    def test_rotating_handler_config(self, tmp_path):
        import main

        log_path = str(tmp_path / "app.log")
        root = logging.getLogger()
        original_handlers = root.handlers[:]
        root.handlers.clear()
        try:
            main.setup_logging(log_path=log_path)
            handler = next(
                h for h in root.handlers
                if isinstance(h, logging.handlers.RotatingFileHandler)
            )
            assert handler.maxBytes == 1_000_000
            assert handler.backupCount == 3
        finally:
            root.handlers = original_handlers


# ---------------------------------------------------------------------------
# ui/index.html — Task 4
# ---------------------------------------------------------------------------

def test_index_html_exists():
    path = os.path.join(PROJECT_ROOT, "ui", "index.html")
    assert os.path.isfile(path), "ui/index.html doit exister"


def test_app_js_contains_pywebviewready():
    # Story 4.1 : le listener pywebviewready est dans app.js (pas inline dans index.html)
    path = os.path.join(PROJECT_ROOT, "ui", "app.js")
    with open(path) as f:
        content = f.read()
    assert "pywebviewready" in content, "ui/app.js doit attendre l'event pywebviewready"


def test_index_html_is_valid_html5():
    path = os.path.join(PROJECT_ROOT, "ui", "index.html")
    with open(path) as f:
        content = f.read()
    assert "<!DOCTYPE html>" in content
    assert "<title>" in content
