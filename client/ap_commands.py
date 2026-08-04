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
# ap_commands.py - AP 配置 UDP 命令处理
import config


def handle_ap_command(parts):
    """
    处理 ap 相关命令
    格式: ap,set_ssid,<新SSID>
          ap,set_password,<新密码>
          ap,set_ip,<IP>
          ap,set_netmask,<掩码>
          ap,set_gateway,<网关>
    """
    if len(parts) < 2:
        return "错误: 缺少子命令，可用: set_ssid, set_password, set_ip, set_netmask, set_gateway"

    subcmd = parts[1].strip().lower()

    if subcmd == "set_ssid":
        if len(parts) < 3:
            return "错误: 缺少 SSID"
        new_ssid = parts[2].strip()
        if not new_ssid:
            return "错误: SSID 不能为空"
        config.update_ap_ssid(new_ssid)
        return f"AP SSID 已更新为 '{new_ssid}'，需重启生效"

    elif subcmd == "set_password":
        if len(parts) < 3:
            return "错误: 缺少密码"
        new_password = parts[2].strip()
        config.update_ap_password(new_password)
        return f"AP 密码已更新（长度为 {len(new_password)}），需重启生效"

    elif subcmd == "set_ip":
        if len(parts) < 3:
            return "错误: 缺少 IP 地址"
        ip = parts[2].strip()
        # 简单验证
        parts_ip = ip.split('.')
        if len(parts_ip) != 4 or not all(p.isdigit() and 0 <= int(p) <= 255 for p in parts_ip):
            return "错误: 无效 IP 地址格式"
        config.update_ap_ip(ip)
        return f"AP IP 已设置为 {ip}，需重启生效"

    elif subcmd == "set_netmask":
        if len(parts) < 3:
            return "错误: 缺少子网掩码"
        mask = parts[2].strip()
        parts_mask = mask.split('.')
        if len(parts_mask) != 4 or not all(p.isdigit() and 0 <= int(p) <= 255 for p in parts_mask):
            return "错误: 无效子网掩码格式"
        config.update_ap_netmask(mask)
        return f"AP 子网掩码已设置为 {mask}，需重启生效"

    elif subcmd == "set_gateway":
        if len(parts) < 3:
            return "错误: 缺少网关地址"
        gw = parts[2].strip()
        parts_gw = gw.split('.')
        if len(parts_gw) != 4 or not all(p.isdigit() and 0 <= int(p) <= 255 for p in parts_gw):
            return "错误: 无效网关地址格式"
        config.update_ap_gateway(gw)
        return f"AP 网关已设置为 {gw}，需重启生效"

    elif subcmd == "help":
        return "AP 配置命令:\n  ap,set_ssid,<新SSID>\n  ap,set_password,<新密码>\n  ap,set_ip,<IP>\n  ap,set_netmask,<掩码>\n  ap,set_gateway,<网关>"

    else:
        return f"未知 ap 子命令: {subcmd}，可用: set_ssid, set_password, set_ip, set_netmask, set_gateway"