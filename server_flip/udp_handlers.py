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
# udp_handlers.py - UDP 命令处理函数（业务逻辑层）
import gc

import machine
import time
import config
from udp_sender import send_response


# =============================================================================
# UDP 命令分发器（处理收到的消息）
# =============================================================================

def custom_udp_processing(payload, sender_ip, dst_mac="00:00:00:00:00:00", direct_transmission=True):
    """
    UDP 命令分发器，将命令路由到对应的模块处理函数。

    参数：
        payload: 收到的消息内容
        sender_ip: 发送方 IP
        dst_mac: 目标 MAC
        direct_transmission: 是否直接回复（True=纯UDP回复，False=通过路由转发）
    """
    lower = payload.lower().strip()

    # ---------- 精确匹配的无参命令 ----------
    if lower == "hello":
        send_response(f"Hi {dst_mac}. I am {config.g_device_nickname}", sender_ip, dst_mac, direct_transmission)
        return
    elif lower == "hi":
        send_response(f"Hello {dst_mac}. I am {config.g_device_nickname}", sender_ip, dst_mac, direct_transmission)
        return
    gc.collect()

    # ---------- 解析带模块前缀的命令（格式: 模块,子命令,参数...） ----------
    parts = [p.strip() for p in payload.split(',')]
    if len(parts) < 1:
        return

    module = parts[0].strip().lower()