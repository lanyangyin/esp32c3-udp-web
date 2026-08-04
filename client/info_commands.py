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
# info_commands.py
import gc
import config
from loader import load_commands

def get_help_info(module=None, include_config=False):
    config_info = ""
    if include_config:
        config_info = f"--- 当前配置 ---\n"
        config_info += f"STA目标AP: {config.g_sta_ssid}\n"
        config_info += f"自身AP SSID: {config.g_ap_ssid}\n"
        config_info += f"UDP监听端口: {config.g_udp_recv_port}\n"
        config_info += f"UDP广播端口: {config.g_udp_broadcast_port}\n"

    cmd_lines = []
    if module is None:
        cmd_lines.append("--- 系统命令 ---")
        cmds = load_commands("system")
        for item in cmds:
            cmd_lines.append(f"  {item['cmd']}  - {item['desc']}")
    else:
        cmds = load_commands(module)
        if not cmds:
            return f"错误: 未知模块 '{module}'"
        cmd_lines.append(f"\n--- {module.upper()} 模块命令 ---")
        for item in cmds:
            cmd_lines.append(f"  {item['cmd']}  - {item['desc']}")

    return config_info + "\n".join(cmd_lines)

def get_status_info():
    try:
        import network
        sta = network.WLAN(network.STA_IF)
        sta_ip = sta.ifconfig()[0] if sta.isconnected() else "未连接"
    except:
        sta_ip = "N/A"

    config_info = f"AP SSID: {config.g_ap_ssid}\n"
    config_info += f"AP IP: {config.g_ap_ip}\n"
    config_info += f"STA SSID: {config.g_sta_ssid}\n"
    config_info += f"STA IP: {sta_ip}\n"
    config_info += f"UDP 监听端口: {config.g_udp_recv_port}\n"
    config_info += f"UDP 广播端口: {config.g_udp_broadcast_port}\n"
    config_info += f"设备昵称: {config.g_device_nickname}\n"
    config_info += f"邻居广播间隔: {config.g_neighbor_advertise_interval} 秒\n"
    config_info += f"路由通告间隔: {config.g_route_advertise_interval} 秒"
    return config_info

def get_memory_info():
    free = gc.mem_free()
    alloc = gc.mem_alloc()
    total = free + alloc
    return f"总内存: {total} 字节\n已用: {alloc} 字节 ({alloc/total*100:.1f}%)\n空闲: {free} 字节"