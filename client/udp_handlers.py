# udp_handlers.py - UDP 命令处理函数（业务逻辑层）

import machine
import time
from udp_sender import send_response


from info_commands import get_help_info, get_status_info, get_memory_info
from config_commands import handle_config_command
from ap_commands import handle_ap_command
from sta_commands import handle_sta_command
from servo_commands import handle_servo_command
from ir_commands import handle_ir05t_command
from route_commands import handle_route_command
from neighbor_commands import handle_neighbor_command
from nickname_commands import handle_nickname_command

# =============================================================================
# UDP 命令分发器（处理收到的消息）
# =============================================================================

def custom_udp_processing(payload, sender_ip, dst_mac="00:00:00:00:00:00", direct_transmission=True):
    lower = payload.lower().strip()
    # 无参命令直接回复
    if lower == "hello":
        send_response(f"Hi {dst_mac}", sender_ip, dst_mac, direct_transmission)
    elif lower == "hi":
        send_response(f"Hello {dst_mac}", sender_ip, dst_mac, direct_transmission)
    elif lower == "help":
        send_response(get_help_info(include_config=True), sender_ip, dst_mac, direct_transmission)
    elif lower.startswith("ap"):
        parts = payload.split(',')
        response = handle_ap_command(parts)
        send_response(response, sender_ip, dst_mac, direct_transmission)
    elif lower.startswith("sta"):
        parts = payload.split(',')
        response = handle_sta_command(parts)
        send_response(response, sender_ip, dst_mac, direct_transmission)
    elif lower == "servo,help":
        send_response(get_help_info("servo"), sender_ip, dst_mac, direct_transmission)
    elif lower == "ir05t,help":
        send_response(get_help_info("ir05t"), sender_ip, dst_mac, direct_transmission)
    elif lower == "status":
        send_response(get_status_info(), sender_ip, dst_mac, direct_transmission)
    elif lower == "memory":
        send_response(get_memory_info(), sender_ip, dst_mac, direct_transmission)
    # 带参数命令交给模块处理
    elif lower.startswith("nickname"):
        parts = payload.split(',')
        response = handle_nickname_command(parts)
        send_response(response, sender_ip, dst_mac, direct_transmission)
    elif lower.startswith("route"):
        parts = payload.split(',')
        response = handle_route_command(parts)
        send_response(response, sender_ip, dst_mac, direct_transmission)
    elif lower.startswith("neighbor"):
        parts = payload.split(',')
        response = handle_neighbor_command(parts)
        send_response(response, sender_ip, dst_mac, direct_transmission)
    elif lower.startswith("servo"):
        parts = payload.split(',')
        response = handle_servo_command(parts)
        send_response(response, sender_ip, dst_mac, direct_transmission)
    elif lower.startswith("ir05t"):
        parts = payload.split(',')
        response = handle_ir05t_command(parts)
        send_response(response, sender_ip, dst_mac, direct_transmission)
    elif lower.startswith("config"):
        parts = payload.split(',')
        response = handle_config_command(parts)
        send_response(response, sender_ip, dst_mac, direct_transmission)
        if len(parts) >= 2 and parts[1].strip().lower() in ("save", "reset"):
            time.sleep(0.5)
            print("[UDP] 执行重启...")
            machine.reset()
    else:
        print(f"[UDP] 未识别的消息: {payload[:50]}")