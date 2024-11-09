# 初始化DXcam最大FPS
dxcam_maxFPS = 30
deactivate_dxcam = False  # 是否禁止加载dxcam

# onnx模型开关
half_precision_model = False

# 颜色忽略部分
tolerance = 80  # Default value
ignore_colors = [[62, 203, 236]]  # Default value, list of BGR tuples

# 自瞄范围
closest_mouse_dist = 100

# 置信度设置
confidence = 0.65

# 垂直瞄准偏移
aimOffset = 0.5

# 停止自瞄范围（百分比）
stop_aim = 1
stop_aim_variety = None  # 变化值
stop_aim_target = 0  # 目标值
stop_aim_variety_state = True  # 停止自瞄范围是否需要回到默认值
slow_aim_speed = 0.5  # 初始化慢速（停止）瞄准数值
expansion_ratio = 1.5  # 扩张强锁范围面积%

# 水平瞄准偏移。最左为1，最右为-1，中间（默认）为0，可为小数
aimOffset_Magnification_x = 0

# 水平瞄准偏移
aimOffset_x = 0

# 预测因子
prediction_factor = 0.1

# 跟踪目标的上一个位置（在程序运行中保存和更新）
previous_centerx = 0
previous_centery = 0

# 鼠标移动平滑
mouse_movement_smoothing_switch = False  # 鼠标移动平滑开关
threshold = 2.0  # threshold: 检测目标是否“停止”的速度阈值。
slowDownFactor = 0.3  # slowDownFactor: 目标停止时的减速因子。
# 预设的阈值和参数
reverse_threshold_x = 4  # 短时间内反向移动的阈值 x 轴
reverse_threshold_y = 2  # 短时间内反向移动的阈值 y 轴
smoothing_factor = 0.6  # 平滑因子，接近1表示更平滑的跟踪
# 新倍率预测：记录上一个方向的目标偏移量和时间
previous_direction = None
transition_start_x = None
transition_duration = 10  # 过渡时间（帧数或时间单位）
direction = "静止"
coordinate_movement_switch = False  # 坐标移动模式开关
# 定义稀疏流光缓存用于存储5次推理结果
direction_cache = []

# 软件页面大小
_win_width = 350
_win_height = 825

# 识别对象限制（敌我识别）
classes = 0

# 锁定对象ID
locked_id = None

# 分阶段瞄准
stage1_scope = 55  # 强锁范围
stage1_intensity = 0.8  # 强锁力度
stage2_scope = 170  # 软锁范围
stage2_intensity = 0.4  # 软锁力度

# 初始化压枪参数
recoil_switch = False  # 压枪开关
recoil_interval = 0.01  # 压枪间隔（s）
recoil_boosted_distance_time = 0.5  # 一阶段时间
recoil_boosted_distance = 4  # 一阶段力度
recoil_standard_distance = 1  # 二阶段力度
recoil_transition_time = 0.2  # 一阶段到二阶段缓冲时间

# 跟踪框ID相关变量
counter_id = 0  # 分配唯一 ID 的计数器
buffer_tracks = {}  # 保存位置和时间的元组
last_updated = {}  # 初始化 last_updated 字典
identification_range = 30  # 连续框判断误差（像素）
unupdated_timeout = 0.1  # 未更新的轨迹存在时间（秒）
crossed_boxes = {}

# 分段瞄准开关
segmented_aiming_switch = False

# 是否开启外部测试窗口（小幅影响性能）
test_window_frame = False

# 是否打开内部测试画面（大幅影响性能）
test_images_GUI = False

# 是否跳过公告获取
crawl_information = False

# 初始化加载成功标识
loaded_successfully = False

# 自动扳机开关
automatic_Trigger = False

# 选择鼠标控制方式
mouse_control = 'win32'

# 飞易来U盘设置
u_vid = 0x1532
u_pid = 0x98


# 目标列表
num_classes = 10  # 假设模型识别10个类别
target_all = list(range(num_classes))
target_mapping = {'敌人': 0, '倒地': 1, '队友': 2, '全部': target_all}
# 定义触发器类型和其他参数
# 在全局范围声明 GUI 控件的变量
aimbot_var = None
circle_var = None
lockSpeed_scale = None
triggerType_var = None
arduinoMode_var = None
lockKey_var = None
confidence_scale = None
closest_mouse_dist_scale = None
screen_width_scale = None
screen_height_scale = None
root = None
aimOffset_scale = None
mouse_Side_Button_Witch_var = None
value_label = None
LookSpeed_label_text = None
target_selection = None
target_selection_var = None
target_selection_str = None
method_of_prediction_var = None
readme_content = ""
random_offset_mode_var = None

# 其他全局变量
Thread_to_join = None
restart_thread = False
run_threads = True
draw_center = True
random_name = False
dll_lg_loaded = False  # 初始化lg_dll加载标识符
recoil_start_time = None

# 随机偏移Y轴状态变量
current_target = None
current_target_dist = float('inf')
aim_offset_x = 0
aim_offset_y = 0
offset_range = (0, 1)  # 偏移范围
time_interval = 0.5  # 时间间隔，单位：秒
enable_random_offset = False  # 随机偏移功能开关
# 截图模式（请勿更改）
screenshot_mode = False

# MSS默认截图长宽(像素)
screen_width = 640
screen_height = 640

# DXcam截图分辨率
DXcam_screenshot = 360