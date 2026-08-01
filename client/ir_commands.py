# ir_commands.py - IR05T 命令处理

from config import (
    get_ir_data, set_ir_data, delete_ir_data, list_ir_names,
    is_valid_name, load_system_config, save_system_config
)
from util import get_used_pins, pin_release, pin_claim

# 此模块需要引用 IR05T 对象，由 main 注入
ir = None
# 改为字典，存储 设备名 -> IR05T 实例
ir_instances = {}

def set_ir_instances(inst_dict):
    global ir_instances
    ir_instances = inst_dict

def set_ir_object(ir_obj):
    global ir
    ir = ir_obj

def handle_ir05t_command(parts):
    if len(parts) < 2:
        return "错误: 缺少子命令"
    subcmd = parts[1].strip().lower()
    try:
        if subcmd == "learn" and len(parts) >= 4 and parts[2].lower() == "save":
            name = parts[3].strip()
            if not name:
                return "错误: 名称不能为空"
            if not is_valid_name(name):
                return "错误: 名称只能包含字母、数字和下划线"
            print(f"[IR] 开始学习并保存到 '{name}'...")
            data = ir.learn()
            if data:
                hex_str = data.hex().upper()
                if set_ir_data(name, hex_str):
                    return f"学习成功，数据已保存为 '{name}'，长度 {len(data)} 字节"
                else:
                    return "学习成功但保存失败"
            else:
                return "学习失败（超时或无信号）"
        elif subcmd == "learn":
            data = ir.learn()
            if data:
                return f"通用学习成功，数据长度 {len(data)} 字节"
            else:
                return "通用学习失败（超时或无信号）"
        elif subcmd == "list":
            names = list_ir_names()
            if names:
                return "已保存的名称列表:\n" + "\n".join(f"  {n}" for n in names)
            else:
                return "暂无已保存的红外数据"
        elif subcmd == "get":
            if len(parts) < 3:
                return "错误: 缺少名称"
            name = parts[2].strip()
            hex_data = get_ir_data(name)
            if hex_data is not None:
                return f"名称 '{name}' 的数据:\n{hex_data}"
            else:
                return f"错误: 未找到名称 '{name}'"
        elif subcmd == "send":
            if len(parts) < 3:
                return "错误: 缺少名称"
            name = parts[2].strip()
            hex_data = get_ir_data(name)
            if hex_data is None:
                return f"错误: 未找到名称 '{name}'"
            try:
                data_bytes = bytes.fromhex(hex_data)
                if ir.send_raw(data_bytes):
                    return f"成功发射 '{name}' 红外信号"
                else:
                    return f"发射 '{name}' 失败"
            except ValueError:
                return f"错误: 名称 '{name}' 的数据格式无效"
        elif subcmd == "delete":
            if len(parts) < 3:
                return "错误: 缺少名称"
            name = parts[2].strip()
            if delete_ir_data(name):
                return f"已删除名称 '{name}'"
            else:
                return f"错误: 未找到名称 '{name}'"
        elif subcmd == "learn_channel":
            if len(parts) < 3:
                return "错误: 缺少通道号"
            try:
                channel = int(parts[2])
            except:
                return "错误: 通道号必须是数字"
            if ir.learn_channel(channel):
                return f"通道 {channel} 已进入学习状态，请按下遥控器"
            else:
                return f"通道 {channel} 学习启动失败"
        elif subcmd == "send_channel":
            if len(parts) < 3:
                return "错误: 缺少通道号"
            try:
                channel = int(parts[2])
            except:
                return "错误: 通道号必须是数字"
            if ir.send_channel(channel):
                return f"通道 {channel} 发射成功"
            else:
                return f"通道 {channel} 发射失败"
        elif subcmd == "send_raw":
            if len(parts) < 3:
                return "错误: 缺少十六进制数据"
            hex_str = parts[2].strip().replace(" ", "")
            try:
                data = bytes.fromhex(hex_str)
                if ir.send_raw(data):
                    return "原始数据发射成功"
                else:
                    return "原始数据发射失败"
            except ValueError:
                return "错误: 无效的十六进制数据"
        elif subcmd == "set_baud":
            if len(parts) < 3:
                return "错误: 缺少波特率"
            try:
                baud = int(parts[2])
            except:
                return "错误: 波特率必须是整数"
            if ir.set_baudrate(baud):
                return f"波特率已修改为 {baud}，下次上电生效"
            else:
                return "修改波特率失败"
        elif subcmd == "set_header":
            if len(parts) < 3:
                return "错误: 缺少帧头字节"
            try:
                header_byte = int(parts[2], 16)
            except:
                return "错误: 帧头必须是十六进制数"
            if ir.set_frame_header(header_byte):
                return f"帧头已修改为 0x{header_byte:02X}，后续指令需使用新帧头"
            else:
                return "修改帧头失败"
        elif subcmd == "set_timeout":
            if len(parts) < 3:
                return "错误: 缺少超时时间（毫秒）"
            try:
                timeout_ms = int(parts[2])
                if timeout_ms < 100:
                    return "错误: 超时时间至少为 100ms"
            except ValueError:
                return "错误: 超时时间必须是整数"
            ir.set_timeout(timeout_ms)
            return f"IR 读取超时已设为 {timeout_ms}ms（立即生效）"
        # ---------- set_tx ----------
        elif subcmd == "set_tx":
            if len(parts) < 3:
                return "错误: 缺少引脚号"
            try:
                new_pin = int(parts[2])
            except:
                return "错误: 引脚号必须是整数"
            # 1. 获取当前配置中的旧引脚
            sys_cfg = load_system_config()
            old_pin = sys_cfg.get("ir_tx_pin")
            if old_pin == new_pin:
                return f"IR TX 引脚已经是 GPIO{new_pin}"
            # 2. 尝试申请新引脚（防止被其他外设占用）
            ok, msg = pin_claim(new_pin, "IR05T_TX")
            if not ok:
                return f"错误: {msg}"
            # 3. 保存配置（若保存失败，回滚释放新引脚）
            sys_cfg["ir_tx_pin"] = new_pin
            if not save_system_config(sys_cfg):
                pin_release(new_pin)
                return "保存系统配置失败"
            # 4. 释放旧引脚（仅当拥有者是 IR05T_TX 时，防止误删）
            if old_pin is not None:
                used = get_used_pins()
                if used.get(old_pin) == "IR05T_TX":
                    pin_release(old_pin)
            return f"IR TX 引脚已设置为 GPIO{new_pin}，执行 config,reload 生效"

        # ---------- set_rx ----------
        elif subcmd == "set_rx":
            if len(parts) < 3:
                return "错误: 缺少引脚号"
            try:
                new_pin = int(parts[2])
            except:
                return "错误: 引脚号必须是整数"
            sys_cfg = load_system_config()
            old_pin = sys_cfg.get("ir_rx_pin")
            if old_pin == new_pin:
                return f"IR RX 引脚已经是 GPIO{new_pin}"
            ok, msg = pin_claim(new_pin, "IR05T_RX")
            if not ok:
                return f"错误: {msg}"
            sys_cfg["ir_rx_pin"] = new_pin
            if not save_system_config(sys_cfg):
                pin_release(new_pin)
                return "保存系统配置失败"
            if old_pin is not None:
                used = get_used_pins()
                if used.get(old_pin) == "IR05T_RX":
                    pin_release(old_pin)

            return f"IR RX 引脚已设置为 GPIO{new_pin}，执行 config,reload 生效"
        else:
            return f"未知 IR05T 子命令: {subcmd}"
    except Exception as e:
        return f"IR05T 操作异常: {e}"