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
# nickname_commands.py - 配置和系统 UDP 命令
import config
import machine
import util
from neighbor import update_self_nickname


def handle_nickname_command(parts):
    """
    处理 nickname 命令
    格式: nickname,set,<新昵称>
    """
    if len(parts) < 2:
        return "错误: 缺少子命令，可用: set, help"

    subcmd = parts[1].strip().lower()

    if subcmd == "set":
        new_nick = parts[2].strip()
        if not new_nick:
            return "错误: 昵称不能为空"

        # 更新全局变量
        config.g_device_nickname = new_nick
        # 持久化
        sys_cfg = config.load_system_config()
        sys_cfg["device_nickname"] = new_nick
        if not config.save_system_config(sys_cfg):
            return "保存配置失败"
        # 处理冲突并更新昵称表
        update_self_nickname()
        return f"昵称已更新为 '{new_nick}'"
    elif subcmd == "help":
        return "昵称模块命令:\n  nickname,set,<新昵称> - 修改设备昵称"
    else:
        return f"未知 nickname 子命令: {subcmd}，可用: set, help"
