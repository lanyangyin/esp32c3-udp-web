# udp.py - UDP 通信、广播线程、消息接收与处理模块
"""
统一使用分片格式发送所有 UDP 消息。
广播消息的 dst_mac 固定为 FF:FF:FF:FF:FF:FF。
接收端仅解析分片格式，不再支持旧格式。
"""
# =============================================================================
# 导入所需模块
# =============================================================================
import gc
import socket
import random
import sys

import select
import _thread
import time
import network
import fragment_protocol
import config          # 导入全局配置变量
import udp_handlers
from udp_sender import (
    send_broadcast_once, send_sta_broadcast_once, send_both_broadcast_once,
    udp_send_to_ip, send_route_message,
    send_neighbor_register_request, send_neighbor_update_request,
    send_route_register_request, send_route_update_request,
    send_route_learn_request, send_route_advertise, send_register_reply, send_route_advertise_ap,
    send_neighbor_advertise_both, send_route_advertise_both
)
from constants import (
    CACHE_CLEAN_INTERVAL,
    BROADCAST_MAC,
    NULL_MAC,
    NEIGHBOR_TTL_MAX,
    ROUTE_TTL_MAX,
    BROADCAST_TTL, UDP_RECV_BUFFER, DEBUG_FRAGMENT
)
import util
import wifi
import route
import neighbor
from util import get_self_mac

# =============================================================================
# 全局状态变量
# =============================================================================
udp_messages = None                 # 存储收到的 UDP 消息（用于前端显示）
udp_messages_lock = _thread.allocate_lock()

def add_udp_message(addr, msg):
    global udp_messages
    with udp_messages_lock:
        udp_messages = {
            'time': time.time(),
            'addr': str(addr),
            'msg': msg
        }

def get_udp_messages():
    """返回包含单条消息的列表（兼容旧接口）"""
    with udp_messages_lock:
        return [udp_messages] if udp_messages is not None else []

def clear_udp_messages():
    global udp_messages
    with udp_messages_lock:
        udp_messages = None

# =============================================================================
# 添加独立的邻居表路由表注册申请回复广播线程函数
# =============================================================================
def udp_neighbor_routing_reply():
    last_advertise_time = time.time()
    last_route_advertise_time = time.time()
    gc_counter = time.time()    # 邻居表&路由表扩散内存整理计时
    while True:
        config.update_heartbeat('udp_neighbor')
        try:
            now = time.time()
            # 定期广播邻居请求回复（携带昵称）
            if now - last_advertise_time >= (config.g_neighbor_advertise_interval + random.randint(0, 5)):
                neighbor.ttl_decrement_neighbors()
                send_neighbor_advertise_both()
                last_advertise_time = now
            # 定期广播路由通告
            if now - last_route_advertise_time >= (config.g_route_advertise_interval + random.randint(0, 15)):
                route.route_ttl_decrement()
                send_route_advertise_both()
                last_route_advertise_time = now
            if now - gc_counter >= 9:
                gc.collect()
                gc_counter = now
            time.sleep(3)  # 避免忙等
        except OSError as e:
            if hasattr(e, 'errno') and e.errno in (11, 110, 116):
                continue
            else:
                print(f"[UDP] 其他OS错误: {e}")
                time.sleep(1)
        except Exception as e:
            print(f"[UDP] 接收异常: {repr(e)}")
            sys.print_exception(e)
            time.sleep(1)


# =============================================================================
# UDP 服务器主循环
# =============================================================================
def udp_receiver():
    """
    UDP 接收线程主循环。
    仅解析分片格式消息，重组后根据 TAG 处理业务逻辑。
    """
    global gc_counter
    recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    recv_sock.bind(('0.0.0.0', config.g_udp_recv_port))
    recv_sock.setblocking(False)
    print(f"[UDP] 接收线程启动，监听端口 {config.g_udp_recv_port}")

    # 获取自身 IP 列表（用于过滤自身消息）
    sta = network.WLAN(network.STA_IF)
    sta_ip = sta.ifconfig()[0] if sta.isconnected() else None
    ap = network.WLAN(network.AP_IF)
    ap_ip = ap.ifconfig()[0] if ap.active() else None
    self_ips = [ip for ip in (sta_ip, ap_ip) if ip]
    print(f"[UDP] 自身 IP 列表: {self_ips}")

    # 回复端口（使用广播端口，也可独立配置）
    print(f"[UDP] UDP 回复端口: {config.g_udp_broadcast_port}")

    reset_start_time = None
    last_clean = time.time()
    last_advertise_time = time.time()
    last_route_advertise_time = time.time()
    gc_counter = time.time()

    while True:
        config.update_heartbeat('udp_receiver')
        try:
            # 定期清理超时分片缓存
            now = time.time()
            if now - last_clean > CACHE_CLEAN_INTERVAL:
                fragment_protocol.clean_frag_cache()
                last_clean = now

            # ---------- 重置引脚检测 ----------
            reset_pin_obj = config.g_reset_pin_obj
            if reset_pin_obj is not None:
                if reset_pin_obj.value() == 0:
                    if reset_start_time is None:
                        reset_start_time = time.time()
                        print(f"[RESET] 引脚已短接，保持 {config.g_reset_hold_time} 秒后触发重置")
                    else:
                        elapsed = time.time() - reset_start_time
                        if elapsed >= config.g_reset_hold_time:
                            print("[RESET] 触发恢复出厂设置...")
                            config.reset_to_factory()
                else:
                    if reset_start_time is not None:
                        print("[RESET] 重置引脚已释放，取消计时")
                        reset_start_time = None

            readable, _, _ = select.select([recv_sock], [], [], 1.0)
            if readable:
                data, addr = recv_sock.recvfrom(UDP_RECV_BUFFER)
                sender_ip = addr[0]
                """消息发送方的IP"""
                sender_port = addr[1]

                try:
                    msg = data.decode('utf-8').strip()
                except UnicodeError:
                    continue

                # print(f"[UDP] 收到来自 {addr} 的消息: {msg[:100]}...")

                # ---------- 仅解析分片格式 ----------
                parsed = fragment_protocol.parse_fragmented_msg(msg)

                # 检查是否有效的分片格式
                if 'TAG' not in parsed or 'SRC' not in parsed or 'DST' not in parsed or 'ID' not in parsed:
                    if sender_ip in self_ips:
                        print(f"[UDP] 忽略来自自身的消息")
                        continue
                    if DEBUG_FRAGMENT:
                        print(f"[UDP] 非分片格式消息:{msg[:40]}")
                    if msg:
                        add_udp_message(addr, msg)
                        udp_handlers.custom_udp_processing(msg, sender_ip)
                    continue

                # 尝试重组
                complete, payload, src_mac, dst_mac, tag, ttl = fragment_protocol.reassemble_fragment(parsed, addr)

                if sender_ip in self_ips and src_mac == get_self_mac():
                    print(f"[UDP] 忽略来自自身的消息")
                    continue

                # 存储原始消息到列表（用于前端显示）
                if payload:
                    add_udp_message(addr, payload)

                if not complete:
                    continue  # 等待更多分片

                if DEBUG_FRAGMENT:
                    print(f"[UDP] 重组完成: TAG={tag}, SRC={src_mac}, DST={dst_mac}, TTL={ttl}, MSG={payload[:10]}")


                # ========== 根据 TAG 处理业务逻辑 ==========
                # ---------- 邻居请求回复 ----------
                if tag == "邻居请求回复":
                    print(f"[UDP] 收到邻居请求回复，来自 {src_mac} ({sender_ip})")
                    # 更新邻居表（IP）
                    neighbor.update_mac_from_reply(mac_str=src_mac, ip_str=sender_ip)
                    # 提取昵称（payload）
                    if payload:
                        nickname = payload.strip()
                        # 处理冲突并更新昵称表
                        neighbor.resolve_nickname_conflict_and_update(nickname, src_mac)
                        print(f"[UDP] 邻居昵称更新: {src_mac} -> {nickname}")
                    else:
                        print(f"[UDP] 邻居请求回复中无昵称")
                    gc.collect()
                # ---------- 路由通告 ----------
                elif tag == "路由通告":
                    # 1. 将发送方自身加入路由表，步距=1
                    route.route_set_ttl(src_mac, sender_ip, route.ROUTE_TTL_MAX, 1)
                    rest = payload.strip()
                    if rest:
                        mac_step_list = [m.strip() for m in rest.split(',') if m.strip()]
                        # 一次性读取路由表到内存
                        table = route.load_route_table()
                        added = 0
                        self_mac = util.get_self_mac()
                        for mac_step in mac_step_list:
                            try:
                                mac, step_str = mac_step.split('_')
                                step = int(step_str) + 1
                                mac = util.mac_to_str(mac)
                            except ValueError:
                                print(f"[ROUTE] 解析通告条目失败: {mac_step}")
                                continue
                            # 合法性检查
                            if step < 1 or step > 255:
                                print(f"[ROUTE] 步距无效: {step}")
                                continue
                            # 跳过自身（已经单独添加）
                            if mac == self_mac:
                                continue
                            # 跳过发送方自身（已经单独添加）
                            if mac == src_mac:
                                continue
                            # 如果已存在且步距更小（更优），则忽略
                            if mac in table and step > table[mac].get("step", 0):
                                print(f"[ROUTE] 保留已有更优路径 {mac} step={table[mac]['step']} < {step}")
                                continue
                            # 否则更新（新增或覆盖）
                            table[mac] = {"ip": sender_ip, "ttl": ROUTE_TTL_MAX, "step": step}
                            added += 1
                            print(f"[ROUTE] 添加/更新路由: {mac} -> {sender_ip}, step={step}")
                        # 一次性保存路由表
                        if added > 0:
                            route.save_route_table(table)
                        print(f"[ROUTE] 通告处理完成，添加 {added} 条新路由")
                    gc.collect()
                else:
                    my_mac = util.get_self_mac()
                    if dst_mac == my_mac or dst_mac == NULL_MAC or dst_mac == BROADCAST_MAC:
                        # ---------- 用户广播消息 ----------
                        if tag == "GENERAL":
                            udp_handlers.custom_udp_processing(payload, sender_ip, src_mac, False)

                        # ---------- 其他自定义 TAG ----------
                        else:
                            print(f"[UDP] 未知 TAG={tag}, payload: {payload[:50]}...")
                    else:
                        # 转发前打印
                        print(f"[DEBUG] 转发消息: payload 类型={type(payload)}, 内容={payload[:50] if isinstance(payload, str) else repr(payload)}")
                        # 尝试向邻居转发
                        neighbors = neighbor.load_neighbors()
                        if dst_mac in neighbors:
                            target_ip = neighbors[dst_mac]["ip"]
                            fragment_protocol.send_udp_fragmented(
                                target_ip=target_ip,
                                port=config.g_udp_broadcast_port,
                                src_mac=src_mac,
                                dst_mac=dst_mac,
                                content=payload,
                                tag=tag,
                                ttl=ttl
                            )
                        else:
                            # 尝试向路由转发
                            route_table = route.load_route_table()
                            if dst_mac in route_table:
                                next_hop_ip = route_table[dst_mac]["ip"]
                                fragment_protocol.send_udp_fragmented(
                                    target_ip=next_hop_ip,
                                    port=config.g_udp_broadcast_port,
                                    src_mac=src_mac,
                                    dst_mac=dst_mac,
                                    content=payload,
                                    tag=tag,
                                    ttl=ttl
                                )
                            else:
                                udp_send_to_ip(sender_ip, f"目标 {dst_mac} 不可达")
                                print(f"[ROUTE_MSG] 无法转发，目标 {dst_mac} 不可达")

            # # 定期广播邻居请求回复（携带昵称）
            # if now - last_advertise_time >= (config.g_neighbor_advertise_interval + random.randint(0, 3)):
            #     neighbor.ttl_decrement_neighbors()
            #     send_neighbor_advertise_both()
            #     last_advertise_time = now
            # # 定期广播路由通告
            # if now - last_route_advertise_time >= (config.g_route_advertise_interval + random.randint(0, 5)):
            #     route.route_ttl_decrement()
            #     send_route_advertise_both()
            #     last_route_advertise_time = now
            # if now - gc_counter >= 9:
            #     gc.collect()
            #     gc_counter = now
        except OSError as e:
            if hasattr(e, 'errno') and e.errno in (11, 110, 116):
                continue
            else:
                print(f"[UDP] 其他OS错误: {e}")
                time.sleep(1)
        except Exception as e:
            print(f"[UDP] 接收异常: {repr(e)}")
            sys.print_exception(e)
            time.sleep(1)