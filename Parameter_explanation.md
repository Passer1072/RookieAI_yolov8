| 参数名称 | 类型 | 范围 | 解释 | 默认值 |
|:---:|:---:|:---:|:---:|:---:|
| **log_level** | `str` | - | 控制台输出的日志等级 | `info`|
| **aim_range** | `int` | ∞ | 自瞄范围 | `150`|
| **aimBot** | `bool` | - | 自瞄启用状态 | `True` |
| **confidence** | `float` | [0, 1] | 模型识别的置信度 | `0.3` |
| **aim_speed_x** | `float` | ∞ | X轴基础瞄准速度 | `6.7` |
| **aim_speed_y** | `float` | ∞ | Y轴基础瞄准速度 | `8.3`|
| **model_file**v| `str` | - | 模型文件路径 | - |
| **mouse_Side_Button_Witch** | `bool` | - | 侧键自瞄开关状态 | `True` |
| **ProcessMode** | `str` | [`single_process`, `multi_process`] | 推理进程模式 | `multi_process` |
| **window_always_on_top** | `bool` | - | 应用窗口是否置顶 | `False` |
| **target_class** | `str` | ∞ | 所使用模型中需要检测的类别 | `0` |
| **lockKey** | `str` | - | 自瞄热键 | `VK_RBUTTON` |
| **triggerType** | `str` | - | 自瞄触发方式 | `按下` |
| **offset_centery** | `float` | ∞ | Y轴瞄准偏移 | `0.75` |
| **offset_centerx** | `float` | ∞ | X轴瞄准偏移 | `0.0` |
| **screen_pixels_for_360_degrees** | `int` | ∞ | 游戏内X轴360度视角像素 | `6550` |
| **screen_height_pixels** | `int` | ∞ | 游戏内Y轴180度视角像素 | `3220` |
| **near_speed_multiplier** | `float` | ∞ | 近点瞄准速度倍率 | `2.5` |
| **slow_zone_radius** | `int` | ∞ | 瞄准减速区域 | `0` |
| **mouseMoveMode** | `str` | - | 鼠标移动方式 | `win32` |
| **lockSpeed** | `float` | ∞ | 自瞄速度 | `5.5` |
