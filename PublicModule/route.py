# route.py - 路由表业务逻辑模块
"""
提供路由表的 TTL 管理、添加、删除、查询等高级操作。
底层文件读写由 config 模块统一管理，本模块只负责路由特定的业务逻辑。
"""

# =============================================================================
# 导入所需模块
# =============================================================================
import config
from config import (
    load_route_table, save_route_table, route_ttl_decrement,
    add_or_update_route, delete_route, get_route,
    ROUTE_TTL_MAX, ROUTE_STEP
)
from util import mac_to_str

# =============================================================================
# 重新导出基础读写函数（保持接口兼容）
# =============================================================================
# 以下函数虽然从 config 导入，但在本模块重新导出，确保其他模块
# 通过 import route 仍能调用 route.load_route_table() 等。
# 无需重复定义，直接重命名即可（实际上无需显式操作，因为 from ... import
# 已经将函数绑定到本模块命名空间，外界 import route 后即可直接使用。


# =============================================================================
# 路由表业务逻辑
# =============================================================================


def route_add(mac, ip, ttl_increment=2, step=ROUTE_STEP):
    """
    添加或更新一个路由条目。
    如果 MAC 已存在，则 IP 更新为新的值，且 TTL 增加 ttl_increment（但不超出 ROUTE_TTL_MAX）。
    如果 MAC 不存在，则新建条目，TTL 设为 min(ttl_increment, ROUTE_TTL_MAX)。
    返回 True（总是成功）。
    """
    mac = mac_to_str(mac)
    existing = get_route(mac)
    if existing:
        new_ttl = min(existing["ttl"] + ttl_increment, ROUTE_TTL_MAX)
    else:
        new_ttl = min(ttl_increment, ROUTE_TTL_MAX)
    add_or_update_route(mac, ip, new_ttl, step)
    return True


def route_set_ttl(mac, ip, ttl=ROUTE_TTL_MAX, step=ROUTE_STEP):
    """
    强制设置路由条目的 IP 和 TTL（不递增，直接覆盖）。
    若 MAC 不存在则新建。
    返回 True。
    """
    mac = mac_to_str(mac)
    add_or_update_route(mac, ip, ttl, step)
    return True


def route_delete(mac):
    """
    删除指定 MAC 的路由条目。
    如果存在则删除并返回 True，否则返回 False。
    """
    mac = mac_to_str(mac)
    return delete_route(mac)


def route_get_table():
    """
    返回当前完整路由表（字典，MAC → {ip, ttl}）。
    """
    return load_route_table()


def format_route_table():
    """格式化路由表为可读字符串"""
    table = load_route_table()
    if not table:
        return "路由表为空"
    lines = ["路由表 (MAC -> IP, TTL, Step):"]
    for mac, entry in table.items():
        lines.append(f"  {mac} -> IP: {entry.get('ip')}, TTL: {entry.get('ttl')}, Step: {entry.get('step')}")
    return "\n".join(lines)