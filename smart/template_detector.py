from typing import Optional, Tuple
import cv2
import numpy as np
from .screen import grab, to_screen, move_click

def _match_multi_scale(
    tpl_bgr: np.ndarray,
    haystack_bgr: np.ndarray,
    method=cv2.TM_CCOEFF_NORMED,
    scales=(0.85, 0.9, 0.95, 1.0, 1.05, 1.1, 1.15),
):
    best_val, best_loc, best_wh = -1, None, None
    th, tw = tpl_bgr.shape[:2]
    for s in scales:
        rw, rh = max(1, int(tw * s)), max(1, int(th * s))
        resized = cv2.resize(tpl_bgr, (rw, rh), interpolation=cv2.INTER_AREA)
        if haystack_bgr.shape[0] < rh or haystack_bgr.shape[1] < rw:
            continue
        res = cv2.matchTemplate(haystack_bgr, resized, method)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        val = max_val if method in (cv2.TM_CCOEFF_NORMED, cv2.TM_CCORR_NORMED) else -min_val
        loc = max_loc if method in (cv2.TM_CCOEFF_NORMED, cv2.TM_CCORR_NORMED) else min_loc
        if val > best_val:
            best_val, best_loc, best_wh = val, loc, (rw, rh)
    return best_val, best_loc, best_wh

def click_template(
    template_path: str,
    region: Optional[Tuple[int, int, int, int]] = None,
    threshold: float = 0.84,
) -> bool:
    tpl = cv2.imread(template_path)
    if tpl is None:
        raise FileNotFoundError(f"Template not found: {template_path}")
    screen = grab(region)
    val, loc, wh = _match_multi_scale(tpl, screen)
    if loc is None or wh is None or val < threshold:
        return False
    x, y = loc; w, h = wh
    cx, cy = x + w // 2, y + h // 2
    sx, sy = to_screen((cx, cy), region)
    move_click(sx, sy)
    return True