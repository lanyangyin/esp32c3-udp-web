# util.py - 通用工具

import gc
import os, json
import socket
import network
import _thread

# =============================================================================
# 全局状态变量
# =============================================================================
DEBUG_GC = True   # 设为 False 关闭打印
_file_locks = {}


# =============================================================================
# 工具函数
# =============================================================================
def get_self_mac():
    """获取本机 MAC 地址（统一使用 AP 接口）"""
    sta_if = network.WLAN(network.STA_IF)
    return mac_to_str(sta_if.config('mac'))

def get_mac_short():
    mac = get_self_mac()
    return mac[-5:].replace(':', '')

def send_broadcast(target_ip, port, message):
    """向指定 IP 和端口发送 UDP 广播消息"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(0.5)  # 防止阻塞
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(message.encode(), (target_ip, port))
        sock.close()
        print(f"[UDP] 已发送广播到 {target_ip}:{port}: {message}")
        return True
    except Exception as e:
        print(f"[UDP] 广播发送失败: {e}")
        return False

def gc_wrapper(func):
    def wrapper(*args, **kwargs):
        if DEBUG_GC:
            before_alloc = gc.mem_alloc()
            gc.collect()
            after_alloc = gc.mem_alloc()
            freed = before_alloc - after_alloc
            if freed > 0:
                print(f"[GC] {func.__name__} 释放 {freed} 字节")
        else:
            gc.collect()
        return func(*args, **kwargs)
    return wrapper

def mac_to_str(mac):
    """将 MAC 地址转换为标准 XX:XX:XX:XX:XX:XX 格式的字符串"""
    if isinstance(mac, tuple) and len(mac) > 0:
        mac = mac[0]
    if isinstance(mac, bytes):
        hex_str = mac.hex().upper()
        return ':'.join(hex_str[i:i+2] for i in range(0, 12, 2))
    elif isinstance(mac, str):
        clean = mac.replace(':', '').replace('-', '').replace(' ', '').upper()
        if len(clean) == 12:
            return ':'.join(clean[i:i+2] for i in range(0, 12, 2))
        else:
            return clean
    else:
        return str(mac).upper()

def get_default_nickname():
    """返回默认设备昵称：MAC地址去掉冒号，转为小写"""
    mac = get_self_mac()
    return mac.replace(':', '').lower()

def is_british_safe_name(name):
    """检查名称是否只包含字母、数字、下划线"""
    for c in name:
        if not ((c >= 'a' and c <= 'z') or (c >= 'A' and c <= 'Z') or (c >= '0' and c <= '9') or c == '_'):
            return False
    return True

def is_safe_name(name):
    """
    检查名称是否安全：
    - 允许 字母、中文、数字、下划线
    - 排除逗号、引号、换行符、管道符等命令/JSON 敏感字符
    """
    forbidden = {',', '"', "'", '\n', '\r', '|', ';'}
    for ch in name:
        if ch in forbidden:
            return False
    return True

def get_file_lock(filepath):
    if filepath not in _file_locks:
        _file_locks[filepath] = _thread.allocate_lock()
    return _file_locks[filepath]

def atomic_write(filepath, data):
    """将 data（dict/list）原子写入 JSON 文件"""
    tmp = filepath + ".tmp"
    try:
        with open(tmp, "w") as f:
            json.dump(data, f)
        os.rename(tmp, filepath)   # rename 在大多数文件系统中是原子的
    except Exception:
        # 清理临时文件
        try:
            os.remove(tmp)
        except:
            pass
        raise
# =============================================================================
# 引脚占用管理
# =============================================================================
_used_pins = {}  # pin → owner (描述字符串)

_pin_lock = _thread.allocate_lock()

def pin_claim(pin, owner):
    """
    申请占用一个 GPIO 引脚。
    返回 (success, message)，success 为 True 表示成功，False 表示已被占用。
    """
    with _pin_lock:
        if pin in _used_pins:
            return False, f"GPIO{pin} 已被 {_used_pins[pin]} 占用"
        _used_pins[pin] = owner
        return True, f"GPIO{pin} 分配给 {owner}"

def pin_release(pin):
    """释放引脚占用，若未被占用则忽略"""
    with _pin_lock:
        if pin in _used_pins:
            del _used_pins[pin]

def get_used_pins():
    """返回当前所有已占用引脚的字典副本"""
    with _pin_lock:
        return dict(_used_pins)