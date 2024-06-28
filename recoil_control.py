import time
import win32api
import win32con
import keyboard
import configparser
import os
import threading

# Ler configuração do perfil
config = configparser.ConfigParser()
config_file = 'settings.config'

if not os.path.isfile(config_file):
    print(f"Error: Configuration file '{config_file}' not found.")
    exit(1)

config.read(config_file)

# Variáveis de perfil iniciais
current_profile = 'Profile1'
x_movement = 0.00  # Começando com o valor neutro
y_movement = 0.00  # Começando com o valor neutro
toggle_key = win32con.VK_HOME  # Botão Home do teclado

# Carregar configurações de perfil inicial
def load_profile(profile):
    global config, x_movement, y_movement
    try:
        if profile not in config:
            raise KeyError(f"Profile {profile} not found in the configuration file.")
        name = config[profile]['name']
        x_movement = float(config[profile]['x_movement'])
        y_movement = float(config[profile]['y_movement'])
        print(f"Loaded profile: {name}")
    except KeyError as e:
        print(f"Error: {e}")
        exit(1)
    except ValueError as e:
        print(f"Error in profile '{profile}': {e}")
        exit(1)

def save_current_profile():
    global config, current_profile, x_movement, y_movement
    config[current_profile]['x_movement'] = f"{x_movement:.2f}"
    config[current_profile]['y_movement'] = f"{y_movement:.2f}"
    with open(config_file, 'w') as configfile:
        config.write(configfile)
    print(f"{current_profile} saved with x_movement: {x_movement:.2f}, y_movement: {y_movement:.2f}")

def switch_profile(profile):
    global current_profile
    current_profile = profile
    load_profile(current_profile)

def increase_y_movement():
    global y_movement
    y_movement = min(y_movement + 0.01, 25.00)
    print(f"y_movement increased to: {y_movement:.2f}")

def decrease_y_movement():
    global y_movement
    y_movement = max(y_movement - 0.01, -25.00)
    print(f"y_movement decreased to: {y_movement:.2f}")

def increase_x_movement():
    global x_movement
    x_movement = min(x_movement + 0.01, 25.00)
    print(f"x_movement increased to: {x_movement:.2f}")

def decrease_x_movement():
    global x_movement
    x_movement = max(x_movement - 0.01, -25.00)
    print(f"x_movement decreased to: {x_movement:.2f}")

def control_recoil():
    global toggle_key, x_movement, y_movement
    recoil_compensation_factor = 2  # Ajustar conforme necessário para compensação para baixo
    quick_start_compensation = 3  # Compensação imediata para as primeiras balas
    dynamic_factor = 2  # Começar com uma compensação forte e diminuir

    shots_fired = 0
    running = False

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
            print("Recoil Compensation: ", 'On' if running else 'Off')
            time.sleep(0.3)  # Debounce delay

        if running and win32api.GetAsyncKeyState(0x01) != 0:  # Botão esquerdo do mouse pressionado
            # Aplicar x_movement e y_movement com um fator de escala para melhor precisão
            move_x = int(x_movement * 10)  # Ajustar o fator conforme necessário
            move_y = int(y_movement * 10)  # Ajustar o fator conforme necessário
            win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, move_x, move_y, 0, 0)
            shots_fired += 1
            dynamic_factor = max(dynamic_factor - 0.05, 1.0)  # Diminuir a taxa de decréscimo lentamente

        time.sleep(0.1)  # Dormir por 10 milissegundos para reduzir o uso da CPU e controlar a taxa de aplicação

def get_next_profile():
    current_profile_index = int(current_profile.replace("Profile", ""))
    next_profile_index = (current_profile_index % 9) + 1
    return f"Profile{next_profile_index}"

def get_previous_profile():
    current_profile_index = int(current_profile.replace("Profile", ""))
    previous_profile_index = (current_profile_index - 2) % 9 + 1
    return f"Profile{previous_profile_index}"

# Carregar perfil inicial quando o módulo é importado
load_profile(current_profile)
