"""
本脚本使用ultralytics官方的YOLOv8 pt模型转换为TRT模型方案
修改原"yolov8n.pt"部分为需要转换的pt模型文件绝对路径，随后运行代码自动进行转换。
"""

from ultralytics import YOLO

# Load a model
model = YOLO("yolov8n.pt")  # load a custom trained model

# Export the model
model.export(format="engine", workspace=8.0, half=True)
