import time
import win32api
import win32con
import keyboard
import configparser
import os
import threading
import yaml

# 读取 YAML 配置文件
yaml_config_file = 'settings.json'


# 检查反后坐力功能是否开启
def is_antirecoil_enabled():
    if not os.path.isfile(yaml_config_file):
        print(f"错误：找不到 YAML 配置文件 '{yaml_config_file}'。")
        return False

    with open(yaml_config_file, 'r') as file:
        yaml_config = yaml.safe_load(file)

    return yaml_config.get('antirecoil', False)


# 读取配置文件
config = configparser.ConfigParser()
config_file = 'settings.config'

if not os.path.isfile(config_file):
    print(f"错误：找不到配置文件 '{config_file}'。")
    exit(1)

config.read(config_file)

# 初始化配置参数
current_profile = 'Profile1'
x_movement = 0.00  # 开始时设置为中心值
y_movement = 0.00  # 开始时设置为中心值
toggle_key = win32con.VK_XBUTTON2  # 使用鼠标的 X2 按钮


# 加载初始化配置设置
def load_profile(profile):
    global config, x_movement, y_movement
    try:
        if profile not in config:
            raise KeyError(f"在配置文件中没找到 {profile} 配置。")
        name = config[profile]['name']
        x_movement = float(config[profile]['x_movement'])
        y_movement = float(config[profile]['y_movement'])
        print(f"已加载配置: {name}")
    except KeyError as e:
        print(f"错误：{e}")
        exit(1)
    except ValueError as e:
        print(f"'{profile}' 配置错误：{e}")
        exit(1)


# 保存当前配置
def save_current_profile():
    global config, current_profile, x_movement, y_movement
    config[current_profile]['x_movement'] = f"{x_movement:.2f}"
    config[current_profile]['y_movement'] = f"{y_movement:.2f}"
    with open(config_file, 'w') as configfile:
        config.write(configfile)
    print(f"{current_profile} 已保存，x_movement: {x_movement:.2f}, y_movement: {y_movement:.2f}")


# 切换配置
def switch_profile(profile):
    global current_profile
    current_profile = profile
    load_profile(current_profile)


# 增加 y 方向的移动距离
def increase_y_movement():
    global y_movement
    y_movement = min(y_movement + 0.01, 25.00)
    print(f"y_movement 已增加到: {y_movement:.2f}")


# 减少 y 方向的移动距离
def decrease_y_movement():
    global y_movement
    y_movement = max(y_movement - 0.01, -25.00)
    print(f"y_movement 已减少到: {y_movement:.2f}")


# 增加 x 方向的移动距离
def increase_x_movement():
    global x_movement
    x_movement = min(x_movement + 0.01, 25.00)
    print(f"x_movement 已增加到: {x_movement:.2f}")


# 减少 x 方向的移动距离
def decrease_x_movement():
    global x_movement
    x_movement = max(x_movement - 0.01, -25.00)
    print(f"x_movement 已减少到: {x_movement:.2f}")


# 控制反后坐力
def control_recoil():
    global toggle_key, x_movement, y_movement
    recoil_compensation_factor = 2  # 调节向下补偿的因子
    quick_start_compensation = 3  # 前几枪立即补偿
    dynamic_factor = 2  # 开始时强烈的补偿减少率

    shots_fired = 0
    running = True

    keyboard.add_hotkey('up', increase_y_movement)
    keyboard.add_hotkey('down', decrease_y_movement)
    keyboard.add_hotkey('right', increase_x_movement)
    keyboard.add_hotkey('left', decrease_x_movement)
    keyboard.add_hotkey('enter', save_current_profile)
    keyboard.add_hotkey('pgup', lambda: switch_profile(get_next_profile()))
    keyboard.add_hotkey('pgdown', lambda: switch_profile(get_previous_profile()))

    while True:
        if win32api.GetAsyncKeyState(toggle_key):
            running = not running
            print("反后坐力补偿：", '打开' if running else '关闭')
            time.sleep(0.3)  # 抖动消除延迟

        if running and win32api.GetAsyncKeyState(0x01) != 0:  # 左鼠标按键被按下
            # 使用缩放因子将 x_movement 和 y_movement 实现更好的精度控制
            move_x = int(x_movement * 10)  # 根据需要调节因子
            move_y = int(y_movement * 10)  # 根据需要调节因子
            win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, move_x, move_y, 0, 0)
            shots_fired += 1
            dynamic_factor = max(dynamic_factor - 0.05, 1.0)  # 减小减弱速度

        time.sleep(0.1)  # 每10毫秒休眠以减小 CPU 利用率和控制应用程序的频率


def get_next_profile():
    current_profile_index = int(current_profile.replace("Profile", ""))
    next_profile_index = (current_profile_index % 9) + 1
    return f"Profile{next_profile_index}"


def get_previous_profile():
    current_profile_index = int(current_profile.replace("Profile", ""))
    previous_profile_index = (current_profile_index - 2) % 9 + 1
    return f"Profile{previous_profile_index}"


def start_control_recoil_thread():
    if is_antirecoil_enabled():
        recoil_thread = threading.Thread(target=control_recoil)
        recoil_thread.daemon = True
        recoil_thread.start()
    else:
        print("反后坐力已禁用，线程未启动。")


# 当模块被导入时，加载初始化配置
load_profile(current_profile)
