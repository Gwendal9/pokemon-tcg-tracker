"""tracker/capture/screen.py — Capture fenêtre MUMU + sélection de région.

- auto_detect_mumu_region() : détecte automatiquement la zone client MuMu.
- show_region_highlight()    : affiche un cadre rouge autour d'une région.
- select_region_interactive() : overlay tkinter pour délimiter la région MUMU.
- capture_region() : capture mss de la région configurée → base64 PNG.
Windows-only. Imports mss/tkinter en lazy pour WSL/CI compatibility.
"""
import logging

logger = logging.getLogger(__name__)


def list_all_windows() -> list:
    """Retourne toutes les fenêtres top-level visibles avec titre, dimensions, hwnd.

    Filtre : visibles, non-iconifiées, taille > 100x100, exclut le tracker.
    Triées par aire décroissante (les grandes fenêtres d'abord).

    Returns:
        Liste de {"hwnd": int, "title": str, "width": int, "height": int}.
    """
    import ctypes    # noqa: PLC0415
    import win32gui  # noqa: PLC0415

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

    found = []

    def _enum_cb(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return
        if win32gui.IsIconic(hwnd):
            return
        title = win32gui.GetWindowText(hwnd)
        if not title:
            return
        if "tracker" in title.lower():
            return
        try:
            l, t, r, b = win32gui.GetWindowRect(hwnd)
            w, h = r - l, b - t
            if w < 100 or h < 100:
                return
            found.append({"hwnd": hwnd, "title": title, "width": w, "height": h, "_area": w * h})
        except Exception:
            pass

    win32gui.EnumWindows(_enum_cb, None)
    found.sort(key=lambda c: c["_area"], reverse=True)
    for item in found:
        del item["_area"]
    return found


def find_window_by_title(title: str) -> dict | None:
    """Cherche une fenêtre dont le titre correspond exactement et retourne sa région.

    Utilisé au démarrage pour restaurer automatiquement la fenêtre sélectionnée.

    Returns:
        {"x", "y", "width", "height"} ou None si introuvable.
    """
    import win32gui  # noqa: PLC0415

    result = [None]

    def _cb(hwnd, _):
        if result[0] is not None:
            return
        if not win32gui.IsWindowVisible(hwnd):
            return
        if win32gui.GetWindowText(hwnd) == title:
            result[0] = hwnd

    win32gui.EnumWindows(_cb, None)
    if result[0] is None:
        return None
    return get_window_region(result[0])


def find_mumu_window() -> int | None:
    """Retourne le hwnd de la fenêtre MuMu Player ou None si non trouvée.

    Cherche toutes les fenêtres visibles dont le titre contient "MuMu"
    (insensible à la casse) pour couvrir MuMu Player, MuMu Player 12, etc.
    Windows-only — win32gui importé en lazy pour WSL/CI compatibility.
    """
    import win32gui  # noqa: PLC0415

    found = []

    _keywords = ("mumu", "pokemon", "pokémon")

    def _enum_cb(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd).lower()
            if any(kw in title for kw in _keywords):
                found.append(hwnd)

    win32gui.EnumWindows(_enum_cb, None)
    return found[0] if found else None


def auto_detect_mumu_region() -> dict | None:
    """Détecte la zone de rendu Pokemon dans MuMu Player.

    Stratégie :
    1. Déclarer le process DPI-aware (coordonnées physiques cohérentes avec mss).
    2. Trouver la fenêtre top-level MuMuPlayer.
    3. Parmi ses fenêtres enfants, chercher d'abord celle dont le titre contient
       "pokemon" ou "pokémon" (l'onglet du jeu dans MuMu).
    4. Si introuvable par titre, prendre l'enfant avec la plus grande aire
       qui est strictement plus petite que la fenêtre MuMu parente.
    5. Retourner les coordonnées écran (GetWindowRect, plus fiable que ClientToScreen
       pour les fenêtres enfants embarquées).

    Returns:
        {"x", "y", "width", "height"} ou None si non trouvé.
    """
    import ctypes    # noqa: PLC0415
    import win32gui  # noqa: PLC0415

    # Force DPI physique — indispensable pour cohérence avec mss
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

    def _window_rect(hwnd):
        """Coordonnées écran absolues via GetWindowRect."""
        try:
            l, t, r, b = win32gui.GetWindowRect(hwnd)
            w, h = r - l, b - t
            if w < 50 or h < 50:
                return None
            return {"x": l, "y": t, "width": w, "height": h, "area": w * h}
        except Exception:
            return None

    # find_mumu_window() cherche "mumu", "pokemon", "pokémon" — retourne le bon hwnd.
    # On log tous les candidats pour comprendre ce qui est trouvé.
    found = []

    def _enum_cb(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return
        if win32gui.IsIconic(hwnd):
            return
        title = win32gui.GetWindowText(hwnd)
        title_l = title.lower()
        # Exclure la fenêtre du tracker lui-même
        if "tracker" in title_l:
            return
        if any(kw in title_l for kw in ("mumu", "pokemon", "pokémon")):
            r = _window_rect(hwnd)
            if r:
                found.append({"hwnd": hwnd, "title": title, **r})
                logger.info("auto_detect candidat: hwnd=%d %r  %dx%d @ (%d,%d)",
                            hwnd, title, r["width"], r["height"], r["x"], r["y"])

    win32gui.EnumWindows(_enum_cb, None)

    if not found:
        logger.warning("auto_detect: aucune fenêtre MuMu/Pokemon trouvée")
        return None

    # Priorité 1 : fenêtre avec "pokemon" ou "pokémon" dans le titre (l'onglet du jeu)
    pokemon_wins = [c for c in found if "pokemon" in c["title"].lower() or "pokémon" in c["title"].lower()]
    if pokemon_wins:
        best = max(pokemon_wins, key=lambda c: c["area"])
        logger.info("auto_detect: fenêtre pokemon sélectionnée  %dx%d @ (%d,%d)",
                    best["width"], best["height"], best["x"], best["y"])
        return {"x": best["x"], "y": best["y"], "width": best["width"], "height": best["height"]}

    # Priorité 2 : fenêtre MuMu (fallback)
    best = max(found, key=lambda c: c["area"])
    logger.info("auto_detect: fallback MuMu  %dx%d @ (%d,%d)",
                best["width"], best["height"], best["x"], best["y"])
    return {"x": best["x"], "y": best["y"], "width": best["width"], "height": best["height"]}


def get_window_region(hwnd: int) -> dict | None:
    """Retourne les coordonnées écran d'une fenêtre par son hwnd.

    Returns:
        {"x", "y", "width", "height"} ou None si introuvable.
    """
    import win32gui  # noqa: PLC0415

    try:
        l, t, r, b = win32gui.GetWindowRect(hwnd)
        w, h = r - l, b - t
        if w < 50 or h < 50:
            return None
        return {"x": l, "y": t, "width": w, "height": h}
    except Exception:
        return None


def show_region_highlight(region: dict, duration: float = 2.5) -> None:
    """Affiche un cadre rouge autour de la région pendant `duration` secondes.

    Crée une fenêtre tkinter sans titre, transparente au centre, avec une
    bordure rouge visible. Utile comme confirmation visuelle après détection.
    """
    import tkinter as tk  # noqa: PLC0415

    x = region["x"]
    y = region["y"]
    w = region["width"]
    h = region["height"]
    border = 4

    root = tk.Tk()
    root.overrideredirect(True)
    root.geometry(f"{w}x{h}+{x}+{y}")
    root.attributes("-topmost", True)
    root.attributes("-transparentcolor", "black")
    root.configure(bg="black")

    canvas = tk.Canvas(root, bg="black", highlightthickness=0)
    canvas.pack(fill=tk.BOTH, expand=True)
    # Contour rouge, intérieur noir (transparent via transparentcolor)
    canvas.create_rectangle(
        border, border, w - border, h - border,
        outline="red", width=border * 2, fill="black",
    )

    root.after(int(duration * 1000), root.destroy)
    root.mainloop()


def select_region_interactive() -> dict | None:
    """Overlay fullscreen transparent pour sélection de région par drag souris.

    Retourne {"x", "y", "width", "height"} en coordonnées écran absolues,
    ou None si l'utilisateur annule (touche Échap).

    Windows-only — appeler depuis un thread non-UI (pas le thread pywebview).
    tkinter importé en lazy pour éviter l'erreur en WSL/CI.
    """
    import tkinter as tk  # noqa: PLC0415 — import lazy intentionnel (Windows-only)

    result = {"region": None}

    root = tk.Tk()
    root.attributes("-fullscreen", True)
    root.attributes("-alpha", 0.3)
    root.configure(bg="black")
    root.attributes("-topmost", True)
    root.title("Sélectionnez la région MUMU — Échap pour annuler")

    canvas = tk.Canvas(root, cursor="crosshair", bg="black", highlightthickness=0)
    canvas.pack(fill=tk.BOTH, expand=True)

    # Label d'instruction
    label = tk.Label(
        root,
        text="Cliquez et glissez pour sélectionner la région MUMU · Échap pour annuler",
        fg="white",
        bg="black",
        font=("Arial", 14),
    )
    label.place(relx=0.5, rely=0.05, anchor="center")

    state = {"start_x": 0, "start_y": 0, "rect_id": None}

    def on_press(event):
        state["start_x"] = event.x_root
        state["start_y"] = event.y_root
        if state["rect_id"]:
            canvas.delete(state["rect_id"])
            state["rect_id"] = None

    def on_drag(event):
        if state["rect_id"]:
            canvas.delete(state["rect_id"])
        x1 = state["start_x"] - root.winfo_rootx()
        y1 = state["start_y"] - root.winfo_rooty()
        x2 = event.x_root - root.winfo_rootx()
        y2 = event.y_root - root.winfo_rooty()
        state["rect_id"] = canvas.create_rectangle(
            x1, y1, x2, y2, outline="red", width=2, fill=""
        )

    def on_release(event):
        x = min(state["start_x"], event.x_root)
        y = min(state["start_y"], event.y_root)
        w = abs(event.x_root - state["start_x"])
        h = abs(event.y_root - state["start_y"])
        if w > 10 and h > 10:
            result["region"] = {"x": x, "y": y, "width": w, "height": h}
        root.destroy()

    def on_escape(event):
        root.destroy()

    canvas.bind("<ButtonPress-1>", on_press)
    canvas.bind("<B1-Motion>", on_drag)
    canvas.bind("<ButtonRelease-1>", on_release)
    root.bind("<Escape>", on_escape)

    root.mainloop()
    return result["region"]


def capture_region_pil(region: dict):
    """Capture la région écran via mss. Retourne une PIL Image ou None si erreur.

    Utilisé en interne par le pipeline de détection (pas de conversion base64).
    """
    import mss  # noqa: PLC0415
    from PIL import Image  # noqa: PLC0415

    try:
        monitor = {
            "left": region["x"],
            "top": region["y"],
            "width": region["width"],
            "height": region["height"],
        }
        with mss.mss() as sct:
            screenshot = sct.grab(monitor)
            return Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
    except Exception as e:
        logger.error("capture_region_pil: %s", e)
        return None


def capture_region(region: dict) -> dict | None:
    """Capture la région écran via mss. Retourne base64 PNG ou None si erreur.

    Args:
        region: dict avec clés x, y, width, height (coordonnées absolues écran).

    Returns:
        {"image_b64": str, "width": int, "height": int} ou None.
    """
    import base64  # noqa: PLC0415
    import io  # noqa: PLC0415
    import mss  # noqa: PLC0415
    from PIL import Image  # noqa: PLC0415

    try:
        monitor = {
            "left": region["x"],
            "top": region["y"],
            "width": region["width"],
            "height": region["height"],
        }
        with mss.mss() as sct:
            screenshot = sct.grab(monitor)
            img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return {"image_b64": b64, "width": region["width"], "height": region["height"]}
    except Exception as e:
        logger.error("capture_region: %s", e)
        return None
