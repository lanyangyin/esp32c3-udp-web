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

def dict_keys_diff(a, b):
    """
    返回 a 的键集合中，不在 b 的键集合中的键列表。
    参数 a 和 b 可以是字典或任何可迭代对象（如列表、集合）。
    若为字典，则取其 .keys()。
    返回 list。
    """
    keys_a = set(a.keys()) if hasattr(a, 'keys') else set(a)
    keys_b = set(b.keys()) if hasattr(b, 'keys') else set(b)
    return list(keys_a - keys_b)


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

# =============================================================================
# 网络
# =============================================================================

def _ip_to_int(ip_str):
    """将点分十进制IP字符串转为整数"""
    parts = ip_str.split('.')
    if len(parts) != 4:
        return 0
    return (int(parts[0]) << 24) | (int(parts[1]) << 16) | (int(parts[2]) << 8) | int(parts[3])

def _int_to_ip(ip_int):
    """将整数转为点分十进制IP字符串"""
    return f"{(ip_int >> 24) & 0xFF}.{(ip_int >> 16) & 0xFF}.{(ip_int >> 8) & 0xFF}.{ip_int & 0xFF}"

def _get_interface_info():
    """获取AP和STA的IP、子网掩码，返回两个字典或None"""
    ap_if = network.WLAN(network.AP_IF)
    sta_if = network.WLAN(network.STA_IF)
    info = {"AP": None, "STA": None}
    if ap_if.active():
        ip, mask, _, _ = ap_if.ifconfig()
        if ip and ip != '0.0.0.0':
            info["AP"] = {"ip": ip, "mask": mask, "ip_int": _ip_to_int(ip), "mask_int": _ip_to_int(mask)}
    if sta_if.active() and sta_if.isconnected():
        ip, mask, _, _ = sta_if.ifconfig()
        if ip and ip != '0.0.0.0':
            info["STA"] = {"ip": ip, "mask": mask, "ip_int": _ip_to_int(ip), "mask_int": _ip_to_int(mask)}
    return info

def _ip_belongs_to(ip_str, if_info):
    """判断ip_str是否属于该接口子网"""
    if not if_info:
        return False
    ip_int = _ip_to_int(ip_str)
    net_addr = if_info["ip_int"] & if_info["mask_int"]
    return (ip_int & if_info["mask_int"]) == net_addr

def get_interface_broadcast(ip_str):
    """
    根据输入的IP地址，判断它属于AP还是STA接口，并返回该接口的广播地址。
    如果IP不属于任何接口，则返回None。
    """
    info = _get_interface_info()
    for iface, data in info.items():
        if data and _ip_belongs_to(ip_str, data):
            # 计算广播地址：网络地址 | (~子网掩码)
            net_addr = data["ip_int"] & data["mask_int"]
            broadcast_int = net_addr | (~data["mask_int"] & 0xFFFFFFFF)
            return _int_to_ip(broadcast_int)
    return None

def get_other_interface_broadcast(ip_str):
    """
    根据输入的IP地址，判断它属于AP还是STA接口，然后返回另一个接口的广播地址。
    如果IP不属于任何接口，或另一个接口未激活/无IP，则返回None。
    """
    info = _get_interface_info()
    # 确定当前接口类型
    current_iface = None
    for iface, data in info.items():
        if data and _ip_belongs_to(ip_str, data):
            current_iface = iface
            break
    if not current_iface:
        return None
    # 获取另一个接口
    other_iface = "STA" if current_iface == "AP" else "AP"
    other_data = info.get(other_iface)
    if not other_data:
        return None
    # 计算另一个接口的广播地址
    net_addr = other_data["ip_int"] & other_data["mask_int"]
    broadcast_int = net_addr | (~other_data["mask_int"] & 0xFFFFFFFF)
    return _int_to_ip(broadcast_int)