"""tracker/capture/ocr.py — Pipeline OCR EasyOCR pour l'extraction des données de combat.

OcrPipeline :
- extract_end_screen_data(img) → {result, opponent, first_player, turns_played,
                                   player_points, opponent_points, captured_at, raw_ocr_data}
- extract_deck_from_prequeue(img, active_deck_id) → deck_id ou fallback

Règles critiques :
- Toujours retourner "?" pour les champs texte non reconnus — jamais None ni chaîne vide
- EasyOCR initialisé une seule fois (singleton injecté depuis main.py)
- Imports easyocr et numpy en lazy (lourds, Windows-only en pratique)
"""
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD = 0.5


class OcrPipeline:
    """Pipeline EasyOCR pour extraire les données de match depuis des captures d'écran."""

    def __init__(self, reader=None):
        self._reader = reader

    def set_reader(self, reader) -> None:
        self._reader = reader

    # ------------------------------------------------------------------
    # Méthodes publiques
    # ------------------------------------------------------------------

    # Zones de lecture (fractions de l'image)
    # TOP    : bande haute — "Victoire !" / "Défaite..." / nom adversaire
    # BOTTOM : tableau stats (après clic, pas de carte)
    # PREQUEUE_TYPE : "Match aléatoire" / "Match classé" etc.
    # PREQUEUE_DECK : nom du deck sous la vignette
    _ZONE_TOP           = (0.0, 0.0,  1.0,  0.35)
    _ZONE_BOTTOM        = (0.0, 0.62, 0.85, 0.95)
    _ZONE_PREQUEUE_TYPE = (0.0, 0.03, 1.0,  0.13)

    def extract_end_screen_data(self, img) -> dict:
        """Extrait les données de fin de combat depuis l'écran de résultat."""
        w, h = img.size

        def crop(zone):
            return img.crop((int(zone[0]*w), int(zone[1]*h),
                             int(zone[2]*w), int(zone[3]*h)))

        top_img    = crop(self._ZONE_TOP)
        bottom_img = crop(self._ZONE_BOTTOM)

        # Upscale 2x le crop bottom pour améliorer la détection des petits textes
        bottom_img_up = bottom_img.resize(
            (bottom_img.width * 2, bottom_img.height * 2),
        )

        top_results = bottom_results = []
        try:
            top_results    = self._read_text(top_img)
            bottom_results = self._read_text(bottom_img_up)
        except Exception as e:
            logger.error("OCR read error: %s", e)

        raw_json = json.dumps(
            [("TOP:" + text, float(conf)) for (_, text, conf) in top_results] +
            [("BOT:" + text, float(conf)) for (_, text, conf) in bottom_results],
            ensure_ascii=False,
        )

        # Tolérance doublée car coordonnées upscalées 2x
        rows = self._group_into_rows(bottom_results, y_tolerance=30)
        _upscale = 2
        logger.info("OCR top: %s", [(t, round(c,2)) for (_, t, c) in top_results])
        logger.info("OCR bottom rows: %s", [[(t, round(c,2)) for (_, t, c) in row] for row in rows])

        return {
            "result":          self._parse_result(top_results),
            "opponent":        self._parse_opponent(top_results),
            "first_player":    self._parse_first_player(rows),
            "turns_played":    self._parse_turns(rows, bottom_results, bottom_img, _upscale),
            "player_points":   self._count_points_circles(rows, "vos points", bottom_img, _upscale),
            "opponent_points": self._count_points_circles(rows, "points adversaire", bottom_img, _upscale),
            "damage_dealt":    self._parse_number_after(rows, ["dégâts inflig", "degats inflig"]),
            "captured_at":     datetime.now().isoformat(),
            "raw_ocr_data":    raw_json,
        }

    # Correspondance fichier → nom French affiché dans l'UI
    _ENERGY_ICON_FILES = {
        "fire":      "Feu",
        "water":     "Eau",
        "grass":     "Plante",
        "lightning": "Électrique",
        "psychic":   "Psy",
        "fighting":  "Combat",
        "metal":     "Acier",
        "darkness":  "Obscurité",
        "colorless": "Incolore",
        "dragon":    "Dragon",
    }

    def extract_opponent_energy(self, img) -> str:
        """Détecte le type d'énergie de l'adversaire depuis l'écran de combat.

        Analyse la zone de génération d'énergie adverse (haut-gauche du plateau,
        x=[0%,13%], y=[22%,55%]) par matching d'histogramme de teinte contre les
        icônes de référence dans ui/vendor/energy/.

        L'histogramme est invariant à la taille du token — pas besoin de connaître
        l'échelle exacte de l'icône dans le jeu.

        Returns:
            Type d'énergie détecté (ex: "Feu", "Acier") ou "?" si non détecté.
        """
        import numpy as np  # noqa: PLC0415
        try:
            # Chargement lazy des signatures de référence
            if not hasattr(self, "_energy_sigs"):
                self._energy_sigs = self._load_energy_signatures()

            w, h = img.size
            x1, x2 = int(0.10 * w), int(0.18 * w)
            y1, y2 = int(0.10 * h), int(0.16 * h)
            zone = img.convert("RGB").crop((x1, y1, x2, y2))

            sig = self._compute_hue_hist(np.asarray(zone, dtype=float) / 255.)

            if not self._energy_sigs:
                # Pas de références chargées → impossible de matcher
                self._save_opponent_energy_debug(img, x1, y1, x2, y2, "?")
                return "?"

            # Matching par intersection d'histogramme (plus haute intersection = meilleur match)
            best_energy = "?"
            best_score  = 0.0
            scores = {}
            for energy_type, ref_sig in self._energy_sigs.items():
                score = float(np.minimum(sig["hist"], ref_sig["hist"]).sum())
                scores[energy_type] = round(score, 3)
                if score > best_score:
                    best_score  = score
                    best_energy = energy_type

            # Seuil minimal : si aucun type ne ressemble assez, on ne retourne pas de résultat
            MIN_SCORE = 0.12
            result = best_energy if best_score >= MIN_SCORE else "?"
            self._last_energy_score = best_score if result != "?" else 0.0
            logger.info(
                "extract_opponent_energy: result=%s score=%.3f | %s",
                result, best_score, scores,
            )
            self._save_opponent_energy_debug(img, x1, y1, x2, y2, result)
            return result
        except Exception as e:
            logger.error("extract_opponent_energy: %s", e)
            return "?"

    def _load_energy_signatures(self) -> dict:
        """Charge les signatures de teinte des icônes d'énergie depuis ui/vendor/energy/."""
        import os
        import numpy as np  # noqa: PLC0415
        from PIL import Image  # noqa: PLC0415

        base = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "..", "ui", "vendor", "energy")
        )
        sigs = {}
        for fname, energy_type in self._ENERGY_ICON_FILES.items():
            path = os.path.join(base, f"{fname}.png")
            try:
                icon = Image.open(path)
                arr = np.asarray(icon.convert("RGBA"), dtype=float) / 255.
                # Utiliser le canal alpha comme masque (ignorer fond transparent)
                alpha_mask = arr[:, :, 3] > 0.5
                rgb = arr[:, :, :3]
                sigs[energy_type] = self._compute_hue_hist(rgb, alpha_mask=alpha_mask)
            except Exception as e:
                logger.warning("_load_energy_signatures: %s — %s", path, e)
        logger.info("Signatures énergie chargées (%d): %s", len(sigs), list(sigs.keys()))
        return sigs

    def _compute_hue_hist(self, rgb_arr, alpha_mask=None) -> dict:
        """Calcule l'histogramme de teinte normalisé d'un tableau RGB [0,1].

        Args:
            rgb_arr:    numpy array H×W×3, valeurs [0,1]
            alpha_mask: masque booléen H×W (None = tout inclus)

        Returns:
            {"hist": ndarray(36,), "gray_ratio": float, "dark_ratio": float}
        """
        import numpy as np  # noqa: PLC0415

        r, g, b = rgb_arr[:, :, 0], rgb_arr[:, :, 1], rgb_arr[:, :, 2]
        mx    = np.maximum(np.maximum(r, g), b)
        mn    = np.minimum(np.minimum(r, g), b)
        delta = mx - mn
        sat   = np.where(mx > 0.15, delta / mx, 0.)
        val   = mx

        base = alpha_mask if alpha_mask is not None else np.ones(r.shape, dtype=bool)
        n_valid = base.sum()
        if n_valid == 0:
            return {"hist": np.zeros(36), "gray_ratio": 0., "dark_ratio": 0.}

        dark_ratio = float(((val < 0.25) & base).sum()) / n_valid
        gray_ratio = float(((sat < 0.20) & (val >= 0.30) & base).sum()) / n_valid

        color_mask = (sat > 0.30) & (val > 0.20) & base
        if color_mask.sum() < 5:
            return {"hist": np.zeros(36), "gray_ratio": gray_ratio, "dark_ratio": dark_ratio}

        h_map = np.zeros_like(r)
        mr  = (delta > 0) & (mx == r)
        mg  = (delta > 0) & (mx == g)
        mb_ = (delta > 0) & (mx == b)
        h_map[mr]  = ((g[mr]  - b[mr])  / delta[mr])  % 6
        h_map[mg]  = (b[mg]   - r[mg])  / delta[mg]   + 2
        h_map[mb_] = (r[mb_]  - g[mb_]) / delta[mb_]  + 4
        hue_deg = h_map / 6. * 360.

        hist, _ = np.histogram(hue_deg[color_mask], bins=36, range=(0., 360.))
        hist_norm = hist.astype(float) / (hist.sum() + 1e-9)
        return {"hist": hist_norm, "gray_ratio": gray_ratio, "dark_ratio": dark_ratio}

    def _save_opponent_energy_debug(self, img, x1, y1, x2, y2, energy: str) -> None:
        """Sauvegarde une image debug avec la zone d'analyse surlignée."""
        try:
            from PIL import ImageDraw, ImageFont  # noqa: PLC0415
            from tracker.paths import get_data_dir  # noqa: PLC0415
            dbg = img.convert("RGB").copy()
            draw = ImageDraw.Draw(dbg, "RGBA")
            draw.rectangle((x1, y1, x2, y2), outline=(255, 165, 0, 255), width=3)
            draw.rectangle((x1, y1, x2, y2), fill=(255, 165, 0, 40))
            label = f"opponent_energy={energy}  zone=({x1},{y1})-({x2},{y2})"
            draw.rectangle((0, 0, dbg.width, 22), fill=(0, 0, 0, 180))
            try:
                font = ImageFont.load_default()
            except Exception:
                font = None
            draw.text((4, 4), label, fill=(255, 255, 255), font=font)
            # Aussi sauvegarder le crop seul pour faciliter l'inspection
            crop = img.convert("RGB").crop((x1, y1, x2, y2))
            data_dir = get_data_dir()
            dbg.save(data_dir + "/debug_opponent_energy.png")
            crop.save(data_dir + "/debug_opponent_energy_crop.png")
        except Exception as _de:
            logger.debug("_save_opponent_energy_debug: %s", _de)

    # Mots-clés qui indiquent une carte Dresseur/Objet — à ignorer
    _TRAINER_KEYWORDS = {
        "dresseur", "objet", "supporter", "ticket", "energie", "énergie",
        "item", "pokemon tool", "outil",
    }

    def extract_active_opponent_pokemon(self, img) -> str | None:
        """Extrait le nom du Pokemon actif adverse en scannant 3 zones.

        Zone 1 (prioritaire) — animation attaque : y=[76%,84%], x=[5%,95%]
          Quand le Pokemon adverse attaque, son nom apparait en grand en bas.
        Zone 2 — titre carte active normale : y=[19%,27%], x=[14%,60%]
          Titre de la carte adverse visible en jeu normal (haut gauche du plateau).
        Zone 3 — animation pose carte : y=[31%,42%], x=[6%,66%]
          Quand une carte Pokemon est posée, son nom apparait en grand au centre.

        Retourne le premier nom plausible trouvé (conf >= 0.40, longueur >= 3,
        pas un mot-clé Dresseur/Objet).
        """
        w, h = img.size
        img_rgb = img.convert("RGB")

        zones = [
            # (x0_frac, y0_frac, x1_frac, y1_frac, upscale, label)
            # Zone principale : titre de la carte active adverse (moitié droite, titre sous le header)
            # Ogerpon Masque Turquoise ex → y=[27%,33%], x=[40%,88%]
            (0.38, 0.26, 0.88, 0.34, 5, "active_opp"),
            # Zone secondaire : légèrement plus haute pour les cartes plus petites
            (0.35, 0.21, 0.90, 0.30, 4, "active_opp_hi"),
        ]

        for (x0, y0, x1, y1, scale, label) in zones:
            crop = img_rgb.crop((int(x0 * w), int(y0 * h), int(x1 * w), int(y1 * h)))
            crop_up = crop.resize((crop.width * scale, crop.height * scale))
            try:
                results = self._read_text(crop_up)
                for (_, text, conf) in results:
                    text = text.strip()
                    if conf < 0.40 or len(text) < 3 or text.isdigit():
                        continue
                    norm_text = text.lower()
                    if any(kw in norm_text for kw in self._TRAINER_KEYWORDS):
                        continue
                    logger.debug("extract_active_opponent_pokemon [%s]: %s (%.2f)", label, text, conf)
                    return text
            except Exception as e:
                logger.error("extract_active_opponent_pokemon [%s]: %s", label, e)

        return None

    def extract_prequeue_data(self, img) -> dict:
        """Extrait le type de match, le nom du deck et le type d'énergie depuis l'écran de pré-combat.

        Détection position-agnostique : cherche la bande colorée du cadre deck
        sur toute la hauteur utile de l'image, indépendamment du layout.
        """
        w, h = img.size

        # Type de match depuis la bannière haute
        type_results = []
        try:
            type_crop = img.crop((0, int(0.03*h), w, int(0.13*h)))
            type_results = self._read_text(type_crop)
        except Exception as e:
            logger.error("OCR prequeue type error: %s", e)
        match_type = self._parse_match_type(type_results)

        # Localisation libre du cadre deck
        strip = self._find_deck_card_strip(img)
        energy_type = strip["energy_type"] if strip else "?"

        # Nom du deck : zone fixe y=[64%, 85%]
        # Le nom personnalisé est toujours dans cette zone dans les deux layouts :
        # - Standard    : nom à y≈66-73% (juste sous la carte)
        # - "Règles"    : nom à y≈74-84% (sous la miniature)
        # "C'est parti !" est filtré par blacklist si présent en bas de zone.
        deck_name = "?"
        if strip:
            name_y1 = int(0.64 * h)
            name_y2 = int(0.76 * h)  # 0.76 : exclut le bouton "C'est parti !" (y≈78-84%)
            if name_y2 > name_y1:
                name_crop = img.crop((int(0.05 * w), name_y1, int(0.95 * w), name_y2))
                try:
                    deck_results = self._read_text(name_crop)
                    deck_name = self._parse_prequeue_deck_name(deck_results)
                except Exception as e:
                    logger.error("OCR deck name error: %s", e)

        # Rang et points — toujours tenté (permet aussi de déduire match_type=classé)
        rank_name = None
        rank_points = None
        try:
            rank_crop = img.crop((int(0.15 * w), int(0.27 * h), int(0.85 * w), int(0.43 * h)))
            rank_results = self._read_text(rank_crop)
            logger.info("OCR rank raw: %s", [(t, round(c, 2)) for (_, t, c) in rank_results])
            rank_name   = self._parse_rank_name(rank_results)
            rank_points = self._parse_rank_points(rank_results)
            # Si la zone rang contient "rang" ou "points", c'est un match classé
            if match_type == "?":
                rank_text = " ".join(t for (_, t, c) in rank_results if c >= 0.25).lower()
                if "rang" in rank_text or "points" in rank_text:
                    match_type = "classé"
                    logger.info("match_type deduit classé depuis zone rang")
        except Exception as e:
            logger.error("OCR rank info error: %s", e)

        logger.info(
            "Prequeue: type=%s deck=%s energy=%s rank=%s pts=%s strip=%s",
            match_type, deck_name, energy_type, rank_name, rank_points,
            {k: strip[k] for k in ("y_top", "y_bot", "hue_deg")} if strip else None,
        )

        # Sauvegarde image debug avec toutes les zones surlignées
        try:
            from PIL import ImageDraw, ImageFont  # noqa: PLC0415
            from tracker.paths import get_data_dir  # noqa: PLC0415
            dbg = img.convert("RGB").copy()
            draw = ImageDraw.Draw(dbg, "RGBA")
            iw, ih = dbg.size
            # Rouge : bande énergie deck
            if strip:
                yt, yb = strip["y_top"], strip["y_bot"]
                draw.rectangle((0, yt, iw, yb), outline=(255, 0, 0, 255), width=3)
                draw.rectangle((0, yt, iw, yb), fill=(255, 0, 0, 60))
            # Vert : zone nom du deck
            draw.rectangle(
                (int(0.05*iw), int(0.64*ih), int(0.95*iw), int(0.76*ih)),
                outline=(0, 200, 0, 255), width=2,
            )
            # Bleu : zone rang — toujours affichée pour debug, remplie si classé
            _rank_x1, _rank_x2 = int(0.15*iw), int(0.85*iw)
            _rank_y1, _rank_y2 = int(0.27*ih), int(0.43*ih)
            draw.rectangle(
                (_rank_x1, _rank_y1, _rank_x2, _rank_y2),
                outline=(0, 120, 255, 255), width=2,
            )
            if "class" in (match_type or "").lower():
                draw.rectangle(
                    (_rank_x1, _rank_y1, _rank_x2, _rank_y2),
                    fill=(0, 120, 255, 30),
                )
            label = (
                f"energy={energy_type}  deck={deck_name}  type={match_type}"
                + (f"  rank={rank_name}  pts={rank_points}" if match_type == "classé" else "")
            )
            draw.rectangle((0, 0, iw, 22), fill=(0, 0, 0, 180))
            try:
                font = ImageFont.load_default()
            except Exception:
                font = None
            draw.text((4, 4), label, fill=(255, 255, 255), font=font)
            dbg.save(get_data_dir() + "/debug_prequeue.png")
        except Exception as _de:
            logger.debug("debug_prequeue save: %s", _de)

        return {
            "match_type":  match_type,
            "deck_name":   deck_name,
            "energy_type": energy_type,
            "rank_name":   rank_name,
            "rank_points": rank_points,
        }

    def _find_deck_card_strip(self, img) -> dict | None:
        """Localise la bande colorée du cadre deck indépendamment de sa position.

        Deux layouts possibles :
        - Standard    : une seule bande colorée (en-tête de la carte deck, y≈38-50%).
        - "Règles"    : deux bandes — grande bannière énergie en haut (y≈16-27%)
                        + en-tête de miniature toujours jaune en bas (y≈55-65%).

        Algorithme :
        1. Recherche dans x=[18%,82%] y=[8%,68%].
        2. Détecte TOUTES les bandes saturées (pas seulement la dernière).
        3. Utilise la bande la PLUS HAUTE pour l'énergie — correcte dans les deux layouts
           (dans "Règles", c'est la bannière colorée ; en standard, c'est l'en-tête deck).

        Returns:
            {"y_top", "y_bot", "hue_deg", "energy_type"} en pixels absolus, ou None.
        """
        import numpy as np  # noqa: PLC0415
        try:
            w, h = img.size
            x1, x2 = int(0.18 * w), int(0.82 * w)
            y1, y2 = int(0.08 * h), int(0.68 * h)

            section = np.asarray(img.convert("RGB").crop((x1, y1, x2, y2)), dtype=float)
            sh, sw = section.shape[:2]
            if sh == 0 or sw == 0:
                return None

            r, g, b = section[:,:,0]/255., section[:,:,1]/255., section[:,:,2]/255.
            mx = np.maximum(np.maximum(r, g), b)
            mn = np.minimum(np.minimum(r, g), b)
            row_frac = np.where(mx > 0.15, (mx - mn) / mx, 0.)
            row_frac = (row_frac > 0.40).mean(axis=1)

            SAT_THRESHOLD = 0.12
            MIN_GAP = 8  # lignes de faible saturation pour séparer deux bandes

            # Détecter toutes les bandes saturées contiguës
            bands = []  # [(row_start, row_end), ...]
            in_band = False
            band_start = -1
            last_active = -1

            for i in range(sh):
                if row_frac[i] >= SAT_THRESHOLD:
                    if not in_band:
                        in_band = True
                        band_start = i
                    last_active = i
                elif in_band and (i - last_active) > MIN_GAP:
                    in_band = False
                    if last_active - band_start >= 2:
                        bands.append((band_start, last_active))

            if in_band and band_start >= 0 and last_active - band_start >= 2:
                bands.append((band_start, last_active))

            if not bands:
                return None

            MIN_START = int(0.04 * sh)

            # Stratégie deux zones — priorité zone2 (deck joueur) sur zone1 :
            #
            # Zone 2 — deck du JOUEUR (y≈46-68% abs)
            #   Rows : 55% → fin de section
            #   Prioritaire : en solo, le panneau de règles adverse est en haut
            #   (zone1) et le deck du joueur est en bas (zone2). En prenant zone2
            #   en premier on évite de lire la couleur du deck adverse.
            #   La bande cyan de l'UI (y≈53% section) est évitée car zone2 démarre
            #   à 55%.
            #
            # Zone 1 — fallback uniquement si zone2 vide
            #   Rows : MIN_START → 38% de section
            #   Critère : bande haute (≥ 20px) = grande bannière colorée
            zone1_end   = int(0.38 * sh)
            zone2_start = int(0.55 * sh)

            z2_bands = [(bs, be) for bs, be in bands
                        if bs >= zone2_start and (be - bs) >= 5]
            z1_bands = [(bs, be) for bs, be in bands
                        if bs >= MIN_START and be <= zone1_end and (be - bs) >= 20]

            if z2_bands:
                # Prendre la bande la plus haute (hauteur max) en zone2 :
                # évite les petits artefacts de bordure au profit du vrai bloc deck
                top_band_start, top_band_end = max(z2_bands, key=lambda b: b[1] - b[0])
            elif z1_bands:
                top_band_start, top_band_end = z1_bands[0]
            else:
                return None
            strip = section[top_band_start:top_band_end + 1]

            sr, sg, sb_ = strip[:,:,0]/255., strip[:,:,1]/255., strip[:,:,2]/255.
            s_mx = np.maximum(np.maximum(sr, sg), sb_)
            s_mn = np.minimum(np.minimum(sr, sg), sb_)
            s_delta = s_mx - s_mn
            s_sat = np.where(s_mx > 0, s_delta / s_mx, 0.)
            s_val = s_mx

            mask = s_sat > 0.35
            if mask.sum() < 10:
                return None

            s_h = np.zeros_like(sr)
            mr  = (s_delta > 0) & (s_mx == sr)
            mg_ = (s_delta > 0) & (s_mx == sg)
            mb  = (s_delta > 0) & (s_mx == sb_)
            s_h[mr]  = ((sg[mr]  - sb_[mr])  / s_delta[mr])  % 6
            s_h[mg_] = (sb_[mg_] - sr[mg_]) / s_delta[mg_]   + 2
            s_h[mb]  = (sr[mb]   - sg[mb])  / s_delta[mb]    + 4
            s_h /= 6.

            # Moyenne circulaire (évite le biais du rouge qui straddle 0°/360°)
            h_rad = s_h[mask] * 2 * np.pi
            hue = float(np.degrees(np.arctan2(np.sin(h_rad).mean(), np.cos(h_rad).mean())) % 360)
            val = float(np.median(s_val[mask]))
            sat = float(np.median(s_sat[mask]))

            # Variance circulaire pour détecter l'Incolore (multicolore)
            hue_std = float(np.degrees(np.sqrt(-2 * np.log(
                np.clip(np.abs(np.exp(1j * h_rad).mean()), 1e-9, 1)
            ))))

            return {
                "y_top":       y1 + top_band_start,
                "y_bot":       y1 + top_band_end,
                "hue_deg":     round(hue, 1),
                "energy_type": self._classify_energy_hue(hue, val, sat, hue_std),
            }
        except Exception as e:
            logger.error("_find_deck_card_strip: %s", e)
            return None

    def _classify_energy_hue(self, hue: float, val: float, sat: float = 0.5,
                             hue_std: float = 0.) -> str:
        """Mappe hue (0-360°) + valeur + saturation → type d'énergie Pokemon TCG.

        Types et couleurs dans PTCG Pocket :
          Rouge       → Feu        (hue  0-25° ou >340°)
          Marron      → Combat     (hue 25-48°)
          Jaune       → Électrique (hue 48-75°)
          Vert        → Plante     (hue 75-160°)
          Bleu        → Eau        (hue 160-255°)
          Violet      → Psy        (hue 255-340°)
          Noir/sombre → Obscurité  (val < 0.30)
          Gris        → Acier      (sat < 0.15)
          Multicolore → Incolore   (variance circulaire de teinte élevée)
        """
        # Incolore : arc-en-ciel — variance circulaire de teinte très élevée
        if hue_std > 50:
            return "Incolore"
        # Obscurité : très sombre
        if val < 0.30:
            return "Obscurité"
        # Acier : gris (faible saturation, mais pas trop sombre)
        if sat < 0.15:
            return "Acier"
        if hue < 25 or hue > 340:
            return "Feu"
        if 25 <= hue <= 48:
            return "Combat"
        if 48 < hue <= 75:
            return "Électrique"
        if 75 < hue <= 160:
            return "Plante"
        if 160 < hue <= 255:
            return "Eau"
        if 255 < hue <= 340:
            return "Psy"
        return "?"

    def _parse_match_type(self, ocr_results) -> str:
        for (_, text, conf) in ocr_results:
            if conf < CONFIDENCE_THRESHOLD:
                continue
            lower = text.lower().strip()
            if "aléatoire" in lower or "aleatoire" in lower:
                return "aléatoire"
            if "classé" in lower or "classe" in lower or "compétitif" in lower:
                return "classé"
            if "entraîn" in lower or "entrainement" in lower or "solo" in lower:
                return "entraînement"
            if "événement" in lower or "evenement" in lower or "event" in lower:
                return "événement"
        return "?"

    def _parse_rank_name(self, ocr_results) -> str | None:
        """Extrait le nom de rang depuis 'Rang [nom]' (ex: 'Rang Hyper Ball 4' → 'Hyper Ball 4').

        Gère deux cas :
        - Token unique  : "Rang Hyper Ball 4" → retourne "Hyper Ball 4"
        - Tokens séparés: "Rang" peut apparaître AVANT ou APRÈS le nom dans les résultats
          OCR (ordre non garanti pour les badges). On cherche le nom avant et après.

        Seuil abaissé à 0.25 : le badge gris a faible contraste.
        """
        _LOW = 0.25

        def _is_name_token(text: str) -> bool:
            lo = text.lower().strip()
            return (lo != "rang" and "points" not in lo
                    and not lo.isdigit() and len(lo) > 1)

        # Pass 1 : "Rang XXX" dans un seul token
        for (_, text, conf) in ocr_results:
            if conf >= _LOW and text.lower().strip().startswith("rang "):
                return text[5:].strip() or None

        # Pass 2 : "Rang" seul — chercher le nom avant ou après
        rang_idx = None
        for i, (_, text, conf) in enumerate(ocr_results):
            if conf >= _LOW and text.lower().strip() == "rang":
                rang_idx = i
                break

        if rang_idx is None:
            return None

        # Chercher d'abord après "Rang"
        for (_, t, c) in ocr_results[rang_idx + 1:]:
            if c >= _LOW and _is_name_token(t):
                return t.strip()

        # Puis avant "Rang" (cas où l'OCR lit le badge de bas en haut)
        for (_, t, c) in reversed(ocr_results[:rang_idx]):
            if c >= _LOW and _is_name_token(t):
                return t.strip()

        return None

    def _parse_rank_points(self, ocr_results) -> int | None:
        """Extrait les points de classement actuels depuis '[N] points'.

        Gère deux cas :
        - Token unique  : "700 points" → extrait 700
        - Tokens séparés: "700" puis "points" → regarde le token précédent
        """
        for i, (_, text, conf) in enumerate(ocr_results):
            if conf < CONFIDENCE_THRESHOLD:
                continue
            lower = text.lower().strip()
            if "points" not in lower:
                continue
            # Chiffres dans le même token avant "points"
            before = lower.split("points")[0]
            digits = "".join(c for c in before if c.isdigit())
            if digits:
                return int(digits)
            # "points" seul → chercher le token précédent numérique
            if i > 0:
                prev_text = ocr_results[i - 1][1].strip()
                prev_conf = ocr_results[i - 1][2]
                if prev_conf >= CONFIDENCE_THRESHOLD:
                    prev_digits = "".join(c for c in prev_text if c.isdigit())
                    if prev_digits and prev_text == prev_digits:  # token purement numérique
                        return int(prev_digits)
        return None

    _DECK_NAME_BLACKLIST = {
        "c'est parti", "c'est parti !", "c'est parti!", "c est parti", "c est parti !",
        "cest parti", "cest parti!", "auto", "désactivé",
        "activé", "désactivée", "activée", "règles", "compétitif",
        "match aléatoire", "ici, vous pouvez choisir votre mode de combat",
        "mode de combat", "et affronter le monde entier.",
        "entamer le combat", "entamer le combat !", "entamer",
        "c'est", "c est",
    }

    # Mots individuels impossibles dans un nom de deck
    _DECK_NAME_WORD_BLACKLIST = {"c'est", "cest", "c est", "parti", "parti!", "!"}

    def _parse_prequeue_deck_name(self, ocr_results) -> str:
        parts = []
        for (_, text, conf) in ocr_results:
            if conf < CONFIDENCE_THRESHOLD:
                continue
            stripped = text.strip()
            if not stripped:
                continue
            if stripped.lower() in self._DECK_NAME_BLACKLIST:
                continue
            if stripped.lower() in self._DECK_NAME_WORD_BLACKLIST:
                continue
            # Ignorer les chiffres seuls (numéros de deck : "01", "09", "21"…)
            if stripped.isdigit():
                continue
            parts.append(stripped)
        # Supprimer un éventuel "C'est parti" en queue (tokens répartis en fin de liste)
        while parts and parts[-1].lower().rstrip("!").strip() in ("c'est", "cest", "parti", "c'est parti"):
            parts.pop()
        return " ".join(parts) if parts else "?"

    # ------------------------------------------------------------------
    # EasyOCR
    # ------------------------------------------------------------------

    def _ensure_reader(self) -> None:
        if self._reader is None:
            import easyocr  # noqa: PLC0415
            self._reader = easyocr.Reader(["fr", "en"], gpu=False)
            logger.info("EasyOCR Reader initialisé (fr+en)")

    def _read_text(self, img) -> list:
        import numpy as np  # noqa: PLC0415
        self._ensure_reader()
        return self._reader.readtext(np.array(img))

    # ------------------------------------------------------------------
    # Groupement en lignes (par proximité Y)
    # ------------------------------------------------------------------

    def _group_into_rows(self, ocr_results, y_tolerance: int = 15) -> list[list]:
        """Regroupe les éléments OCR par ligne (Y proche).

        Retourne une liste de lignes, chaque ligne étant une liste d'éléments
        (bbox, text, conf) triés par X croissant.
        """
        if not ocr_results:
            return []

        def center_y(item):
            bbox = item[0]
            return (bbox[0][1] + bbox[2][1]) / 2

        def center_x(item):
            bbox = item[0]
            return (bbox[0][0] + bbox[2][0]) / 2

        sorted_items = sorted(ocr_results, key=center_y)
        rows = []
        current_row = [sorted_items[0]]
        current_y = center_y(sorted_items[0])

        for item in sorted_items[1:]:
            y = center_y(item)
            if abs(y - current_y) <= y_tolerance:
                current_row.append(item)
            else:
                rows.append(sorted(current_row, key=center_x))
                current_row = [item]
                current_y = y

        if current_row:
            rows.append(sorted(current_row, key=center_x))

        return rows

    def _find_value_in_row(self, rows, label_keywords: list[str],
                           min_conf: float = CONFIDENCE_THRESHOLD) -> str | None:
        """Cherche une ligne dont le premier élément (label) contient un keyword,
        et retourne la concaténation des éléments suivants (valeur)."""
        for row in rows:
            if not row:
                continue
            label_text = row[0][1].lower().strip()
            if any(kw in label_text for kw in label_keywords):
                values = [item[1].strip() for item in row[1:] if item[2] >= min_conf]
                if values:
                    return " ".join(values)
        return None

    # ------------------------------------------------------------------
    # Parsing des champs
    # ------------------------------------------------------------------

    def _parse_result(self, ocr_results) -> str:
        _RESULT_CONF = 0.35  # seuil abaissé car "Défaite..." souvent < 0.5
        for (_, text, conf) in ocr_results:
            if conf < _RESULT_CONF:
                continue
            upper = text.upper().strip().rstrip("!.… -").strip()
            if upper in ("WIN", "YOU WIN", "VICTORY", "VICTOIRE", "GAGNE", "GAGNÉ"):
                return "W"
            if upper in ("LOSE", "YOU LOSE", "DEFEAT", "DEFAITE", "DÉFAITE", "PERDU"):
                return "L"
        return "?"

    def _parse_opponent(self, ocr_results) -> str:
        """Extrait le nom de l'adversaire depuis 'contre [nom]'.

        Si OCR split le nom en plusieurs éléments, on concatène les suivants
        (en s'arrêtant sur Victoire/Défaite/Gagné).
        """
        _stop = {"victoire !", "victoire", "défaite...", "défaite", "gagné !", "gagné",
                 "perdu !", "perdu", "historique", "carte star"}
        for i, (_, text, conf) in enumerate(ocr_results):
            if conf < CONFIDENCE_THRESHOLD:
                continue
            lower = text.lower().strip()
            if lower.startswith("contre "):
                parts = [text[7:].strip()]
                for (_, t2, c2) in ocr_results[i + 1:]:
                    if t2.lower().strip() in _stop:
                        break
                    if c2 >= CONFIDENCE_THRESHOLD:
                        parts.append(t2.strip())
                return " ".join(p for p in parts if p) or "?"
        return "?"

    def _parse_first_player(self, rows) -> str:
        """Détecte 'A joué en premier' ou 'A joué en deuxième'."""
        val = self._find_value_in_row(rows, ["ordre d'action", "ordre d", "action"])
        if val is None:
            return "?"
        lower = val.lower()
        # "A joué en premier" = je joue en premier
        if "premier" in lower or "first" in lower:
            return "Moi"
        # "A joué en deuxième" = l'adversaire a joué en premier
        if "deuxi" in lower or "second" in lower:
            return "Adversaire"
        return "?"

    def _parse_turns(self, rows, raw_results=None, bottom_img=None, upscale=1) -> int | None:
        result = self._parse_number_after(rows, ["tours jou", "tours joué"])
        if result is not None:
            return result

        # Fallback 1 : scan séquentiel des résultats bruts
        if raw_results:
            for i, (_, text, conf) in enumerate(raw_results):
                if conf < 0.3 or "tours" not in text.lower():
                    continue
                for _, t2, c2 in raw_results[i + 1: i + 5]:
                    if c2 < 0.1:
                        continue
                    normalized = t2.replace("o", "0").replace("O", "0").replace("l", "1").replace("I", "1")
                    digits = "".join(c for c in normalized if c.isdigit())
                    if digits:
                        val = int(digits)
                        if 1 <= val <= 99:
                            logger.info("_parse_turns fallback raw: %s", val)
                            return val

        # Fallback 2 : crop ciblé sur la zone valeur de "Tours joués" + upscale 4x
        if bottom_img is not None:
            for row in rows:
                if not row or "tours" not in row[0][1].lower():
                    continue
                try:
                    bbox = row[0][0]
                    row_y = ((bbox[0][1] + bbox[2][1]) / 2) / upscale
                    row_h = max(abs(bbox[2][1] - bbox[0][1]) / upscale, 20)
                    w, h = bottom_img.size
                    y0 = max(0, int(row_y - row_h))
                    y1 = min(h, int(row_y + row_h))
                    x0 = w // 2  # moitié droite seulement (valeur)
                    crop = bottom_img.crop((x0, y0, w, y1))
                    crop_up = crop.resize((crop.width * 4, crop.height * 4))
                    ocr_res = self._read_text(crop_up)
                    for (_, t, c) in ocr_res:
                        if c < 0.1:
                            continue
                        normalized = t.replace("o", "0").replace("O", "0").replace("l", "1").replace("I", "1")
                        digits = "".join(ch for ch in normalized if ch.isdigit())
                        if digits:
                            val = int(digits)
                            if 1 <= val <= 99:
                                logger.info("_parse_turns fallback crop4x: %s", val)
                                return val
                except Exception as e:
                    logger.debug("_parse_turns fallback crop4x: %s", e)
        return None

    def _parse_number_after(self, rows, keywords: list[str]) -> int | None:
        """Retourne le premier entier trouvé dans la valeur d'une ligne identifiée par keywords.
        Seuil de confiance abaissé pour les valeurs numériques (OCR parfois peu confiant)."""
        val = self._find_value_in_row(rows, keywords, min_conf=0.15)
        if val is None:
            return None
        # Remplacer les confusions OCR courantes : o/O → 0, l/I → 1
        normalized = val.replace("o", "0").replace("O", "0").replace("l", "1").replace("I", "1")
        digits = "".join(c for c in normalized if c.isdigit())
        return int(digits) if digits else None

    def _count_points_circles(self, rows, label_kw: str,
                               bottom_img=None, upscale: int = 1) -> int | None:
        """Compte les cercles de points.

        Stratégie 1 : lire les chiffres OCR dans la ligne (cercles bien lus).
        Stratégie 2 (fallback) : détecter les cercles colorés par saturation
                                  dans l'image originale (cercles illisibles par OCR).
        """
        target_row = None
        for row in rows:
            if not row:
                continue
            # Concaténer les 2 premiers tokens pour gérer les labels splittés
            # ("Vos" + "points" → "vos points")
            row_label = " ".join(item[1] for item in row[:2]).lower().strip()
            if label_kw in row_label:
                target_row = row
                break
        if target_row is None:
            return None

        # Stratégie 1 : valeur max des chiffres lus par OCR
        # Le numéro sur le dernier cercle coloré = nombre de prizes pris (ex: "3" = 3 pts)
        digit_vals = [int(item[1].strip()) for item in target_row[1:] if item[1].strip().isdigit()]
        ocr_count = min(3, max(digit_vals)) if digit_vals else 0
        logger.info("_count_points_circles [%s]: target_row=%s digit_vals=%s ocr_count=%s",
                    label_kw, [(it[1], it[2]) for it in target_row], digit_vals, ocr_count)

        # Stratégie 2 : détection couleur dans l'image originale (plus fiable)
        if bottom_img is None:
            return ocr_count  # pas d'image → on fait confiance à l'OCR

        try:
            import numpy as np  # noqa: PLC0415

            # Coordonnées de la ligne dans l'image originale (corriger upscale)
            bbox = target_row[0][0]
            row_y = ((bbox[0][1] + bbox[2][1]) / 2) / upscale
            row_h = max(abs(bbox[2][1] - bbox[0][1]) / upscale, 20)

            w, h = bottom_img.size
            y0 = max(0, int(row_y - row_h * 0.9))
            y1 = min(h, int(row_y + row_h * 0.9))
            x0 = w // 3  # ignorer la zone label
            strip = bottom_img.crop((x0, y0, w, y1)).convert("RGB")

            arr = np.asarray(strip, dtype=float)
            r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
            cmax = np.maximum(np.maximum(r, g), b)
            cmin = np.minimum(np.minimum(r, g), b)
            sat = np.where(cmax > 30, (cmax - cmin) / (cmax + 1e-6), 0.0)
            colored_cols = (sat > 0.30).any(axis=0)

            n = 0
            in_c = False
            gap = 0
            for c in colored_cols:
                if c:
                    if not in_c:
                        n += 1
                        in_c = True
                    gap = 0
                else:
                    if in_c:
                        gap += 1
                        if gap > 4:
                            in_c = False

            logger.info("_count_points_circles [%s]: sat_n=%s result=%s",
                        label_kw, n, max(ocr_count, min(3, n)))
            # Prendre le max : OCR peut sous-estimer, saturation peut sur-estimer
            return max(ocr_count, min(3, n))

        except Exception as e:
            logger.info("_count_points_circles saturation error [%s]: %s", label_kw, e)
            return ocr_count
