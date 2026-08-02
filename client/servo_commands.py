# servo_commands.py - 舵机命令处理

# servo_commands.py

import time
from machine import Timer

from info_commands import get_help_info
from config import load_servo_config, save_servo_config, load_system_config, save_system_config, check_pin_conflicts
from util import get_used_pins, pin_claim, pin_release

# ---------- 异步播放状态 ----------
_playback_state = {
    "active": False,          # 是否正在播放
    "ctrl": None,             # ServoController 对象
    "angles": [],             # 角度列表
    "index": 0,               # 当前执行到的下标
    "timer": None,            # Timer 对象
    "stop_requested": False,  # 外部请求停止标志
    "interval_ms": 700,       # 每个角度之间的间隔（毫秒）
}

def _playback_step(timer):
    """
    定时器回调函数：执行一个角度，并决定是否继续或结束。
    注意：此回调在中断上下文中运行，应避免分配内存、打印大量信息。
    """
    state = _playback_state
    if not state["active"] or state["stop_requested"]:
        # 停止播放
        state["active"] = False
        if state["timer"]:
            state["timer"].deinit()
            state["timer"] = None
        return

    # 执行当前角度
    ctrl = state["ctrl"]
    angles = state["angles"]
    idx = state["index"]
    if idx >= len(angles):
        # 播放完成
        state["active"] = False
        if state["timer"]:
            state["timer"].deinit()
            state["timer"] = None
        print("[舵机] 动作组播放完成")
        return

    # 设置角度（注意：PWM 操作在回调中通常安全，但不宜过长）
    try:
        ctrl.set_angle(angles[idx])
    except Exception as e:
        print(f"[舵机] 播放出错: {e}")
        state["active"] = False
        if state["timer"]:
            state["timer"].deinit()
            state["timer"] = None
        return

    state["index"] += 1

def start_playback(ctrl, angles, interval_ms=700):
    """
    启动一个异步播放任务。
    如果有正在播放的任务，会先停止它。
    """
    # 如果已有播放任务，先停止
    if _playback_state["active"]:
        stop_playback()
        # 等待旧定时器完全释放（微小延迟）
        time.sleep_ms(50)

    # 重置状态
    _playback_state["ctrl"] = ctrl
    _playback_state["angles"] = angles
    _playback_state["index"] = 0
    _playback_state["stop_requested"] = False
    _playback_state["active"] = True
    _playback_state["interval_ms"] = interval_ms

    # 创建定时器（模式为周期，但每次回调都会判断是否继续）
    tim = Timer(0)  # 使用 Timer 0，也可用 -1 自动分配
    tim.init(period=interval_ms, mode=Timer.PERIODIC, callback=_playback_step)
    _playback_state["timer"] = tim
    print(f"[舵机] 开始异步播放，共 {len(angles)} 个角度，间隔 {interval_ms}ms")

def stop_playback():
    """立即停止当前播放任务"""
    if _playback_state["active"]:
        _playback_state["stop_requested"] = True  # 通知回调退出
        # 等待回调自停，但为了保险，强行销毁定时器
        if _playback_state["timer"]:
            _playback_state["timer"].deinit()
            _playback_state["timer"] = None
        _playback_state["active"] = False
        print("[舵机] 播放已中断")

# 注意：此模块需要引用外部舵机控制器字典，由 main 注入
servo_controllers = None

def set_servo_controllers(ctrl_dict):
    global servo_controllers
    servo_controllers = ctrl_dict

def handle_servo_command(parts):
    if len(parts) < 2:
        return "错误: 缺少子命令"
    subcmd = parts[1].strip().lower()
    try:
        if subcmd == "help":
            return get_help_info("servo")
        elif subcmd == "list":
            if not servo_controllers:
                return "暂无舵机"
            lines = ["舵机列表:"]
            servo_config = load_servo_config()
            for name, ctrl in servo_controllers.items():
                init_ang = servo_config.get(name, {}).get("init_angle", 90)
                lines.append(f"  {name}: GPIO{ctrl.pin}, 初始化角度={init_ang}°")
            return "\n".join(lines)

        # ---------- set_pin ----------
        elif subcmd == "set_pin":
            if len(parts) < 4:
                return "错误: 缺少参数，格式: servo,set_pin,<舵机名称>,<引脚>"
            name = parts[2].strip()
            try:
                new_pin = int(parts[3])
            except:
                return "错误: 引脚必须是整数"
            # 基础合法性校验（沿用你的原有逻辑）
            if new_pin < 0 or new_pin > 21 or new_pin in range(12, 18):
                return "错误: 引脚无效或为 Flash 专用引脚"
            # 加载配置并获取旧引脚
            servo_config = load_servo_config()
            old_pin = None
            if name in servo_config:
                old_pin = servo_config[name].get("pin")
            if old_pin == new_pin:
                return f"舵机 '{name}' 已经是 GPIO{new_pin}"
            # 检查引脚冲突（静态配置），排除自身
            conflict_info = check_pin_conflicts(new_pin, exclude_owners=[f"舵机-{name}"])
            if conflict_info['has_conflict']:
                # 提取冲突详情
                for p, owners in conflict_info['conflicts'].items():
                    owner_str = ', '.join([f"{o[0]}({o[1]})" for o in owners])
                    return f"错误: GPIO{p} 已被占用: {owner_str}"
            # 1. 尝试申请新引脚
            ok, msg = pin_claim(new_pin, f"舵机-{name}")
            if not ok:
                return f"错误: {msg}"
            # 2. 更新配置对象
            if name not in servo_config:
                servo_config[name] = {"pin": new_pin, "init_angle": 90, "动作组": {}}
            else:
                servo_config[name]["pin"] = new_pin
                if "init_angle" not in servo_config[name]:
                    servo_config[name]["init_angle"] = 90
            # 3. 保存配置，失败则回滚
            if not save_servo_config(servo_config):
                pin_release(new_pin)
                return "保存舵机配置失败"
            # 4. 释放旧引脚（若存在且拥有者匹配）
            if old_pin is not None:
                used = get_used_pins()
                if used.get(old_pin) == f"舵机-{name}":
                    pin_release(old_pin)
            return f"舵机 '{name}' 引脚已设置为 GPIO{new_pin}，执行 config,reload 生效"

        elif subcmd == "set_init_angle":
            if len(parts) < 4:
                return "错误: 缺少参数，格式: servo,set_init_angle,<舵机名称>,<初始化角度>"
            name = parts[2].strip()
            try:
                init_angle = int(parts[3])
            except:
                return "错误: 角度必须是整数"
            if not (0 <= init_angle <= 180):
                return "错误: 角度必须在 0~180 之间"
            servo_config = load_servo_config()
            if name not in servo_config:
                return f"错误: 舵机 '{name}' 不存在，请先设置引脚"
            servo_config[name]["init_angle"] = init_angle
            if save_servo_config(servo_config):
                return f"舵机 '{name}' 初始化角度已设置为 {init_angle}°，执行 config,reload 生效"
            else:
                return "保存舵机配置失败"
        elif subcmd == "set":
            if len(parts) < 4:
                return "错误: 缺少参数，格式: servo,set,<舵机名称>,<角度>"
            name = parts[2].strip()
            try:
                angle = int(parts[3])
            except:
                return "错误: 角度必须是整数"
            if name not in servo_controllers:
                return f"错误: 未找到舵机 '{name}'，请检查配置或执行 config,reload"
            ctrl = servo_controllers[name]
            ctrl.set_angle(angle)
            return f"舵机 '{name}' 已转到 {angle}°"
        elif subcmd == "record":
            if len(parts) < 5:
                return "错误: 至少需要 舵机名称, 动作组名称, 一个角度"
            name = parts[2].strip()
            group_name = parts[3].strip()
            angle_strs = parts[4:]
            angles = []
            for s in angle_strs:
                try:
                    angles.append(int(s))
                except:
                    return f"错误: 无效角度 '{s}'"
            if not angles:
                return "错误: 至少需要一个角度"
            servo_config = load_servo_config()
            if name not in servo_config:
                return f"错误: 舵机 '{name}' 不存在，请先使用 servo,set_pin 创建"
            if "动作组" not in servo_config[name]:
                servo_config[name]["动作组"] = {}
            servo_config[name]["动作组"][group_name] = angles
            if save_servo_config(servo_config):
                return f"动作组 '{group_name}' 已保存到舵机 '{name}'，共 {len(angles)} 个角度"
            else:
                return "保存舵机配置失败"

        # ---------- play ----------
        elif subcmd == "play":
            if len(parts) < 4:
                return "错误: 缺少参数，格式: servo,play,<舵机名称>,<动作组名称>"
            name = parts[2].strip()
            group_name = parts[3].strip()
            if name not in servo_controllers:
                return f"错误: 未找到舵机 '{name}'，请检查配置或执行 config,reload"
            ctrl = servo_controllers[name]
            servo_config = load_servo_config()
            if name not in servo_config:
                return f"错误: 舵机 '{name}' 不存在配置"
            groups = servo_config[name].get("动作组", {})
            if group_name not in groups:
                return f"错误: 舵机 '{name}' 下未找到动作组 '{group_name}'"
            angles = groups[group_name]
            if not angles:
                return f"错误: 动作组 '{group_name}' 为空"
            # 启动异步播放（使用默认 700ms 间隔）
            start_playback(ctrl, angles, interval_ms=700)
            return f"动作组 '{group_name}' 开始播放（异步）"

        elif subcmd == "delete_group":
            if len(parts) < 4:
                return "错误: 缺少参数，格式: servo,delete_group,<舵机名称>,<动作组名称>"
            name = parts[2].strip()
            group_name = parts[3].strip()
            servo_config = load_servo_config()
            if name not in servo_config:
                return f"错误: 舵机 '{name}' 不存在"
            if "动作组" in servo_config[name] and group_name in servo_config[name]["动作组"]:
                del servo_config[name]["动作组"][group_name]
                if save_servo_config(servo_config):
                    return f"动作组 '{group_name}' 已从舵机 '{name}' 删除"
                else:
                    return "保存舵机配置失败"
            else:
                return f"错误: 舵机 '{name}' 下未找到动作组 '{group_name}'"
        elif subcmd == "list_groups":
            if len(parts) < 3:
                return "错误: 缺少舵机名称"
            name = parts[2].strip()
            servo_config = load_servo_config()
            if name not in servo_config:
                return f"错误: 舵机 '{name}' 不存在"
            groups = servo_config[name].get("动作组", {})
            if not groups:
                return f"舵机 '{name}' 暂无动作组"
            lines = [f"舵机 '{name}' 的动作组:"]
            for gname, angles in groups.items():
                lines.append(f"  {gname}: {angles}")
            return "\n".join(lines)
        elif subcmd == "delete":
            if len(parts) < 3:
                return "错误: 缺少舵机名称，格式: servo,delete,<舵机名称>"
            name = parts[2].strip()
            servo_config = load_servo_config()
            if name not in servo_config:
                return f"错误: 舵机 '{name}' 不存在"
            if name in servo_controllers:
                pin = servo_controllers[name].pin
                servo_controllers[name].pwm.deinit()
                del servo_controllers[name]
                pin_release(pin)  # 释放引脚占用
            del servo_config[name]
            if not save_servo_config(servo_config):
                return "删除舵机配置失败"
            if name in servo_controllers:
                try:
                    servo_controllers[name].pwm.deinit()
                except:
                    pass
                del servo_controllers[name]
            return f"舵机 '{name}' 已删除（若已初始化，已释放）"
            # servo_commands.py - 修改 stop 分支

        elif subcmd == "stop":
            if _playback_state["active"]:
                # 获取正在播放的舵机名称（需要额外记录，或者从 ctrl 反查）
                # 这里我们简单处理：如果 state 中有 ctrl，可以尝试复位
                ctrl = _playback_state.get("ctrl")
                if ctrl:
                    # 从配置读取该舵机的 init_angle
                    servo_config = load_servo_config()
                    # 由于我们没有存 name，只能通过遍历查找，或者提前在 state 里存 name
                    # 建议在 start_playback 时同时保存 name，我这里演示查找方式：
                    for name, cfg in servo_config.items():
                        if cfg.get("pin") == ctrl.pin:
                            init_angle = cfg.get("init_angle", 90)
                            ctrl.set_angle(init_angle)
                            break
                stop_playback()
                return "舵机播放已停止，并复位到初始角度"
            else:
                return "当前没有正在播放的动作组"

    except Exception as e:
        return f"舵机操作异常: {e}"