# SPDX-License-Identifier: GPL-3.0-only
# SPDX-FileCopyrightText: 2026 lanyangyin <2436725966@qq.com>
#
# This file is part of the ESP32-C3 Multi-Function Control Platform project.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
# ir_commands.py - IR05T 多设备命令处理
from info_commands import get_help_info
from config import (
    get_ir_device, set_ir_device, delete_ir_device,
    list_ir_devices, get_ir_data, set_ir_data,
    delete_ir_data, list_ir_data_names,
    check_pin_conflicts,load_ir_config, save_ir_config
)
from util import pin_claim, pin_release, is_safe_name
from ir05t import IR05T
from constants import DEFAULT_IR_BAUDRATE, DEFAULT_IR_TIMEOUT

# 全局字典：设备名 -> IR05T 实例
ir_instances = {}

def set_ir_instances(inst_dict):
    """由 app.py 注入已初始化的 IR 实例字典"""
    global ir_instances
    ir_instances = inst_dict

def _get_ir_obj(dev_name):
    """获取设备实例，若不存在返回 None"""
    return ir_instances.get(dev_name)

def handle_ir05t_command(parts):
    """
    处理 IR05T 命令（格式见 control_config.json 中的帮助）
    所有需要操作设备的命令都必须指定设备名。
    """
    if len(parts) < 2:
        return "错误: 缺少子命令"

    subcmd = parts[1].strip().lower()

    # ---------- 设备管理命令（无需设备名） ----------
    if subcmd == "list_devices":
        devs = list_ir_devices()
        if not devs:
            return "暂无 IR 设备"
        lines = ["IR 设备列表:"]
        for name in devs:
            cfg = get_ir_device(name)
            status = "已初始化" if name in ir_instances else "未初始化"
            lines.append(f"  {name} (TX={cfg['tx_pin']}, RX={cfg['rx_pin']}) - {status}")
        return "\n".join(lines)

    if subcmd == "add":
        # 格式: ir05t,add,<设备名>,<tx_pin>,<rx_pin>[,<baudrate>[,<timeout>[,<uart_id>]]]
        if len(parts) < 5:
            return "错误: 格式 ir05t,add,<设备名>,<tx_pin>,<rx_pin>[,<baudrate>[,<timeout>[,<uart_id>]]]"
        name = parts[2].strip()
        try:
            tx_pin = int(parts[3])
            rx_pin = int(parts[4])
            baudrate = int(parts[5]) if len(parts) > 5 else DEFAULT_IR_BAUDRATE
            timeout = int(parts[6]) if len(parts) > 6 else DEFAULT_IR_TIMEOUT
            uart_id = int(parts[7]) if len(parts) > 7 else 1
        except ValueError:
            return "错误: 参数必须是整数"
        # 检查是否存在
        if get_ir_device(name):
            return f"错误: 设备 '{name}' 已存在"
        # 检查引脚冲突
        conflict = check_pin_conflicts(tx_pin)
        if conflict['has_conflict']:
            return f"错误: TX 引脚 {tx_pin} 被占用"
        conflict = check_pin_conflicts(rx_pin)
        if conflict['has_conflict']:
            return f"错误: RX 引脚 {rx_pin} 被占用"
        # 保存配置（包含 uart_id）
        if not set_ir_device(name, tx_pin, rx_pin, baudrate, timeout, uart_id):
            return "保存配置失败"
        # 申请引脚
        ok, msg = pin_claim(tx_pin, f"IR-{name}-TX")
        if not ok:
            delete_ir_device(name)
            return f"错误: {msg}"
        ok, msg = pin_claim(rx_pin, f"IR-{name}-RX")
        if not ok:
            pin_release(tx_pin)
            delete_ir_device(name)
            return f"错误: {msg}"
        # 初始化
        try:
            obj = IR05T(uart_id=uart_id, tx_pin=tx_pin, rx_pin=rx_pin,
                        baudrate=baudrate, timeout=timeout)
            ir_instances[name] = obj
            return f"设备 '{name}' 已添加并初始化"
        except Exception as e:
            pin_release(tx_pin)
            pin_release(rx_pin)
            delete_ir_device(name)
            return f"初始化失败: {e}"
    if subcmd == "set_pin":
        if len(parts) < 5:
            return "错误: 格式 ir05t,set_pin,<设备名>,<tx_pin>,<rx_pin>[,<uart_id>]"
        dev_name = parts[2].strip()
        try:
            new_tx = int(parts[3])
            new_rx = int(parts[4])
            new_uart = int(parts[5]) if len(parts) > 5 else None
        except ValueError:
            return "错误: 引脚和 UART ID 必须是整数"
        # 获取当前配置
        cfg = get_ir_device(dev_name)
        if not cfg:
            return f"错误: 设备 '{dev_name}' 不存在"
        old_tx = cfg['tx_pin']
        old_rx = cfg['rx_pin']
        old_uart = cfg.get('uart_id', 1)
        # 检查新引脚冲突（排除自身）
        exclude = [f"IR-{dev_name}-TX", f"IR-{dev_name}-RX"]
        if new_tx != old_tx:
            conflict = check_pin_conflicts(new_tx, exclude_owners=exclude)
            if conflict['has_conflict']:
                return f"错误: TX 引脚 {new_tx} 被占用"
        if new_rx != old_rx:
            conflict = check_pin_conflicts(new_rx, exclude_owners=exclude)
            if conflict['has_conflict']:
                return f"错误: RX 引脚 {new_rx} 被占用"
        # 更新配置
        cfg['tx_pin'] = new_tx
        cfg['rx_pin'] = new_rx
        if new_uart is not None:
            cfg['uart_id'] = new_uart
        # 保存配置
        all_cfg = load_ir_config()
        all_cfg[dev_name] = cfg
        if not save_ir_config(all_cfg):
            return "保存配置失败"
        # 重新初始化
        obj = ir_instances.pop(dev_name, None)
        if obj:
            try:
                obj.deinit()
            except:
                pass
        # 释放旧引脚（确保是自身占用）
        if old_tx != new_tx:
            pin_release(old_tx)
        if old_rx != new_rx:
            pin_release(old_rx)
        # 申请新引脚
        ok, msg = pin_claim(new_tx, f"IR-{dev_name}-TX")
        if not ok:
            return f"错误: {msg}"
        ok, msg = pin_claim(new_rx, f"IR-{dev_name}-RX")
        if not ok:
            pin_release(new_tx)
            return f"错误: {msg}"
        # 创建新实例
        baudrate = cfg.get('baudrate', DEFAULT_IR_BAUDRATE)
        timeout = cfg.get('timeout', DEFAULT_IR_TIMEOUT)
        uart_id = cfg.get('uart_id', 1)
        try:
            new_obj = IR05T(uart_id=uart_id, tx_pin=new_tx, rx_pin=new_rx,
                            baudrate=baudrate, timeout=timeout)
            ir_instances[dev_name] = new_obj
            return f"设备 '{dev_name}' 引脚已更新并重新初始化"
        except Exception as e:
            pin_release(new_tx)
            pin_release(new_rx)
            return f"初始化失败: {e}"
    if subcmd == "delete":
        if len(parts) < 3:
            return "错误: 缺少设备名"
        name = parts[2].strip()
        if not get_ir_device(name):
            return f"错误: 设备 '{name}' 不存在"
        # 释放实例和引脚
        obj = ir_instances.pop(name, None)
        if obj:
            try:
                obj.deinit()
            except:
                pass
        cfg = get_ir_device(name)
        if cfg:
            pin_release(cfg['tx_pin'])
            pin_release(cfg['rx_pin'])
        # 删除配置
        if delete_ir_device(name):
            return f"设备 '{name}' 已删除"
        else:
            return "删除配置失败"
    # ---------- 帮助命令（无需设备名） ----------
    if subcmd == "help":
        return get_help_info("ir05t")

    # ---------- 需要设备名的操作命令 ----------
    if len(parts) < 3:
        return "错误: 缺少设备名"
    dev_name = parts[2].strip()
    obj = _get_ir_obj(dev_name)
    if obj is None:
        return f"错误: 设备 '{dev_name}' 未初始化，请先添加"

    # ---------- 通用学习（不保存） ----------
    if subcmd == "learn" and (len(parts) == 3 or (len(parts) == 4 and parts[3].lower() != "save")):
        data = obj.learn()
        if data:
            return f"学习成功， {data.hex().upper()} "
            # return f"学习成功，数据长度 {len(data)} 字节"
        else:
            return "学习失败（超时或无信号）"

    # ---------- 学习并保存 ----------
    if subcmd == "learn_save":
        if len(parts) < 4:
            return "错误: 缺少数据名，格式 ir05t,learn_save,<设备名>,<数据名>"
        dev_name = parts[2].strip()
        data_name = parts[3].strip()
        if not data_name:
            return "错误: 数据名不能为空"
        if not is_safe_name(data_name):
            return "错误: 数据名只能包含字母、数字和下划线"
        print(f"[IR] 设备 {dev_name} 学习并保存到 '{data_name}'...")
        data = obj.learn()
        if data:
            hex_str = data.hex().upper()
            if set_ir_data(dev_name, data_name, hex_str):
                return f"学习成功，数据已保存为 '{data_name}'，长度 {len(data)} 字节"
            else:
                return "学习成功但保存失败"
        else:
            return "学习失败（超时或无信号）"

    # ---------- 发送已保存数据 ----------
    if subcmd == "send":
        if len(parts) < 4:
            return "错误: 缺少数据名"
        data_name = parts[3].strip()
        hex_data = get_ir_data(dev_name, data_name)
        if hex_data is None:
            return f"错误: 设备 '{dev_name}' 下未找到数据 '{data_name}'"
        try:
            data_bytes = bytes.fromhex(hex_data)
            if obj.send_raw(data_bytes):
                return f"成功发送 '{data_name}'"
            else:
                return f"发送 '{data_name}' 失败"
        except ValueError:
            return f"错误: 数据 '{data_name}' 格式无效"

    # ---------- 列出该设备下所有数据 ----------
    if subcmd == "list":
        names = list_ir_data_names(dev_name)
        if not names:
            return f"设备 '{dev_name}' 暂无数据"
        return f"设备 '{dev_name}' 的数据:\n" + "\n".join(f"  {n}" for n in names)

    # ---------- 获取数据内容 ----------
    if subcmd == "get":
        if len(parts) < 4:
            return "错误: 缺少数据名"
        data_name = parts[3].strip()
        hex_data = get_ir_data(dev_name, data_name)
        if hex_data is None:
            return f"错误: 未找到数据 '{data_name}'"
        return f"数据 '{data_name}':\n{hex_data}"

    # ---------- 删除数据 ----------
    if subcmd == "delete_data":
        if len(parts) < 4:
            return "错误: 缺少数据名"
        data_name = parts[3].strip()
        if delete_ir_data(dev_name, data_name):
            return f"数据 '{data_name}' 已删除"
        else:
            return f"错误: 未找到数据 '{data_name}'"

    # ---------- 通道学习 ----------
    if subcmd == "learn_channel":
        if len(parts) < 4:
            return "错误: 缺少通道号"
        try:
            ch = int(parts[3])
            if not 1 <= ch <= 5:
                raise ValueError
        except ValueError:
            return "错误: 通道号必须是 1~5"
        if obj.learn_channel(ch):
            return f"通道 {ch} 学习已启动，请按遥控器"
        else:
            return f"通道 {ch} 学习启动失败"

    # ---------- 发送通道 ----------
    if subcmd == "send_channel":
        if len(parts) < 4:
            return "错误: 缺少通道号"
        try:
            ch = int(parts[3])
            if not 1 <= ch <= 5:
                raise ValueError
        except ValueError:
            return "错误: 通道号必须是 1~5"
        if obj.send_channel(ch):
            return f"通道 {ch} 发送成功"
        else:
            return f"通道 {ch} 发送失败"

    # ---------- 发送原始数据 ----------
    if subcmd == "send_raw":
        if len(parts) < 4:
            return "错误: 缺少十六进制数据"
        hex_str = parts[3].strip().replace(" ", "")
        try:
            data = bytes.fromhex(hex_str)
            if obj.send_raw(data):
                return "原始数据发送成功"
            else:
                return "原始数据发送失败"
        except ValueError:
            return "错误: 无效的十六进制数据"

    # ---------- 设置波特率 ----------
    if subcmd == "set_baud":
        if len(parts) < 4:
            return "错误: 缺少波特率"
        try:
            baud = int(parts[3])
        except ValueError:
            return "错误: 波特率必须是整数"
        # 修改硬件
        if obj.set_baudrate(baud):
            # 更新配置
            cfg = get_ir_device(dev_name)
            if cfg:
                cfg['baudrate'] = baud
                # 保存配置（需要加载全部并保存，简单起见用 save_ir_config 全量写回）
                all_cfg = load_ir_config()
                all_cfg[dev_name]['baudrate'] = baud
                save_ir_config(all_cfg)
            return f"波特率已设为 {baud}（已生效，下次上电仍保持）"
        else:
            return "修改波特率失败"

    # ---------- 设置超时 ----------
    if subcmd == "set_timeout":
        if len(parts) < 4:
            return "错误: 缺少超时时间（毫秒）"
        try:
            timeout_ms = int(parts[3])
            if timeout_ms < 100:
                return "错误: 超时至少为 100ms"
        except ValueError:
            return "错误: 超时必须是整数"
        obj.set_timeout(timeout_ms)
        # 更新配置
        cfg = get_ir_device(dev_name)
        if cfg:
            cfg['timeout'] = timeout_ms
            all_cfg = load_ir_config()
            all_cfg[dev_name]['timeout'] = timeout_ms
            save_ir_config(all_cfg)
        return f"超时已设为 {timeout_ms}ms"

    # ---------- 设置帧头 ----------
    if subcmd == "set_header":
        if len(parts) < 4:
            return "错误: 缺少帧头字节（十六进制）"
        try:
            header = int(parts[3], 16)
        except ValueError:
            return "错误: 帧头必须是十六进制数"
        if obj.set_frame_header(header):
            return f"帧头已设为 0x{header:02X}"
        else:
            return "设置帧头失败"

    # ---------- 未知子命令 ----------
    return f"未知 IR05T 子命令: {subcmd}"