import os
from pathlib import Path
import sys
from typing import Any
import json

Root = Path(os.path.realpath(sys.argv[0])).parent


class _Config:
    def __init__(self):
        self.default = {
            "aim_range": 135,
            "aimbot": True,
            "mouse_mode": "mouse",
            "closest_mouse_dist": 160.8,
            "confidence": 0.32,
            "lockSpeed": 0.2,
            "offset_x": 0,
            "offset_y": 0,
            "model_file": "yolov8n.pt",
            "mouse_Side_Button_Witch": True,
            "ProcessMode": "multi_process",
            "window_always_on_top": False,
            "target_class": "0",
        }
        self.content = self.read()

    def read(self) -> dict:
        try:
            os.makedirs(Root / "Data", exist_ok=True)
            with open(Root / "Data" / "settings.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return self.default

    def get(self, key: str, default: Any = None) -> Any:
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

    def delete(self, key: str) -> None:
        if key in self.content:
            del self.content[key]
            self.save()

    def save(self) -> None:
        with open(Root / "Data" / "settings.json", "w", encoding="utf8") as f:
            f.write(json.dumps(self.content, ensure_ascii=False, indent=4))

    def __getitem__(self, key: str) -> Any:
        return self.content.get(key, self.default.get(key))

    def __setitem__(self, key: str, value: Any) -> None:
        self.update(key, value)

    def __delitem__(self, key: str) -> None:
        self.delete(key)


Config = _Config()
