"""tracker/capture/screen.py — Capture fenêtre MUMU + sélection de région.

- select_region_interactive() : overlay tkinter pour délimiter la région MUMU.
- capture_region() : capture mss de la région configurée → base64 PNG.
Windows-only. Imports mss/tkinter en lazy pour WSL/CI compatibility.
"""
import logging

logger = logging.getLogger(__name__)


def find_mumu_window() -> int | None:
    """Retourne le hwnd de la fenêtre MuMu Player ou None si non trouvée.

    Windows-only — win32gui importé en lazy pour WSL/CI compatibility.
    """
    import win32gui  # noqa: PLC0415
    hwnd = win32gui.FindWindow(None, "MuMu Player")
    return hwnd if hwnd else None


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
