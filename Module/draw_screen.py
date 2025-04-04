# import pygame
# import sys

# import ctypes  # 新增导入（仅Windows）


# class PerspectiveOverlay:
#     def __init__(self, area_rect: tuple[int, int, int, int]):
#         if not pygame.get_init():
#             pygame.init()
#         self.area_rect = area_rect
#         self.screen_width = pygame.display.Info().current_w
#         self.screen_height = pygame.display.Info().current_h

#         # 创建窗口并设置透明（仅Windows）
#         flags = pygame.NOFRAME | pygame.HWSURFACE
#         self.screen = pygame.display.set_mode(
#             (self.screen_width, self.screen_height), flags
#         )
#         if sys.platform == "win32":
#             hwnd = pygame.display.get_wm_info()["window"]
#             ctypes.windll.user32.SetWindowLongW(hwnd, -20, 0x80000)

#         # 创建透明Surface并初始化为全透明
#         self.surface = pygame.Surface(
#             (self.screen_width, self.screen_height), pygame.SRCALPHA
#         )
#         self.surface.fill((0, 0, 0, 0))  # 显式填充透明背景

#     def draw_border(
#         self, rect: tuple[int, int, int, int], color: tuple[int, int, int], width=2
#     ):
#         # 确保每次绘制前Surface背景透明（关键）
#         self.surface.fill((0, 0, 0, 0))  # 新增：清除残留内容
#         pygame.draw.rect(self.surface, color, rect, width)

#     def update(self):
#         # 将Surface内容渲染到窗口
#         self.screen.blit(self.surface, (0, 0))
#         pygame.display.update()

#     def run(self):
#         running = True
#         while running:
#             for event in pygame.event.get():
#                 if event.type == pygame.QUIT:
#                     running = False
#             # 每次循环重新绘制边框（确保持续显示）
#             self.draw_border(  # 新增：在循环中持续绘制边框
#                 (
#                     self.area_rect[0],
#                     self.area_rect[1],
#                     self.area_rect[2] - self.area_rect[0],
#                     self.area_rect[3] - self.area_rect[1],
#                 ),
#                 (255, 0, 0),
#                 width=3,
#             )
#             self.update()
#         pygame.quit()
#         sys.exit()

#     @staticmethod
#     def get_screen_center() -> tuple[int, int]:
#         """获取屏幕中心坐标"""
#         if not pygame.get_init():
#             pygame.init()
#         info = pygame.display.Info()
#         return (info.current_w // 2, info.current_h // 2)


# # 使用示例
# if __name__ == "__main__":
#     # 获取屏幕中心并定义区域
#     center_x, center_y = PerspectiveOverlay.get_screen_center()
#     area = (center_x - 100, center_y - 100, 200, 200)  # 左  # 上  # 宽度  # 高度
#     # 转换为 (left, top, right, bottom) 格式
#     area_rect = (area[0], area[1], area[0] + area[2], area[1] + area[3])

#     overlay = PerspectiveOverlay(area_rect)

#     # 绘制红色边框（围绕指定区域）
#     overlay.draw_border(
#         (area[0], area[1], area[2], area[3]), (255, 0, 0), width=3  # 红色
#     )

#     # 启动透视层（实时显示）
#     overlay.run()
