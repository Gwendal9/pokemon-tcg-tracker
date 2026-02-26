"""tests/test_updater.py — Tests unitaires pour tracker.updater et tracker.version."""
import json
from io import BytesIO
from unittest.mock import MagicMock, patch

from tracker.version import __version__
from tracker.updater import _is_newer, check_for_update


# ---------------------------------------------------------------------------
# _is_newer
# ---------------------------------------------------------------------------

class TestIsNewer:
    def test_newer_patch(self):
        assert _is_newer("0.1.1", "0.1.0") is True

    def test_newer_minor(self):
        assert _is_newer("0.2.0", "0.1.0") is True

    def test_newer_major(self):
        assert _is_newer("1.0.0", "0.9.9") is True

    def test_same_version(self):
        assert _is_newer("0.1.0", "0.1.0") is False

    def test_older_version(self):
        assert _is_newer("0.0.9", "0.1.0") is False

    def test_with_v_prefix(self):
        assert _is_newer("v0.2.0", "0.1.0") is True

    def test_invalid_version(self):
        # Should not raise, return False
        assert _is_newer("bad", "0.1.0") is False


# ---------------------------------------------------------------------------
# check_for_update
# ---------------------------------------------------------------------------

def _mock_response(tag_name: str, html_url: str = "https://github.com/x"):
    payload = json.dumps({"tag_name": tag_name, "html_url": html_url}).encode()
    mock_resp = MagicMock()
    mock_resp.read.return_value = payload
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


class TestCheckForUpdate:
    def test_returns_none_when_up_to_date(self):
        with patch("urllib.request.urlopen", return_value=_mock_response("v0.1.0")):
            result = check_for_update("0.1.0")
        assert result is None

    def test_returns_dict_when_newer(self):
        with patch("urllib.request.urlopen",
                   return_value=_mock_response("v0.2.0", "https://github.com/rel")):
            result = check_for_update("0.1.0")
        assert result is not None
        assert result["version"] == "0.2.0"
        assert result["url"] == "https://github.com/rel"

    def test_returns_none_on_network_error(self):
        with patch("urllib.request.urlopen", side_effect=OSError("timeout")):
            result = check_for_update("0.1.0")
        assert result is None

    def test_returns_none_when_older_release(self):
        with patch("urllib.request.urlopen", return_value=_mock_response("v0.0.9")):
            result = check_for_update("0.1.0")
        assert result is None

    def test_returns_none_on_empty_tag(self):
        with patch("urllib.request.urlopen",
                   return_value=_mock_response("", "https://github.com/rel")):
            result = check_for_update("0.1.0")
        assert result is None


# ---------------------------------------------------------------------------
# version
# ---------------------------------------------------------------------------

class TestVersion:
    def test_version_is_string(self):
        assert isinstance(__version__, str)

    def test_version_semver_format(self):
        parts = __version__.split(".")
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)
