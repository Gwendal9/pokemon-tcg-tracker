"""Tests transitions d'état CombatState via PollingLoop (Story 3.2).

Tests sur _detect_and_transition() et _compute_next_state() directement.
capture_region_pil et StateDetector sont mockés — pas de vrai screen/MUMU.
"""
import pytest
from unittest.mock import MagicMock, patch

from tracker.capture.detector import CombatState, PollingLoop, StateDetector


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_loop(detector_overrides=None):
    """Construit un PollingLoop avec config mockée, MUMU déjà détecté."""
    config = MagicMock()
    config.get_all.return_value = {
        "mumu_region": {"x": 0, "y": 0, "width": 800, "height": 600}
    }
    detector = MagicMock(spec=StateDetector)
    # Valeurs par défaut : tout False
    detector.is_pre_queue_ranked.return_value = False
    detector.is_in_combat.return_value = False
    detector.is_end_screen.return_value = False
    if detector_overrides:
        for attr, val in detector_overrides.items():
            getattr(detector, attr).return_value = val

    loop = PollingLoop(config=config, detector=detector)
    loop._mumu_detected = True  # MUMU déjà détecté pour tester les transitions
    return loop, detector


FAKE_IMG = MagicMock()


# ---------------------------------------------------------------------------
# StateDetector — valeurs par défaut (stubs)
# ---------------------------------------------------------------------------

def test_state_detector_defaults_false():
    d = StateDetector()
    img = MagicMock()
    assert d.is_pre_queue_ranked(img) is False
    assert d.is_in_combat(img) is False
    assert d.is_end_screen(img) is False


# ---------------------------------------------------------------------------
# _compute_next_state — transitions
# ---------------------------------------------------------------------------

def test_idle_to_pre_queue():
    loop, det = make_loop()
    det.is_pre_queue_ranked.return_value = True
    result = loop._compute_next_state(CombatState.IDLE, FAKE_IMG)
    assert result == CombatState.PRE_QUEUE


def test_idle_stays_idle_when_not_pre_queue():
    loop, det = make_loop()
    result = loop._compute_next_state(CombatState.IDLE, FAKE_IMG)
    assert result == CombatState.IDLE


def test_pre_queue_to_in_combat():
    loop, det = make_loop()
    det.is_in_combat.return_value = True
    result = loop._compute_next_state(CombatState.PRE_QUEUE, FAKE_IMG)
    assert result == CombatState.IN_COMBAT


def test_pre_queue_to_idle_when_not_ranked():
    """Quitter la queue ranked → retour IDLE (AC5)."""
    loop, det = make_loop()
    det.is_pre_queue_ranked.return_value = False
    det.is_in_combat.return_value = False
    result = loop._compute_next_state(CombatState.PRE_QUEUE, FAKE_IMG)
    assert result == CombatState.IDLE


def test_in_combat_to_end_screen():
    loop, det = make_loop()
    det.is_end_screen.return_value = True
    result = loop._compute_next_state(CombatState.IN_COMBAT, FAKE_IMG)
    assert result == CombatState.END_SCREEN


def test_in_combat_stays_when_no_end_screen():
    loop, det = make_loop()
    result = loop._compute_next_state(CombatState.IN_COMBAT, FAKE_IMG)
    assert result == CombatState.IN_COMBAT


def test_end_screen_to_idle():
    loop, det = make_loop()
    det.is_end_screen.return_value = False
    result = loop._compute_next_state(CombatState.END_SCREEN, FAKE_IMG)
    assert result == CombatState.IDLE


def test_end_screen_stays_while_visible():
    loop, det = make_loop()
    det.is_end_screen.return_value = True
    result = loop._compute_next_state(CombatState.END_SCREEN, FAKE_IMG)
    assert result == CombatState.END_SCREEN


# ---------------------------------------------------------------------------
# _detect_and_transition — intégration avec capture
# ---------------------------------------------------------------------------

@patch("tracker.capture.detector.capture_region_pil", return_value=FAKE_IMG)
def test_detect_and_transition_updates_state(mock_cap):
    loop, det = make_loop()
    det.is_pre_queue_ranked.return_value = True
    loop._detect_and_transition()
    assert loop.state == CombatState.PRE_QUEUE


@patch("tracker.capture.detector.capture_region_pil", return_value=None)
def test_detect_and_transition_skips_on_capture_failure(mock_cap):
    loop, det = make_loop()
    det.is_pre_queue_ranked.return_value = True
    loop._detect_and_transition()
    assert loop.state == CombatState.IDLE  # pas de transition sans image


@patch("tracker.capture.detector.capture_region_pil", return_value=FAKE_IMG)
def test_detect_and_transition_calls_on_state_changed(mock_cap):
    loop, det = make_loop()
    det.is_pre_queue_ranked.return_value = True
    changes = []
    loop.set_callbacks(on_state_changed=lambda prev, nxt: changes.append((prev, nxt)))
    loop._detect_and_transition()
    assert changes == [(CombatState.IDLE, CombatState.PRE_QUEUE)]


@patch("tracker.capture.detector.capture_region_pil", return_value=FAKE_IMG)
def test_detect_and_transition_no_callback_when_no_change(mock_cap):
    loop, det = make_loop()
    changes = []
    loop.set_callbacks(on_state_changed=lambda p, n: changes.append((p, n)))
    loop._detect_and_transition()  # tout False → reste IDLE
    assert changes == []


@patch("tracker.capture.detector.capture_region_pil", return_value=FAKE_IMG)
def test_detect_and_transition_exception_in_detector_does_not_crash(mock_cap):
    loop, det = make_loop()
    det.is_pre_queue_ranked.side_effect = RuntimeError("detector crash")
    loop._detect_and_transition()  # ne doit pas lever
    assert loop.state == CombatState.IDLE


def test_detect_and_transition_skips_when_no_region():
    """Sans région configurée, aucune capture ni transition."""
    config = MagicMock()
    config.get_all.return_value = {"mumu_region": None}
    detector = MagicMock(spec=StateDetector)
    loop = PollingLoop(config=config, detector=detector)
    loop._mumu_detected = True
    loop._detect_and_transition()
    detector.is_pre_queue_ranked.assert_not_called()


# ---------------------------------------------------------------------------
# AC5 — Combat non-ranked
# ---------------------------------------------------------------------------

@patch("tracker.capture.detector.capture_region_pil", return_value=FAKE_IMG)
def test_non_ranked_does_not_trigger_pre_queue(mock_cap):
    """is_pre_queue_ranked=False → état reste IDLE (AC5)."""
    loop, det = make_loop()
    det.is_pre_queue_ranked.return_value = False
    loop._detect_and_transition()
    assert loop.state == CombatState.IDLE
