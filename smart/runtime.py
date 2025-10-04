from typing import Any, Dict, List
from .actions import SmartActions

class SmartExecutor:
    """
    解释并执行 smart_* 事件；支持 IF 守护条件判断
    """
    def __init__(self):
        self.act = SmartActions()

    def handle(self, event: List[Any]) -> bool:
        typ = event[0]
        payload: Dict = event[1] if len(event) >= 2 and isinstance(event[1], dict) else {}
        if typ == "smart_click_ocr":
            return self.act.find_and_click_text(
                payload.get("keywords", []),
                region=payload.get("region"),
                timeout=float(payload.get("timeout", 10.0)),
                interval=float(payload.get("interval", 0.4)),
                prefer_area=payload.get("prefer_area", "bottom-right"),
            )
        elif typ == "smart_wait_text":
            return self.act.wait_for_text(
                payload.get("keywords", []),
                region=payload.get("region"),
                timeout=float(payload.get("timeout", 120.0)),
                interval=float(payload.get("interval", 0.8)),
                require_green=bool(payload.get("require_green", False)),
            )
        elif typ == "smart_scroll_until_text":
            return self.act.scroll_until_text(
                payload.get("keywords", []),
                max_scrolls=int(payload.get("max_scrolls", 8)),
                step=int(payload.get("step", -600)),
                region=payload.get("region"),
                prefer_area=payload.get("prefer_area", "bottom"),
                pause=float(payload.get("pause", 0.3)),
            )
        elif typ == "smart_click_template":
            return self.act.click_by_template(
                payload.get("template_path", ""),
                region=payload.get("region"),
                threshold=float(payload.get("threshold", 0.84)),
            )
        elif typ == "smart_mute":
            self.act.ensure_muted(payload.get("strategy", "press_m"))
            return True
        elif typ in ("smart_if_guard_ocr", "smart_end_guard"):
            # IF/END-IF 的执行在 recorder 里处理，这里占位返回 True
            return True
        return False

    # 供 recorder 的 IF 守护即时判断调用
    def condition_met(self, payload: Dict) -> bool:
        keywords = payload.get("keywords", [])
        region = payload.get("region")
        prefer_area = payload.get("prefer_area", "bottom-right")
        require_green = bool(payload.get("require_green", False))
        return self.act.is_text_present(
            keywords=keywords,
            region=region,
            prefer_area=prefer_area,
            require_green=require_green
        )