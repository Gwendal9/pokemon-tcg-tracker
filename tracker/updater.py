"""tracker/updater.py — Vérification de mise à jour via GitHub Releases API."""
import json
import logging
import urllib.request

logger = logging.getLogger(__name__)

GITHUB_RELEASES_URL = (
    "https://api.github.com/repos/Gwendal9/pokemon-tcg-tracker/releases/latest"
)


def _is_newer(latest: str, current: str) -> bool:
    """Compare deux versions semver 'X.Y.Z'. Retourne True si latest > current."""
    try:
        def parse(v):
            return tuple(int(x) for x in v.lstrip("v").split(".")[:3])
        return parse(latest) > parse(current)
    except Exception:
        return False


def check_for_update(current_version: str):
    """Interroge GitHub Releases API.

    Retourne {"version": "X.Y.Z", "url": "..."} si une version plus récente
    est disponible, None sinon.
    """
    try:
        req = urllib.request.Request(
            GITHUB_RELEASES_URL,
            headers={"User-Agent": "pokemon-tcg-tracker-updater"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
        tag = data.get("tag_name", "").lstrip("v")
        url = data.get("html_url", "")
        if tag and url and _is_newer(tag, current_version):
            return {"version": tag, "url": url}
    except Exception as e:
        logger.debug("check_for_update: %s", e)
    return None
