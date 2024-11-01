from typing import Any, Union
import json


class Option:
    def __init__(self):
        self.default = {
            "aimbot": True,
            "lockSpeed": 0.7,
            "triggerType": "按下",
            "arduinoMode": False,
            "lockKey": "右键",
            "mouse_Side_Button_Witch": True,
            "method_of_prediction": "倍率预测",
            "confidence": 0.5,
            # 'extra_offset_x': 5,
            # 'extra_offset_y': 5,
            "prediction_factor": 0.5,
            "closest_mouse_dist": 160,
            "screen_width": 360,
            "screen_height": 360,
            "aimOffset": 0.4,
            "aimOffset_Magnification_x": 0,
            "model_file": "yolov8n.pt",
            "test_window_frame": False,
            "crawl_information": True,
            "screenshot_mode": False,
            "DXcam_screenshot": 360,
            "dxcam_maxFPS": 30,
            "segmented_aiming_switch": False,
            "mouse_control": "win32",
            "stage1_scope": 50,
            "stage1_intensity": 0.8,
            "stage2_scope": 170,
            "stage2_intensity": 0.4,
            "enable_random_offset": False,
            "time_interval": 1,
            "tolerance": 63.0,
            "ignore_colors": [[62, 203, 236]],
            "offset_range": [0, 1],
            "recoil_switch": False,
            "recoil_interval": 0.1,
            "recoil_boosted_distance": 5,
            "recoil_boosted_distance_time": 0.5,
            "recoil_standard_distance": 1,
            "recoil_transition_time": 0.2,
        }
        self.content = self.read()

    def read(self) -> dict:
        try:
            with open("settings.json", "r", encoding="utf-8") as f:
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
        with open("settings.json", "w", encoding="utf8") as f:
            f.write(json.dumps(self.content, ensure_ascii=False, indent=4))
