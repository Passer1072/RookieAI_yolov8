# jump_detection.py

def check_target_switching(offset_distance, last_offset_distance, jump_detection_switch, fluctuation_range, target_switching):
    """
    判断是否发生目标切换

    参数:
    - offset_distance: 当前的目标偏移距离
    - last_offset_distance: 上一次的目标偏移距离
    - jump_detection_switch: 跳变检测开关，是否启用跳变检测
    - jump_suppression_fluctuation_range: 允许的波动范围（单位：像素）
    - target_switching: 记录状态。（鼠标按下时持续性禁止移动，直到松开）

    返回:
    - target_switching: 是否发生了目标切换 (True or False)
    """

    if last_offset_distance is not None and not target_switching:
        # 如果启用跳变检测
        if jump_detection_switch:
            # 判断是否有不规律的跳变，判断 offset_distance 是否突然增大
            if offset_distance > last_offset_distance + fluctuation_range:
                target_switching = True  # 判断为目标切换
                logger.debug("目标切换")
            else:
                target_switching = False  # 认为是正常的规律移动
                logger.debug("正常移动")
        else:
            # 如果不启用跳变检测，则认为是正常移动
            target_switching = False
            logger.debug("正常移动")

    return target_switching
