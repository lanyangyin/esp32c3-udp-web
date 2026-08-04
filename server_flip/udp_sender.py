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
# =============================================================================
# 导入所需模块
# =============================================================================
import gc
import socket
import time
import fragment_protocol
import config          # 导入全局配置变量
from util import get_self_mac, get_interface_broadcast, get_other_interface_broadcast
import wifi
import route
import neighbor
from constants import (
    BROADCAST_MAC,
    NULL_MAC,
    UDP_RESPONSE_MAX_PACKET,
    UDP_RESPONSE_SLEEP,
    DEFAULT_ROUTE_TTL,
    BROADCAST_TTL, DEBUG_FRAGMENT
)

# =============================================================================
# 高级发送函数（统一使用分片格式）
# =============================================================================

def send_udp_fragmented_simple(target_ip, dst_mac, content, tag):
    """简化的分片发送：自动获取本机 MAC，使用默认端口"""
    src_mac = get_self_mac()
    route_table = route.load_route_table()
    if dst_mac in route_table:
        ttl = route_table[dst_mac]["step"]
    else:
        ttl = DEFAULT_ROUTE_TTL
    return fragment_protocol.send_udp_fragmented(
        target_ip=target_ip,
        port=config.g_udp_broadcast_port,
        src_mac=src_mac,
        dst_mac=dst_mac,
        content=content,
        tag=tag,
        ttl=ttl
    )


def send_interface_broadcast_fragmented(tag, ip = None, content=None):
    """同ip端广播分片消息（dst_mac = FF:FF:FF:FF:FF:FF）"""
    target_ip = get_interface_broadcast(ip)
    if not target_ip:
        return False
    return fragment_protocol.send_udp_fragmented(
        target_ip=target_ip,
        port=config.g_udp_broadcast_port,
        src_mac=get_self_mac(),
        dst_mac=BROADCAST_MAC,
        content=content,
        tag=tag,
        ttl=BROADCAST_TTL
    )


def send_other_interface_broadcast_fragmented(tag, ip = None, content=None, src_mac=get_self_mac()):
    """向另一个ip端广播分片消息（dst_mac = FF:FF:FF:FF:FF:FF）"""
    target_ip = get_other_interface_broadcast(ip)
    if not target_ip:
        return False
    return fragment_protocol.send_udp_fragmented(
        target_ip=target_ip,
        port=config.g_udp_broadcast_port,
        src_mac=src_mac,
        dst_mac=BROADCAST_MAC,
        content=content,
        tag=tag,
        ttl=BROADCAST_TTL
    )


def send_udp_broadcast_fragmented(tag, interface_mode = "STA", src_mac=get_self_mac(), content=None):
    """广播分片消息（dst_mac = FF:FF:FF:FF:FF:FF）"""
    if interface_mode == "AP":
        target_ip = config.g_ap_broadcast_addr
    else:
        prefix = wifi.get_sta_prefix()
        if prefix:
            target_ip = f"{prefix}.255"
        else:
            print("[UDP] STA 未连接")  # 新增
            return False
    return fragment_protocol.send_udp_fragmented(
        target_ip=target_ip,
        port=config.g_udp_broadcast_port,
        src_mac=src_mac,
        dst_mac=BROADCAST_MAC,
        content=content,
        tag=tag,
        ttl=BROADCAST_TTL
    )


# =============================================================================
# 单播发送
# =============================================================================

# IP 发送，（AP/STA 网段）IP 尾号发送，昵称发送
def udp_send_to_ip(target_ip, content):
    """
    向指定 IP 发送 UDP 分片消息（自动查找 MAC）。
    如果找不到 MAC，则使用（00:00:00:00:00:00）并打印警告。
    """
    dst_mac = neighbor.get_mac_by_ip(target_ip)
    if not dst_mac:
        dst_mac = NULL_MAC
        print(f"[UDP] 警告: 未找到目标 {target_ip} 的MAC，使用空MAC")
    return send_udp_fragmented_simple(target_ip, dst_mac, content, tag="GENERAL")


# =============================================================================
# 路由单播发送
# =============================================================================


def send_route_message(dst_mac, cmd_msg):
    """发送路由消息到目标 MAC（单播）"""
    next_hop_ip = None
    neighbors = neighbor.load_neighbors()
    if dst_mac in neighbors:
        next_hop_ip = neighbors[dst_mac].get("ip")
    else:
        # 清理并查路由表
        route_table = route.load_route_table()
        if dst_mac in route_table:
            next_hop_ip = route_table[dst_mac]["ip"]
    if next_hop_ip:
        return send_udp_fragmented_simple(
            target_ip=next_hop_ip,
            dst_mac=dst_mac,
            content=cmd_msg,
            tag="GENERAL"
        )
    print(f"[ROUTE_MSG] 发送失败，目标 {dst_mac} 不可达")
    return False


# =============================================================================
# 单次广播发送（同步，不创建线程）
# =============================================================================

def send_broadcast_once(content):
    """发送一次 AP 广播（同步，不创建线程）"""
    return send_udp_broadcast_fragmented(content=content, interface_mode="AP", tag="GENERAL")


def send_sta_broadcast_once(content):
    """发送一次 STA 广播（同步，不创建线程）"""
    return send_udp_broadcast_fragmented(content=content, interface_mode="STA", tag="GENERAL")


def send_both_broadcast_once(content):
    """发送一次 AP+STA 双网段广播（同步，不创建线程）"""
    ap_ok = send_udp_broadcast_fragmented(content=content, interface_mode="AP", tag="GENERAL")
    sta_ok = send_udp_broadcast_fragmented(content=content, interface_mode="STA", tag="GENERAL")
    return ap_ok and sta_ok


# =============================================================================
# UDP 回复发送（简单文本）
# =============================================================================
def send_response(text, target_ip, dst_mac:str, direct_transmission:bool=True):
    """发送 UDP 回复，自动分段（纯文本）"""
    gc.collect()  # 发送前尝试回收内存

    if direct_transmission:
        MAX_PACKET_SIZE = UDP_RESPONSE_MAX_PACKET
        lines = text.split('\n')
        if len(text.encode('utf-8')) <= MAX_PACKET_SIZE:
            data = text.encode('utf-8')
            sock = None
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(0.5)
                sock.sendto(data, (target_ip, config.g_udp_broadcast_port))
            except Exception as e:
                print(f"[UDP] 回复发送失败: {e}")
            finally:
                if sock:
                    sock.close()
            return

        # 分段发送
        parts = []
        current_lines = []
        current_len = 0
        prefix_overhead = len("[part 999/999]\n".encode('utf-8'))
        for line in lines:
            line_len = len(line.encode('utf-8')) + 1
            if current_lines and (current_len + line_len + prefix_overhead > MAX_PACKET_SIZE):
                parts.append("\n".join(current_lines))
                current_lines = [line]
                current_len = line_len
            else:
                current_lines.append(line)
                current_len += line_len
        if current_lines:
            parts.append("\n".join(current_lines))

        num_parts = len(parts)
        for i, part_text in enumerate(parts):
            if num_parts > 1:
                packet_text = f"[part {i+1}/{num_parts}]\n" + part_text
            else:
                packet_text = part_text
            data = packet_text.encode('utf-8')
            sock = None
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(0.5)
                sock.sendto(data, (target_ip, config.g_udp_broadcast_port))
                print(f"[UDP] 已发送分段 {i + 1}/{num_parts} 到 {target_ip}:{config.g_udp_broadcast_port}, 大小 {len(data)} 字节")
                time.sleep(UDP_RESPONSE_SLEEP)
            except Exception as e:
                print(f"[UDP] 发送段 {i+1} 失败: {e}")
            finally:
                if sock:
                    sock.close()
    else:
        # 分片协议发送，内部已有打印（在 fragment_protocol 中）
        send_route_message(dst_mac, text)



# =============================================================================
# 死亡宣告
# =============================================================================
def death_broadcast(mac_list:str, src_mac=get_self_mac()):
    """发送某一个设备的死亡宣告, mac_list中的mac用逗号隔开"""
    print(f"[死亡宣告] {src_mac} —> 丢失设备:\n\t{mac_list.replace(',', '\t\n')}")
    ap_ok = send_udp_broadcast_fragmented(content=mac_list, interface_mode="AP", src_mac=src_mac, tag="死亡触发更新")
    sta_ok = send_udp_broadcast_fragmented(content=mac_list, interface_mode="STA", src_mac=src_mac, tag="死亡触发更新")
    return ap_ok and sta_ok


# =============================================================================
# 邻居表
# =============================================================================

# def send_neighbor_register_request(interface_mode="AP"):
#     """发送邻居注册请求（分片格式）[广播]"""
#     send_udp_broadcast_fragmented(tag="邻居注册请求", interface_mode=interface_mode)
#
#
# def send_neighbor_update_request(interface_mode = "AP"):
#     """邻居更新请求（分片格式）[广播]"""
#     send_udp_broadcast_fragmented(tag="邻居更新请求", interface_mode=interface_mode)
#
#
# def send_register_reply(target_ip, dst_mac):
#     """回复邻居注册请求（分片格式）[UDP]，携带本机昵称"""
#     return send_udp_fragmented_simple(
#         target_ip=target_ip,
#         dst_mac=dst_mac,
#         tag="邻居请求回复",
#         content=config.g_device_nickname   # 改为发送昵称
#     )


def send_neighbor_advertise(interface_mode="AP"):
    """向指定网段广播邻居请求回复（携带本机昵称）"""
    if DEBUG_FRAGMENT:
        print(f"[邻居请求回复{interface_mode}]")
    content = config.g_device_nickname  # 发送昵称
    return send_udp_broadcast_fragmented(
        tag="邻居请求回复",
        interface_mode=interface_mode,
        content=content
    )

def send_neighbor_advertise_both():
    """向 AP 和 STA 双网段广播邻居请求回复"""
    ap_ok = send_neighbor_advertise("AP")
    sta_ok = send_neighbor_advertise("STA")
    return ap_ok and sta_ok


# =============================================================================
# 路由表
# =============================================================================
#
#
# def send_route_register_request():
#     """发送路由注册请求（在 AP 网段）[广播]"""
#     send_udp_broadcast_fragmented(
#         tag="路由注册请求",
#         interface_mode="AP",
#         content=1
#     )
#
#
# def send_route_register_reply(target_ip, dst_mac):
#     """发送路由注册请求的回复，向来源方向"""
#     send_udp_fragmented_simple(
#         target_ip=target_ip,
#         dst_mac=dst_mac,
#         tag="路由请求回复",
#         content=None
#     )
#
#
# def send_route_update_request():
#     """发送路由更新请求（在 STA 网段）[广播]"""
#     send_udp_broadcast_fragmented(
#         tag="路由更新请求",
#         interface_mode="STA"
#     )
#
#
# def send_route_learn_request():
#     """发送路由学习请求[广播]"""
#     send_udp_broadcast_fragmented(
#         tag="路由学习请求",
#         interface_mode="STA"
#     )


def send_route_advertise():
    """
    发送路由通告（在 STA 网段）[广播]即使没有路由表也要发出去
    我能到达谁——我距离它多远——他的昵称是什么——我从谁那里知道的
    """
    mac_step_list = []
    self_mac = get_self_mac()
    self_info = f"{self_mac}_0_{config.g_device_nickname}_{self_mac}"
    """我能到达谁——我距离它多远——他的昵称是什么——我从谁那里知道的"""
    route_table = route.load_route_table()
    nickname_table = config.load_nicknames()
    if route_table:
        mac_step_list = [f"{mac}_{route_table[mac]['step']}_{nickname_table.get(mac,None)}_{route_table[mac].get('source',None)}" for mac in list(route_table.keys())]
    mac_step_list.append(self_info)
    content = ",".join(mac_step_list)
    if DEBUG_FRAGMENT:
        print(f"[路由通告STA] \n\t{content.replace(',', '\n\t')}")
    prefix = wifi.get_sta_prefix()
    if not prefix:
        print("[UDP] STA 未连接")
        return False
    target_ip = f"{prefix}.255"
    return fragment_protocol.send_udp_fragmented(
        target_ip=target_ip,
        port=config.g_udp_broadcast_port,
        src_mac=self_mac,
        dst_mac=BROADCAST_MAC,
        content=content,
        punctuation=',',
        tag="路由通告",
        ttl=2
    )


def send_route_advertise_ap():
    """
    发送路由通告（在 AP 网段）[广播]即使没有路由表也要发出去
    我能到达谁——我距离它多远——他的昵称是什么——我从谁那里知道的
    """
    mac_step_list = []
    self_mac = get_self_mac()
    self_info = f"{self_mac}_0_{config.g_device_nickname}_{self_mac}"
    """我能到达谁——我距离它多远——他的昵称是什么——我从谁那里知道的"""
    route_table = route.load_route_table()
    nickname_table = config.load_nicknames()
    if route_table:
        mac_step_list = [f"{mac}_{route_table[mac]['step']}_{nickname_table.get(mac,None)}_{route_table[mac].get('source',None)}" for mac in list(route_table.keys())]
    mac_step_list.append(self_info)
    content = ",".join(mac_step_list)
    if DEBUG_FRAGMENT:
        print(f"[路由通告AP] \n\t{content.replace(',', '\n\t')}")
    target_ip = config.g_ap_broadcast_addr   # ✅ 提前赋值，确保定义
    return fragment_protocol.send_udp_fragmented(
        target_ip=target_ip,
        port=config.g_udp_broadcast_port,
        src_mac=self_mac,
        dst_mac=BROADCAST_MAC,      # 确保 BROADCAST_MAC 已定义
        content=content,
        punctuation=',',
        tag="路由通告",
        ttl=2
    )


def send_route_advertise_both():
    """向 AP 和 STA 双网段广播路由通告"""
    ap_ok = send_route_advertise_ap()
    sta_ok = send_route_advertise()   # 原有的 STA 广播
    return ap_ok and sta_ok