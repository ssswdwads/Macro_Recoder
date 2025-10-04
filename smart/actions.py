import time
from typing import Dict, List, Optional, Tuple
import cv2
import numpy as np
from .screen import grab, move_click, to_screen, scroll as wheel, key_press
from .ocr_utils import find_keywords
from .template_detector import click_template

Region = Tuple[int, int, int, int]

class SmartActions:
    def find_and_click_text(
        self,
        keywords: List[str],
        region: Optional[Region] = None,
        timeout: float = 10.0,
        interval: float = 0.4,
        prefer_area: str = "bottom-right",
    ) -> bool:
        end = time.time() + timeout
        while time.time() < end:
            hit = find_keywords(keywords, region=region, prefer_area=prefer_area)
            if hit:
                x, y = hit["center"]
                move_click(x, y)
                return True
            time.sleep(interval)
        return False

    def wait_for_text(
        self,
        keywords: List[str],
        region: Optional[Region] = None,
        timeout: float = 120.0,
        interval: float = 0.8,
        require_green: bool = False,
    ) -> bool:
        def is_green_patch(img_bgr: np.ndarray, cx: int, cy: int) -> bool:
            h, w = img_bgr.shape[:2]
            x1, y1 = max(0, cx - 8), max(0, cy - 8)
            x2, y2 = min(w, cx + 8), min(h, cy + 8)
            patch = img_bgr[y1:y2, x1:x2]
            if patch.size == 0:
                return False
            hsv = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV)
            H, S, V = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
            mask = (H >= 35) & (H <= 85) & (S >= 60) & (V >= 80)
            return (mask.sum() / mask.size) > 0.4

        end = time.time() + timeout
        while time.time() < end:
            img = grab(region)
            hit = find_keywords(keywords, region=region, prefer_area="bottom-right")
            if hit:
                if not require_green:
                    return True
                cx, cy = hit["center"]
                if region:
                    l, t, _, _ = region
                    cx, cy = cx - l, cy - t
                if is_green_patch(img, cx, cy):
                    return True
            time.sleep(interval)
        return False

    def scroll_until_text(
        self,
        keywords: List[str],
        max_scrolls: int = 8,
        step: int = -600,  # 负数向下滚动
        region: Optional[Region] = None,
        prefer_area: str = "bottom",
        pause: float = 0.3,
    ) -> bool:
        hit = find_keywords(keywords, region=region, prefer_area=prefer_area)
        if hit:
            x, y = hit["center"]
            move_click(x, y)
            return True

        for _ in range(max_scrolls):
            wheel(step)
            time.sleep(pause)
            hit = find_keywords(keywords, region=region, prefer_area=prefer_area)
            if hit:
                x, y = hit["center"]
                move_click(x, y)
                return True
        return False

    def click_by_template(
        self,
        template_path: str,
        region: Optional[Region] = None,
        threshold: float = 0.84,
    ) -> bool:
        return click_template(template_path, region=region, threshold=threshold)

    def ensure_muted(self, strategy: str = "press_m"):
        if strategy == "press_m":
            key_press("m")
        else:
            key_press("m")

    # 新增：即时条件判断（用于 IF 守护，非阻塞）
    def is_text_present(
        self,
        keywords: List[str],
        region: Optional[Region] = None,
        prefer_area: str = "bottom-right",
        require_green: bool = False,
    ) -> bool:
        hit = find_keywords(keywords, region=region, prefer_area=prefer_area)
        if not hit:
            return False
        if not require_green:
            return True
        # 颜色判断（可选）
        img = grab(region)
        cx, cy = hit["center"]
        if region:
            l, t, _, _ = region
            cx, cy = cx - l, cy - t
        h, w = img.shape[:2]
        x1, y1 = max(0, cx - 8), max(0, cy - 8)
        x2, y2 = min(w, cx + 8), min(h, cy + 8)
        patch = img[y1:y2, x1:x2]
        if patch.size == 0:
            return False
        hsv = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV)
        H, S, V = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
        mask = (H >= 35) & (H <= 85) & (S >= 60) & (V >= 80)
        return (mask.sum() / mask.size) > 0.4