import cv2
import numpy as np

def get_mean_color(frame, box, height=30):
    x1, y1, x2, y2 = map(int, box)
    region_above = frame[max(0, y1-height):y1, x1:x2]

    if region_above.size == 0:
        return None

    mean_color = cv2.mean(region_above)[:3]
    return mean_color

# Exemplo de uso
image_path = '/mnt/data/Screenshot_5.png'
image = cv2.imread(image_path)
box = [100, 150, 200, 250]  # Exemplo de coordenadas (x1, y1, x2, y2)
mean_color = get_mean_color(image, box)

if mean_color is not None:
    print(f"Mean color (BGR): {mean_color}")
else:
    print("A região de detecção está vazia.")
