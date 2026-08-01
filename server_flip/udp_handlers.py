# udp_handlers.py - UDP 命令处理函数（业务逻辑层）

import machine
import time
from udp_sender import send_response


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
    else:
        print(f"[UDP] 未识别的消息: {payload[:50]}")