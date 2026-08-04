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
# reset_commands.py - 重置引脚配置 UDP 命令处理
import config
from machine import Pin

def handle_reset_command(parts):
    """
    处理 reset 相关命令
    格式: reset,set_pin,<引脚>
          reset,set_time,<秒数>
          reset,status
    """
    if len(parts) < 2:
        return "错误: 缺少子命令，可用: set_pin, set_time, status"

    subcmd = parts[1].strip().lower()

    if subcmd == "set_pin":
        if len(parts) < 3:
            return "错误: 缺少引脚号"
        try:
            pin = int(parts[2])
            if pin < 0 or pin > 21 or pin in range(12, 18):
                return "错误: 引脚无效或为 Flash 专用引脚"
            config.update_reset_pin(pin)
            return f"重置引脚已设为 GPIO{pin}，需重启生效"
        except ValueError:
            return "错误: 引脚必须是整数"

    elif subcmd == "set_time":
        if len(parts) < 3:
            return "错误: 缺少秒数"
        try:
            seconds = int(parts[2])
            if seconds < 1:
                return "错误: 秒数至少为1秒"
            config.update_reset_hold_time(seconds)
            return f"重置短接时间已设为 {seconds} 秒，需重启生效"
        except ValueError:
            return "错误: 秒数必须是整数"

    elif subcmd == "status":
        reset_pin_obj = config.g_reset_pin_obj
        if reset_pin_obj is None:
            return "重置引脚未初始化"
        level = reset_pin_obj.value()
        status = "低电平 (短接)" if level == 0 else "高电平 (未短接)"
        return f"重置引脚: GPIO{config.g_reset_pin}\n短接时间: {config.g_reset_hold_time} 秒\n当前状态: {status}"

    else:
        return f"未知 reset 子命令: {subcmd}，可用: set_pin, set_time, status"