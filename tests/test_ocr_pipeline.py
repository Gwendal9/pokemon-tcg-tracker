"""Tests OcrPipeline (Story 3.3).

EasyOCR reader mocké — pas d'import lourd ni de GPU.
"""
import json
from unittest.mock import MagicMock

import pytest

from tracker.capture.ocr import OcrPipeline


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_ocr(ocr_results):
    """OcrPipeline avec un reader mock retournant ocr_results."""
    mock_reader = MagicMock()
    mock_reader.readtext.return_value = ocr_results
    return OcrPipeline(reader=mock_reader)


FAKE_IMG = MagicMock()


# ---------------------------------------------------------------------------
# extract_end_screen_data — résultat
# ---------------------------------------------------------------------------

def test_win_result():
    ocr = make_ocr([(None, "WIN!", 0.95)])
    result = ocr.extract_end_screen_data(FAKE_IMG)
    assert result["result"] == "W"


def test_lose_result():
    ocr = make_ocr([(None, "LOSE!", 0.95)])
    result = ocr.extract_end_screen_data(FAKE_IMG)
    assert result["result"] == "L"


def test_unknown_text_returns_question_mark():
    ocr = make_ocr([(None, "SOMETHING ELSE", 0.99)])
    result = ocr.extract_end_screen_data(FAKE_IMG)
    assert result["result"] == "?"


def test_low_confidence_returns_question_mark():
    """Confiance < 0.5 → '?' même si le texte ressemble à 'WIN'."""
    ocr = make_ocr([(None, "WIN", 0.3)])
    result = ocr.extract_end_screen_data(FAKE_IMG)
    assert result["result"] == "?"


def test_empty_ocr_returns_question_mark():
    ocr = make_ocr([])
    result = ocr.extract_end_screen_data(FAKE_IMG)
    assert result["result"] == "?"


# ---------------------------------------------------------------------------
# extract_end_screen_data — champs non implémentés = "?"
# ---------------------------------------------------------------------------

def test_opponent_is_question_mark():
    ocr = make_ocr([])
    result = ocr.extract_end_screen_data(FAKE_IMG)
    assert result["opponent"] == "?"


def test_first_player_is_question_mark():
    ocr = make_ocr([])
    result = ocr.extract_end_screen_data(FAKE_IMG)
    assert result["first_player"] == "?"


def test_no_none_fields():
    """Aucun champ ne doit être None ni chaîne vide (AC3)."""
    ocr = make_ocr([])
    result = ocr.extract_end_screen_data(FAKE_IMG)
    for key, val in result.items():
        assert val is not None, f"{key} est None"
        assert val != "", f"{key} est une chaîne vide"


# ---------------------------------------------------------------------------
# extract_end_screen_data — raw_ocr_data (AC5)
# ---------------------------------------------------------------------------

def test_raw_ocr_data_is_valid_json():
    ocr = make_ocr([(None, "WIN!", 0.95)])
    result = ocr.extract_end_screen_data(FAKE_IMG)
    parsed = json.loads(result["raw_ocr_data"])
    assert isinstance(parsed, list)


def test_raw_ocr_data_contains_text_and_confidence():
    ocr = make_ocr([(None, "WIN!", 0.95)])
    result = ocr.extract_end_screen_data(FAKE_IMG)
    parsed = json.loads(result["raw_ocr_data"])
    assert parsed[0][0] == "WIN!"
    assert abs(parsed[0][1] - 0.95) < 1e-6


# ---------------------------------------------------------------------------
# extract_end_screen_data — captured_at (AC2 / FR8)
# ---------------------------------------------------------------------------

def test_captured_at_is_iso8601():
    from datetime import datetime
    ocr = make_ocr([])
    result = ocr.extract_end_screen_data(FAKE_IMG)
    # datetime.fromisoformat lève ValueError si format invalide
    dt = datetime.fromisoformat(result["captured_at"])
    assert dt is not None


# ---------------------------------------------------------------------------
# extract_end_screen_data — exception EasyOCR (robustesse)
# ---------------------------------------------------------------------------

def test_easyocr_exception_returns_fallback_dict():
    """Si EasyOCR lève une exception, retourner un dict avec '?' — pas de crash."""
    mock_reader = MagicMock()
    mock_reader.readtext.side_effect = RuntimeError("EasyOCR crash")
    ocr = OcrPipeline(reader=mock_reader)
    result = ocr.extract_end_screen_data(FAKE_IMG)
    assert result["result"] == "?"
    assert result["opponent"] == "?"
    assert result["first_player"] == "?"
    assert "captured_at" in result
    assert "raw_ocr_data" in result


# ---------------------------------------------------------------------------
# extract_deck_from_prequeue — fallback active_deck_id (AC4)
# ---------------------------------------------------------------------------

def test_extract_deck_returns_active_deck_id():
    ocr = OcrPipeline()
    assert ocr.extract_deck_from_prequeue(FAKE_IMG, active_deck_id=42) == 42


def test_extract_deck_returns_none_when_no_fallback():
    ocr = OcrPipeline()
    assert ocr.extract_deck_from_prequeue(FAKE_IMG) is None


def test_extract_deck_with_none_img():
    ocr = OcrPipeline()
    assert ocr.extract_deck_from_prequeue(None, active_deck_id=7) == 7


# ---------------------------------------------------------------------------
# _parse_result — variantes texte
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text", ["WIN", "WIN!", "YOU WIN", "YOU WIN!", "VICTORY"])
def test_parse_result_win_variants(text):
    ocr = make_ocr([(None, text, 0.9)])
    result = ocr.extract_end_screen_data(FAKE_IMG)
    assert result["result"] == "W"


@pytest.mark.parametrize("text", ["LOSE", "LOSE!", "YOU LOSE", "YOU LOSE!", "DEFEAT"])
def test_parse_result_lose_variants(text):
    ocr = make_ocr([(None, text, 0.9)])
    result = ocr.extract_end_screen_data(FAKE_IMG)
    assert result["result"] == "L"
