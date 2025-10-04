from typing import List, Optional, Tuple, Dict, Any
import numpy as np
from rapidfuzz import process, fuzz
from .screen import grab

# 可选两种 OCR 引擎：优先 easyocr（若已安装 torch 等），否则回退到 Tesseract
_USE_EASYOCR = False
_EASYREADER = None

def _try_init_easyocr(langs=None, gpu=False):
    global _USE_EASYOCR, _EASYREADER
    try:
        import easyocr  # type: ignore
        if langs is None:
            langs = ["ch_sim", "en"]
        _EASYREADER = easyocr.Reader(langs, gpu=gpu)
        _USE_EASYOCR = True
    except Exception:
        _USE_EASYOCR = False

def _ocr_easy(image: np.ndarray):
    assert _EASYREADER is not None
    # 返回 [(bbox, text, conf), ...]
    return _EASYREADER.readtext(image, detail=1, paragraph=False)

def _ocr_tesseract(image: np.ndarray):
    # 用 pytesseract 返回与 easyocr 近似的结构
    import cv2
    import pytesseract
    from pytesseract import Output
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    data = pytesseract.image_to_data(rgb, lang="chi_sim+eng", output_type=Output.DICT)
    n = len(data["text"])
    results = []
    for i in range(n):
        txt = (data["text"][i] or "").strip()
        if not txt:
            continue
        conf = float(data.get("conf", ["0"] * n)[i])
        try:
            conf = conf / 100.0
        except Exception:
            conf = 0.0
        x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
        bbox = [[x, y], [x + w, y], [x + w, y + h], [x, y + h]]
        results.append((bbox, txt, conf))
    return results

def ocr(image: np.ndarray):
    if _EASYREADER is None and not _USE_EASYOCR:
        _try_init_easyocr()
    if _USE_EASYOCR and _EASYREADER is not None:
        return _ocr_easy(image)
    # 回退到 Tesseract
    return _ocr_tesseract(image)

def find_keywords(
    keywords: List[str],
    region: Optional[Tuple[int, int, int, int]] = None,
    min_conf: float = 0.5,
    prefer_area: str = "bottom-right",
    negative: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    """
    返回: {'center': (x,y) 屏幕坐标, 'text': str, 'conf': float, 'bbox': list}
    """
    img = grab(region)
    results = ocr(img)
    negative = negative or ["上一", "上一个", "Prev", "Previous"]

    best = None
    best_score = -1.0

    for bbox, text, conf in results:
        text = str(text or "").strip()
        if conf < min_conf:
            continue
        if any(ng in text for ng in negative):
            continue
        matched = any(kw in text for kw in keywords)
        if not matched:
            cand = process.extractOne(text, keywords, scorer=fuzz.partial_ratio)
            if not cand or cand[1] < 80:
                if "下一" not in text and "完成" not in text and "已完成" not in text:
                    continue

        xs = [p[0] for p in bbox]; ys = [p[1] for p in bbox]
        cx, cy = int(sum(xs) / 4), int(sum(ys) / 4)

        score = float(conf)
        if region:
            _, _, w, h = region
            # 位置偏好
            if prefer_area == "bottom-right":
                score += 0.4 * (1.0 / (max(w - cx, 1) + max(h - cy, 1)))
            elif prefer_area == "bottom":
                score += 0.3 * (1.0 / max(h - cy, 1))

        if score > best_score:
            best_score = score
            best = {"center": (cx, cy), "text": text, "conf": float(conf), "bbox": bbox}

    if best and region:
        l, t, _, _ = region
        best["center"] = (best["center"][0] + l, best["center"][1] + t)

    return best