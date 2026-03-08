"""tools/debug_windows.py — Diagnostic des fenêtres MuMu Player.

Lance ce script depuis Windows (pas WSL) avec :
    python tools/debug_windows.py

Il affiche TOUTES les fenêtres visibles + la hiérarchie complète
des fenêtres MuMu (enfants, classes, coordonnées).
"""
import win32gui
import win32api
import win32con


def get_rect_info(hwnd):
    """Retourne (window_rect, client_rect_screen) ou None."""
    try:
        wr = win32gui.GetWindowRect(hwnd)          # (left, top, right, bottom) écran
        cl, ct, cr, cb = win32gui.GetClientRect(hwnd)
        sx, sy = win32gui.ClientToScreen(hwnd, (cl, ct))
        w = cr - cl
        h = cb - ct
        return {
            "win_rect": wr,
            "client_x": sx, "client_y": sy,
            "client_w": w, "client_h": h,
            "client_area": w * h,
        }
    except Exception as e:
        return {"error": str(e)}


def print_window(hwnd, depth=0, label=""):
    indent = "  " * depth
    title = win32gui.GetWindowText(hwnd)
    cls = win32gui.GetClassName(hwnd)
    visible = win32gui.IsWindowVisible(hwnd)
    info = get_rect_info(hwnd)

    tag = f"[{label}] " if label else ""
    print(f"{indent}{tag}hwnd={hwnd} visible={visible}")
    print(f"{indent}  titre  : {repr(title)}")
    print(f"{indent}  classe : {cls}")
    if "error" in info:
        print(f"{indent}  ERREUR : {info['error']}")
    else:
        wr = info["win_rect"]
        print(f"{indent}  win_rect   : left={wr[0]} top={wr[1]} right={wr[2]} bottom={wr[3]}"
              f"  ({wr[2]-wr[0]}x{wr[3]-wr[1]})")
        print(f"{indent}  client_scr : x={info['client_x']} y={info['client_y']}"
              f"  {info['client_w']}x{info['client_h']}  aire={info['client_area']}")


def enum_children(parent_hwnd, depth=1):
    children = []

    def _cb(hwnd, _):
        children.append(hwnd)

    try:
        win32gui.EnumChildWindows(parent_hwnd, _cb, None)
    except Exception:
        pass

    for child in children:
        # Seulement les enfants directs (profondeur 1 par rapport au parent)
        parent_of_child = win32gui.GetParent(child)
        if parent_of_child == parent_hwnd:
            print_window(child, depth=depth)
            enum_children(child, depth=depth + 1)


def main():
    print("=" * 70)
    print("TOUTES LES FENETRES VISIBLES (titre non vide)")
    print("=" * 70)
    all_windows = []

    def _top_cb(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title:
                all_windows.append((hwnd, title))

    win32gui.EnumWindows(_top_cb, None)

    for hwnd, title in sorted(all_windows, key=lambda x: x[1].lower()):
        print(f"  hwnd={hwnd:8d}  {repr(title)}")

    print()
    print("=" * 70)
    print("FENETRES CONTENANT 'mumu' (insensible casse) + ENFANTS")
    print("=" * 70)

    mumu_found = [(hwnd, title) for hwnd, title in all_windows if "mumu" in title.lower()]

    if not mumu_found:
        print("  Aucune fenetre MuMu trouvee !")
        print("  Assurez-vous que MuMu Player est ouvert et visible.")
        return

    for hwnd, title in mumu_found:
        print()
        print(f">>> FENETRE PRINCIPALE : {repr(title)}")
        print_window(hwnd, depth=0, label="TOP")
        print(f"    Enfants :")
        enum_children(hwnd, depth=1)

    print()
    print("=" * 70)
    print("RECOMMANDATION : cherchez le candidat avec la plus grande")
    print("'client_area' ET dont client_w/client_h ressemble a l'ecran du jeu.")
    print("Le rapport largeur/hauteur de Pokemon TCG Pocket est environ 0.56 (portrait)")
    print("ou 1.78 (paysage).")
    print("=" * 70)

    # Collecter tous les candidats valides (>100x100)
    candidates = []

    def _collect(hwnd):
        info = get_rect_info(hwnd)
        if "error" in info:
            return
        w = info["client_w"]
        h = info["client_h"]
        if w < 100 or h < 100:
            return
        ratio = w / h if h > 0 else 0
        candidates.append({
            "hwnd": hwnd,
            "title": win32gui.GetWindowText(hwnd),
            "cls": win32gui.GetClassName(hwnd),
            "x": info["client_x"], "y": info["client_y"],
            "w": w, "h": h,
            "area": info["client_area"],
            "ratio": ratio,
        })

    def _cb_all(hwnd, _):
        _collect(hwnd)

    for hwnd, _ in mumu_found:
        _collect(hwnd)
        try:
            win32gui.EnumChildWindows(hwnd, _cb_all, None)
        except Exception:
            pass

    candidates.sort(key=lambda c: c["area"], reverse=True)
    print()
    print("TOP 5 par aire (meilleurs candidats) :")
    for i, c in enumerate(candidates[:5]):
        ratio_str = f"{c['ratio']:.2f}"
        print(f"  #{i+1}  hwnd={c['hwnd']}  {c['w']}x{c['h']}  ratio={ratio_str}"
              f"  x={c['x']} y={c['y']}  classe={c['cls']}  titre={repr(c['title'])}")

    best = candidates[0] if candidates else None
    if best:
        print()
        print(f"SELECTION ACTUELLE (plus grande aire) :")
        print(f"  x={best['x']} y={best['y']} w={best['w']} h={best['h']}")
        print(f"  classe={best['cls']}  ratio={best['ratio']:.2f}")


if __name__ == "__main__":
    main()
