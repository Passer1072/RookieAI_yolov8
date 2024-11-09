| 参数名称 | 类型 | 范围 | 解释 | 建议值 |
|:---:|:---:|:---:|:---:|:---:|
| DXcam_screenshot | int | 无限 | 设置DXcam截图时的截图范围大小，建议不要设置太大。 | 560 |
| aimOffset | float | 0-1 | 设置自瞄的高度，数字越大越接近目标的头部。0为自瞄框的中点，1为最高点。 | 0.4 |
| aimbot | bool | true / false | 开关自瞄功能。 | true |
| arduinoMode | bool | true / false | 控制其他鼠标移动模式的参数，当前未启用。 | false |
| closest_mouse_dist | float | 0-300 | 设置正常瞄准模式下的自瞄范围。可通过GUI设置。 | 160 |
| confidence | float | 0-1 | 目标识别的置信度，过高可能丢失目标，过低可能错误识别其他物体为目标。 | 0.6 |
| crawl_information | bool | true / false | 从GitHub获取README文件中的更新公告和版本号，可能会影响启动速度。 | false |
| dxcam_maxFPS | integer | 0-240 | 设置DXcam截图模式下的最大帧率。过高的帧率会增加延迟。 | 30 |
| extra_offset_x | float | 0-20 | 修正截图延迟引起的目标偏差，调整瞄准速度。过大可能导致抖动。 | 5 |
| extra_offset_y | float | 0-20 | 修正截图延迟引起的目标偏差，调整瞄准速度，合理的值可以改善锁定目标时的压枪效果。 | 4 |
| lockKey | string | '左键', '右键', '下侧键' | 设置触发自瞄的热键。 | '右键' |
| lockSpeed | float | 0-1 | 调整正常瞄准模式下的自瞄速度。过快可能导致被检测。 | 0.5 |
| method_of_prediction | string | '禁用预测', '倍率预测', '像素预测' | 设置自瞄的预测方法。 | '像素预测' |
| model_file | string | 略 | 存储自定义模型的文件路径。 | 略 |
| mouse_Side_Button_Witch | bool | true / false | 控制鼠标下侧键的自瞄开关。 | true |
| prediction_factor | float | 0-1 | '倍率预测'的倍率设置。 | 0.4 |
| screen_height | float | 100-2000 | 设置截图的高度，较高会降低截图帧率。 | 560 |
| screen_width | float | 100-2000 | 设置截图的宽度，较高会降低截图帧率。 | 560 |
| screenshot_mode | integer | 1, 2 | 1为mss截图模式，2为基于DXcam的截图模式。 | 1 |
| test_images_GUI | bool | true / false | 启用调试图像显示，可能影响性能。 | false |
| test_window_frame | bool | true / false | 启用外部调试窗口，可能影响性能。 | false |
| triggerType | string | '按下', '切换', 'shift+按下' | 设置触发自瞄的方式。 | 'shift+按下' |
| segmented_aiming_switch | bool | true / false | 开启分段瞄准模式，适用于精细瞄准。 | true |
| stage1_scope | integer | 无限 | 设置分段瞄准内圈的范围。 | 50 |
| stage1_intensity | float | 0-1 | 设置分段瞄准内圈的瞄准速度。 | 0.78 |
| stage2_scope | integer | 无限 | 设置分段瞄准外圈的范围。 | 170 |
| stage2_intensity | float | 0-1 | 设置分段瞄准外圈的瞄准速度。 | 0.4 |
| aimOffset_Magnification_x | float | -1~1 | 微调水平方向的瞄准位置。 | 0 |
| offset_range | tuple | 0-1 | 设置随机偏移的范围。 | [0, 1] |
| time_interval | float / int| >= 0 | 设置随机偏移的时间间隔。 | 1 |
| enable_random_offset | bool | true / false | 启用随机瞄准偏移功能。 | true |
