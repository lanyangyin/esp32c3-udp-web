# neighbor.py - 邻居表和昵称表业务逻辑模块
"""
提供设备发现、认证、昵称管理的高级操作。
底层文件读写由 config 模块统一管理，本模块只负责业务逻辑。
"""

# =============================================================================
# 导入所需模块
# =============================================================================
import random
from config import (
    # 邻居表操作
    load_neighbors, save_neighbors,
    add_or_update_neighbor, delete_neighbor,
    get_neighbor,
    # 昵称表操作
    load_nicknames, save_nicknames, g_device_nickname,
    add_or_update_nickname, delete_nickname,
    ttl_decrement_neighbors,
    NEIGHBOR_TTL_MAX
)
from util import mac_to_str, get_self_mac



# =============================================================================
# 邻居表业务逻辑
# =============================================================================

def update_mac_from_reply(mac_str, ip_str):
    """更新邻居表，设置 TTL=2"""
    mac = mac_to_str(mac_str)
    add_or_update_neighbor(mac, ip_str, ttl=NEIGHBOR_TTL_MAX)
    print(f"[NEIGHBOR] 更新: {mac} -> IP {ip_str}, TTL={NEIGHBOR_TTL_MAX}")

def get_auth_devices():
    """
    获取所有已认证设备（邻居表中 IP 不为空的条目），
    并附带其昵称（若有）。
    返回列表：[{'mac': '...', 'ip': '...', 'nickname': '...'}, ...]
    """
    neighbors = load_neighbors()
    nicknames = load_nicknames()
    result = []
    for mac, entry in neighbors.items():
        ip = entry.get("ip")
        if ip:
            result.append({
                'mac': mac,
                'ip': ip,
                'nickname': nicknames.get(mac, '')
            })
    return result


def clear_unauth():
    """
    清除邻居表中所有 IP 为空的无效条目，同时移除对应的昵称（若存在）。
    返回被清除的设备数量。
    """
    neighbors = load_neighbors()
    nicknames = load_nicknames()
    to_delete = [mac for mac, entry in neighbors.items() if not entry.get("ip")]
    for mac in to_delete:
        del neighbors[mac]
        if mac in nicknames:
            del nicknames[mac]
    if to_delete:
        save_neighbors(neighbors)
        save_nicknames(nicknames)
    return len(to_delete)


def delete_device(mac):
    """
    从邻居表和昵称表中同时删除指定 MAC 的设备。
    返回是否至少删除了一个表中的条目。
    """
    mac = mac_to_str(mac)
    deleted = False
    if delete_neighbor(mac):
        deleted = True
    if delete_nickname(mac):
        deleted = True
    return deleted


# =============================================================================
# 昵称表业务逻辑
# =============================================================================

def set_nickname(mac, nickname):
    """
    为指定 MAC 设置昵称（要求昵称在全局唯一）。
    如果昵称已被其他 MAC 占用，返回 False；否则更新并保存，返回 True。
    """
    mac = mac_to_str(mac)
    nicknames = load_nicknames()
    # 检查昵称唯一性
    for m, n in nicknames.items():
        if n == nickname and m != mac:
            return False
    # 更新昵称
    add_or_update_nickname(mac, nickname)
    return True


def get_mac_by_ip(target_ip):
    """根据 IP 地址从邻居表中查找对应的 MAC 地址"""
    neighbors = load_neighbors()
    for mac, entry in neighbors.items():
        if entry.get("ip") == target_ip:
            return mac
    return None


def format_neighbor_table():
    """格式化邻居表为可读字符串"""
    neighbors = load_neighbors()
    if not neighbors:
        return "邻居表为空"
    lines = ["邻居表 (MAC -> IP, TTL):"]
    for mac, entry in neighbors.items():
        lines.append(f"  {mac} -> IP: {entry.get('ip')}, TTL: {entry.get('ttl')}")
    return "\n".join(lines)


def resolve_nickname_conflict_and_update(nickname, mac):
    """
    将指定 MAC 的昵称设为 nickname，如果与其他设备冲突，则修改其他设备的昵称加随机数。
    返回是否成功。
    """
    mac = mac_to_str(mac)
    nicknames = load_nicknames()
    # 1. 检查是否有其他设备使用相同昵称
    conflict_macs = [m for m, n in nicknames.items() if n == nickname and m != mac]
    if conflict_macs:
        # 为每个冲突设备生成新昵称：原昵称 + "_" + 4位随机数
        for cmac in conflict_macs:
            # 生成随机数，确保不与已有昵称重复（简单循环）
            while True:
                suffix = ''.join(random.choice('0123456789abcdef') for _ in range(4))
                new_nick = nickname + "_" + suffix
                # 检查是否已被其他设备使用
                if new_nick not in nicknames.values():
                    break
            nicknames[cmac] = new_nick
            print(f"[NEIGHBOR] 昵称冲突，将 {cmac} 的昵称改为 {new_nick}")
    # 2. 更新本机或指定设备的昵称
    nicknames[mac] = nickname
    save_nicknames(nicknames)
    return True

def update_self_nickname():
    """在启动或修改昵称后调用，处理本机昵称冲突并更新昵称表"""
    self_mac = get_self_mac()
    self_nick = g_device_nickname
    return resolve_nickname_conflict_and_update(self_nick, self_mac)