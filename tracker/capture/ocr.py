"""tracker/capture/ocr.py — Pipeline OCR EasyOCR pour l'extraction des données de combat.

OcrPipeline :
- extract_end_screen_data(img) → {result, opponent, first_player, captured_at, raw_ocr_data}
- extract_deck_from_prequeue(img, active_deck_id) → deck_id ou fallback

Règles critiques :
- Toujours retourner "?" pour les champs non reconnus — jamais None ni chaîne vide
- EasyOCR initialisé une seule fois (singleton injecté depuis main.py)
- Imports easyocr et numpy en lazy (lourds, Windows-only en pratique)
"""
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Seuil de confiance minimal pour accepter un résultat OCR
CONFIDENCE_THRESHOLD = 0.5


class OcrPipeline:
    """Pipeline EasyOCR pour extraire les données de match depuis des captures d'écran.

    Usage :
        ocr = OcrPipeline(reader=easyocr.Reader(['en'], gpu=False))
        data = ocr.extract_end_screen_data(end_screen_img)
        # data = {"result": "W", "opponent": "?", "first_player": "?", ...}
    """

    def __init__(self, reader=None):
        """
        Args:
            reader: Instance easyocr.Reader pré-initialisée (injectée depuis main.py).
                    Si None, sera initialisée au premier appel via _ensure_reader().
        """
        self._reader = reader

    def set_reader(self, reader) -> None:
        """Injecte un reader EasyOCR (utilisé depuis main.py ou les tests)."""
        self._reader = reader

    # ------------------------------------------------------------------
    # Méthodes publiques
    # ------------------------------------------------------------------

    def extract_end_screen_data(self, img) -> dict:
        """Extrait les données de fin de combat depuis l'écran de résultat.

        Args:
            img: PIL Image de la région configurée au moment de l'écran de fin.

        Returns:
            dict avec clés : result, opponent, first_player, captured_at, raw_ocr_data.
            Tous les champs extraits ont une valeur (jamais None — "?" si incertain).
        """
        raw_results = []
        try:
            raw_results = self._read_text(img)
        except Exception as e:
            logger.error("OCR read error: %s", e)

        raw_json = json.dumps(
            [(text, float(conf)) for (_, text, conf) in raw_results],
            ensure_ascii=False,
        )

        return {
            "result": self._parse_result(raw_results),
            "opponent": self._parse_opponent(raw_results),
            "first_player": self._parse_first_player(raw_results),
            "captured_at": datetime.now().isoformat(),
            "raw_ocr_data": raw_json,
        }

    def extract_deck_from_prequeue(self, img, active_deck_id=None) -> int | None:
        """Extrait le deck joué depuis l'icône visible à l'écran pré-queue.

        Fallback sur active_deck_id si l'identification OCR échoue.

        Args:
            img: PIL Image de la région pré-queue (peut être None si non capturé).
            active_deck_id: deck_id configuré manuellement en fallback.

        Returns:
            deck_id (int) ou None si aucun deck identifiable.

        TODO: Implémenter la détection visuelle de l'icône de deck une fois
              les patterns Pokemon TCG Pocket calibrés sur Windows.
        """
        logger.debug(
            "extract_deck_from_prequeue: fallback active_deck_id=%s", active_deck_id
        )
        return active_deck_id

    # ------------------------------------------------------------------
    # Méthodes internes — EasyOCR
    # ------------------------------------------------------------------

    def _ensure_reader(self) -> None:
        """Initialise le reader EasyOCR si pas encore fait (lazy — import lourd)."""
        if self._reader is None:
            import easyocr  # noqa: PLC0415 — import lazy intentionnel (~200MB)
            self._reader = easyocr.Reader(["en"], gpu=False)
            logger.info("EasyOCR Reader initialisé")

    def _read_text(self, img) -> list:
        """Lance EasyOCR sur l'image. Retourne [(bbox, text, confidence)]."""
        import numpy as np  # noqa: PLC0415 — import lazy
        self._ensure_reader()
        return self._reader.readtext(np.array(img))

    # ------------------------------------------------------------------
    # Méthodes internes — parsing des résultats OCR
    # ------------------------------------------------------------------

    def _parse_result(self, ocr_results) -> str:
        """Extrait le résultat V/D depuis les textes OCR.

        Cherche les textes "WIN" ou "LOSE" avec confiance ≥ CONFIDENCE_THRESHOLD.
        Retourne "W", "L", ou "?" si non reconnu.

        TODO: Calibrer avec les textes exacts de l'écran de fin de Pokemon TCG Pocket.
        """
        for (_, text, conf) in ocr_results:
            if conf < CONFIDENCE_THRESHOLD:
                continue
            upper = text.upper().strip()
            if upper in ("WIN", "WIN!", "YOU WIN", "YOU WIN!", "VICTORY"):
                return "W"
            if upper in ("LOSE", "LOSE!", "YOU LOSE", "YOU LOSE!", "DEFEAT"):
                return "L"
        return "?"

    def _parse_opponent(self, ocr_results) -> str:
        """Extrait le nom de l'adversaire depuis les textes OCR.

        TODO: Calibrer selon la position du nom adversaire dans l'UI de fin de combat.
              La position relative dans l'image est spécifique à Pokemon TCG Pocket.
        """
        return "?"

    def _parse_first_player(self, ocr_results) -> str:
        """Extrait qui a commencé en premier (me/opponent) depuis les textes OCR.

        TODO: Calibrer selon les indicateurs visuels "You go first" / "Opponent goes first"
              dans l'UI de Pokemon TCG Pocket.
        """
        return "?"
