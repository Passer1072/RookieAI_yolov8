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
            "mouse_mode": "mouse",
            "closest_mouse_dist": 160.8,
            "confidence": 0.32,
            "lockSpeed": 0.2,
            "offset_x": 0,
            "offset_y": 0,
            "model_file": "yolov8n.pt",
            "slow_zone_radius": 0,  #未知
            "near_speed_multiplier": 1.0,  #未知
            "screen_pixels_for_360_degrees": 0,  #未知
            "screen_height_pixels": 0,  #未知
            "mouse_Side_Button_Witch": True,
            "ProcessMode": "multi_process",
            "window_always_on_top": False,
            "target_class": "0"
        }
        self.content = self.read()

    def read(self) -> dict:
        try:
            os.makedirs(Root / "Data", exist_ok=True)
            with open(Root / "Data" / "settings.json", "r", encoding="utf-8") as f:
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

    def delete(self, key: str) -> None:
        if key in self.content:
            del self.content[key]
            self.save()

    def save(self) -> None:
        with open(Root / "Data" / "settings.json", "w", encoding="utf8") as f:
            f.write(json.dumps(self.content, ensure_ascii=False, indent=4))

    def __getitem__(self, key: str) -> Any:
        value = self.content.get(key, self.default.get(key))
        print(f"Accessing key '{key}': {value}")  # 可以在这里添加其他逻辑
        return value

    def __setitem__(self, key: str, value: Any) -> None:
        print(f"Setting key '{key}' to: {value}")  # 可以在这里添加其他逻辑
        self.update(key, value)

    def __delitem__(self, key: str) -> None:
        print(f"Deleting key '{key}'")  # 可以在这里添加其他逻辑
        self.delete(key)

Config = _Config()