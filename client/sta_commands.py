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
# sta_commands.py - STA 配置 UDP 命令处理
import config


def handle_sta_command(parts):
    """
    处理 sta 相关命令
    格式: sta,set_ssid,<SSID>
          sta,set_password,<密码>
          sta,set_timeout,<秒数>
    """
    if len(parts) < 2:
        return "错误: 缺少子命令，可用: set_ssid, set_password, set_timeout"

    subcmd = parts[1].strip().lower()

    if subcmd == "set_ssid":
        if len(parts) < 3:
            return "错误: 缺少 SSID"
        ssid = parts[2].strip()
        config.save_wifi_config(ssid, config.g_sta_password)
        return f"STA SSID 已更新为 '{ssid}'，需重启生效"

    elif subcmd == "set_password":
        if len(parts) < 3:
            return "错误: 缺少密码"
        password = parts[2].strip()
        config.save_wifi_config(config.g_sta_ssid, password)
        return f"STA 密码已更新（长度为 {len(password)}），需重启生效"

    elif subcmd == "set_timeout":
        if len(parts) < 3:
            return "错误: 缺少超时秒数"
        try:
            timeout = int(parts[2])
            if timeout < 5:
                return "错误: 超时至少为5秒"
            config.update_sta_timeout(timeout)
            return f"STA 连接超时已设为 {timeout} 秒，需重启生效"
        except ValueError:
            return "错误: 超时必须是整数"

    elif subcmd == "help":
        return "STA 配置命令:\n  sta,set_ssid,<SSID>\n  sta,set_password,<密码>\n  sta,set_timeout,<秒数>"

    else:
        return f"未知 sta 子命令: {subcmd}，可用: set_ssid, set_password, set_timeout"