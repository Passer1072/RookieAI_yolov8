import os
from pathlib import Path
import sys
from typing import Any, Union
import json

Root = Path(os.path.realpath(sys.argv[0])).parent


class _Config:
    def __init__(self):
        self.default = {
            "aim_range": 135,
            "aimbot": True,
            "closest_mouse_dist": 160.8,
            "confidence": 0.32,
            "lockSpeed": 0.2,
            "model_file": "yolov8n.pt",
            "mouse_Side_Button_Witch": True,
            "ProcessMode": "multi_process",
            "window_always_on_top": False,
            "target_class": "0"
        }
        self.content = self.read()

    def read(self) -> dict:
        try:
            with open(Root / "settings.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return self.default

    def get(self, key: str, default: Any = None) -> Union[int, str, list, float, bool]:
        """
        获取配置项的值，如果不存在则返回默认值。

        :param key: 配置项的键
        :param default: 默认值
        :return: 返回配置项的值，类型可能是 int, str, list, float 或 bool
        """
        if default is not None:
            return self.content.get(key, default)
        return self.content.get(key, self.default.get(key))

    def update(self, key: str, value: Any) -> None:
        self.content[key] = value
        self.save()

    def save(self) -> None:
        with open(Root / "settings.json", "w", encoding="utf8") as f:
            f.write(json.dumps(self.content, ensure_ascii=False, indent=4))

Config = _Config()