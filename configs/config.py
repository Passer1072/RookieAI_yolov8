import os
from pathlib import Path
import sys
from typing import Any
import json

Root = Path(os.path.realpath(sys.argv[0])).parent


class Config:
    default = {
        "log_level": "info",
        "aim_range": 150,
        "aimBot": True,
        "confidence": 0.3,
        "aim_speed_x": 6.7,
        "aim_speed_y": 8.3,
        "model_file": "yolov8n.pt",
        "mouse_Side_Button_Witch": True,
        "ProcessMode": "single_process",
        "window_always_on_top": False,
        "target_class": "0",
        "lockKey": "VK_RBUTTON",
        "triggerType": "按下",
        "offset_centery": 0.75,
        "offset_centerx": 0.0,
        "screen_pixels_for_360_degrees": 6550,
        "screen_height_pixels": 3220,
        "near_speed_multiplier": 2.5,
        "slow_zone_radius": 0,
        "mouseMoveMode": "win32",
        "lockSpeed": 5.5,
        "jump_suppression_switch": False,
        "jump_suppression_fluctuation_range": 18
    }
    content = None

    @classmethod
    def read(cls) -> dict:
        try:
            os.makedirs(Root / "data", exist_ok=True)
            with open(Root / "data" / "settings.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return cls.default

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        """
        获取配置项的值，如果不存在则返回默认值。

        :param key: 配置项的键
        :param default: 默认值
        :return: 返回配置项的值，类型可能是 int, str, list, float 或 bool
        """
        if cls.content is None:
            cls.content = cls.read()  # 读取配置文件
        if default is not None:
            return cls.content.get(key, default)
        return cls.content.get(key, cls.default.get(key))

    @classmethod
    def update(cls, key: str, value: Any) -> None:
        if cls.content is None:
            cls.content = cls.read()
        cls.content[key] = value
        cls.save()

    @classmethod
    def delete(cls, key: str) -> None:
        if cls.content is None:
            cls.content = cls.read()
        if key in cls.content:
            del cls.content[key]
            cls.save()

    @classmethod
    def save(cls) -> None:
        if cls.content is None:
            cls.content = cls.read()
        with open(Root / "data" / "settings.json", "w", encoding="utf8") as f:
            f.write(json.dumps(cls.content, ensure_ascii=False, indent=4))
