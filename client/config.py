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
# config.py - 配置管理、全局变量、工具函数
# 提供所有配置文件的 CRUD（增删改查）操作

import json
import os
import time
import machine
from util import mac_to_str, get_mac_short, get_default_nickname, get_self_mac, get_file_lock, atomic_write, \
    ensure_config_dir
from constants import (
    DEFAULT_AP_IP, DEFAULT_AP_SUBNET,
    DEFAULT_STA_SSID, DEFAULT_STA_PASSWORD, DEFAULT_AP_SSID_PREFIX,
    DEFAULT_UDP_RECV_PORT, DEFAULT_UDP_BROADCAST_PORT,
    DEFAULT_UDP_POLL_INTERVAL, DEFAULT_LED_PIN,
    DEFAULT_STA_TIMEOUT,
    ROUTE_TTL_MAX, ROUTE_STEP, NEIGHBOR_TTL_MAX,
    DEFAULT_NEIGHBOR_ADVERTISE_INTERVAL, DEFAULT_ROUTE_ADVERTISE_INTERVAL,
    DEFAULT_IR_BAUDRATE, DEFAULT_IR_TIMEOUT,
    DEFAULT_RESET_PIN, DEFAULT_RESET_HOLD_TIME, NEIGHBOR_STEP
)


# =============================================================================
# 配置存储目录
# =============================================================================
CONFIG_DIR = "configs/"
# =============================================================================
# 文件路径常量
# =============================================================================
SYSTEM_CONFIG_FILE = CONFIG_DIR + "system-config.json" # AP / UDP / LED 等系统参数
WIFI_CONFIG_FILE = CONFIG_DIR + "wifi-config.json"          # STA 模式凭据
NICKNAMES_FILE = CONFIG_DIR + "nicknames.json"         # 昵称表（MAC → 昵称）
NEIGHBORS_FILE = CONFIG_DIR + "neighbors.json"         # 邻居表（MAC → IP）
ROUTE_TABLE_FILE = CONFIG_DIR + "route_table.json"     # 路由表（MAC → {ip, ttl}）
NEIGHBOR_CONFIG_FILE = CONFIG_DIR + "neighbor-config.json"
ROUTE_CONFIG_FILE = CONFIG_DIR + "route-config.json"

CONTROL_CONFIG_FILE = CONFIG_DIR + "control_config.json"
SERVO_CONFIG_FILE = CONFIG_DIR + "servo-config.json"
IR_CONFIG_FILE = CONFIG_DIR + "ir05t-config.json"

# =============================================================================
# 默认系统配置
# =============================================================================
DEFAULT_SYSTEM_CONFIG = {
    "ap_ssid": f"{DEFAULT_AP_SSID_PREFIX}{get_mac_short()}",
    "ap_password": "",
    "ap_ip": DEFAULT_AP_IP,
    "ap_subnet": DEFAULT_AP_SUBNET,
    "udp_recv_port": DEFAULT_UDP_RECV_PORT,
    "udp_broadcast_port": DEFAULT_UDP_BROADCAST_PORT,
    "udp_poll_interval": DEFAULT_UDP_POLL_INTERVAL,
    "led_pin": DEFAULT_LED_PIN,
    "sta_timeout": DEFAULT_STA_TIMEOUT,
    "device_nickname": get_default_nickname(),
    "reset_pin": DEFAULT_RESET_PIN,
    "reset_hold_time": DEFAULT_RESET_HOLD_TIME,
}

DEFAULT_STA_CONFIG = {
    "ssid": DEFAULT_STA_SSID,
    "password": DEFAULT_STA_PASSWORD
}

DEFAULT_NEIGHBOR_CONFIG = {
    "advertise_interval": DEFAULT_NEIGHBOR_ADVERTISE_INTERVAL,
}

DEFAULT_ROUTE_CONFIG = {
    "advertise_interval": DEFAULT_ROUTE_ADVERTISE_INTERVAL,
}

# =============================================================================
# 全局配置变量
# =============================================================================
g_ap_ssid = f"{DEFAULT_AP_SSID_PREFIX}{get_mac_short()}"
g_ap_password = ""
g_ap_ip = DEFAULT_AP_IP
g_ap_subnet = DEFAULT_AP_SUBNET
g_ap_broadcast_addr = "192.168.4.255"   # 将在 load_global_config 中计算
g_sta_timeout = DEFAULT_STA_TIMEOUT
g_udp_recv_port = DEFAULT_UDP_RECV_PORT
g_udp_broadcast_port = DEFAULT_UDP_BROADCAST_PORT
g_udp_poll_interval = DEFAULT_UDP_POLL_INTERVAL
g_led_pin = DEFAULT_LED_PIN
g_device_nickname = get_default_nickname()
g_reset_pin = DEFAULT_RESET_PIN
g_reset_hold_time = DEFAULT_RESET_HOLD_TIME

g_sta_ssid = DEFAULT_STA_SSID
g_sta_password = DEFAULT_STA_PASSWORD

g_neighbor_advertise_interval = DEFAULT_NEIGHBOR_ADVERTISE_INTERVAL

g_route_advertise_interval = DEFAULT_ROUTE_ADVERTISE_INTERVAL


g_reset_pin_obj = None


# =============================================================================
# WiFi 配置（STA 凭据）
# 文件：wifi-config.json
# 结构：{"ssid": "...", "password": "..."}
# =============================================================================

def load_wifi_config():
    """读取 WiFi 配置，更新全局 g_sta_ssid/g_sta_password，返回 (ssid, password)"""
    global  g_sta_ssid, g_sta_password
    try:
        with open(WIFI_CONFIG_FILE, "r") as f:
            data = json.load(f)
        ssid = data.get("ssid", DEFAULT_STA_SSID)
        password = data.get("password", DEFAULT_STA_PASSWORD)
        g_sta_ssid = ssid
        g_sta_password = password
        print(f"[CONFIG] 读取 STA 配置: SSID='{ssid}'")
        return (ssid, password) if ssid else (None, None)
    except Exception as e:
        print(f"[CONFIG] 读取 STA 配置失败: {e}")
        ssid = ""
        password = ""
        # 创建空配置
        try:
            lock = get_file_lock(WIFI_CONFIG_FILE)
            with lock:
                atomic_write(WIFI_CONFIG_FILE, DEFAULT_STA_CONFIG)
        except Exception as e:
            print(f"[CONFIG] 创建默认WiFi配置失败: {e}")
        # with open(WIFI_CONFIG_FILE, "w") as f:
        #     json.dump(DEFAULT_STA_CONFIG, f)
    print(f"[CONFIG] STA 配置: SSID='{ssid}'")
    return ssid, password

def save_wifi_config(ssid, password):
    """保存 WiFi 配置并更新全局变量"""
    global  g_sta_ssid, g_sta_password
    try:
        data = {"ssid": ssid, "password": password}
        lock = get_file_lock(WIFI_CONFIG_FILE)
        with lock:  # MicroPython 支持上下文管理器
            # 写入操作（见下文原子写）
            atomic_write(WIFI_CONFIG_FILE, data)
        # with open(WIFI_CONFIG_FILE, "w") as f:
        #     json.dump(data, f)
        g_sta_ssid = ssid
        g_sta_password = password
        print(f"[CONFIG] STA 配置已保存: SSID='{ssid}'")
        return True
    except Exception as e:
        print(f"[CONFIG] 保存系统配置失败: {e}")
        return False

def update_sta_timeout(new_timeout):
    """更新 STA 连接超时并保存到配置文件"""
    global g_sta_timeout
    config = load_system_config()
    config["sta_timeout"] = new_timeout
    save_system_config(config)
    g_sta_timeout = new_timeout

def reset_wifi_config():
    """重置 WiFi 配置（清空）"""
    save_wifi_config("", "")


# =============================================================================
# 系统配置（AP / UDP / LED / 超时等）
# 文件：system-config.json
# 结构：见 DEFAULT_SYSTEM_CONFIG
# =============================================================================

def load_system_config():
    """
    读取系统配置，缺失键自动补全为默认值。
    若文件不存在或损坏，则从旧 control_config.json 尝试迁移部分字段。
    """
    try:
        with open(SYSTEM_CONFIG_FILE, "r") as f:
            config = json.load(f)
        # 补全缺失的键
        need_save = False
        for key in DEFAULT_SYSTEM_CONFIG:
            if key not in config:
                config[key] = DEFAULT_SYSTEM_CONFIG[key]
                need_save = True
        if need_save:
            # 写回（补全后的）
            try:
                lock = get_file_lock(SYSTEM_CONFIG_FILE)
                with lock:
                    atomic_write(SYSTEM_CONFIG_FILE, config)
            except Exception as e:
                print(f"[CONFIG] 创建默认系统配置失败: {e}")
            # with open(SYSTEM_CONFIG_FILE, "w") as f:
            #     json.dump(config, f)
        return config
    except:
        # 文件不存在，创建默认，并生成 device_nickname
        default = DEFAULT_SYSTEM_CONFIG.copy()
        save_system_config(default)
        return default

def save_system_config(config):
    """保存系统配置，成功返回 True，失败返回 False"""
    try:
        lock = get_file_lock(SYSTEM_CONFIG_FILE)
        with lock:  # MicroPython 支持上下文管理器
            # 写入操作（见下文原子写）
            atomic_write(SYSTEM_CONFIG_FILE, config)
        # with open(SYSTEM_CONFIG_FILE, "w") as f:
        #     json.dump(config, f)
        return True
    except Exception as e:
        print(f"[CONFIG] 保存系统配置失败: {e}")
        return False

def reset_system_config():
    """重置系统配置为默认值"""
    save_system_config(DEFAULT_SYSTEM_CONFIG)

def update_system_config(key, value):
    """更新单个系统配置项（并保存）"""
    config = load_system_config()
    config[key] = value
    save_system_config(config)

def update_device_nickname(new_nickname):
    """更新设备昵称并保存到配置文件"""
    global g_device_nickname
    config = load_system_config()
    config["device_nickname"] = new_nickname
    save_system_config(config)
    g_device_nickname = new_nickname

def update_ap_ssid(new_ssid):
    """更新 AP SSID 并保存到配置文件"""
    global g_ap_ssid
    config = load_system_config()
    config["ap_ssid"] = new_ssid
    save_system_config(config)
    g_ap_ssid = new_ssid

def update_ap_password(new_password):
    """更新 AP 密码并保存到配置文件"""
    global g_ap_password
    config = load_system_config()
    config["ap_password"] = new_password
    save_system_config(config)
    g_ap_password = new_password

def update_ap_ip(new_ip):
    """更新 AP IP 并保存到配置文件"""
    global g_ap_ip, g_ap_broadcast_addr
    config = load_system_config()
    config["ap_ip"] = new_ip
    save_system_config(config)
    g_ap_ip = new_ip
    # 重新计算广播地址
    ip_parts = new_ip.split('.')
    if len(ip_parts) == 4:
        g_ap_broadcast_addr = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.255"

def update_ap_netmask(new_mask):
    """更新 AP 子网掩码并保存到配置文件"""
    global g_ap_subnet
    config = load_system_config()
    config["ap_subnet"] = new_mask
    save_system_config(config)
    g_ap_subnet = new_mask

def update_ap_gateway(new_gw):
    """更新 AP 网关（实际是 IP）并保存到配置文件"""
    global g_ap_ip, g_ap_broadcast_addr
    config = load_system_config()
    config["ap_ip"] = new_gw
    save_system_config(config)
    g_ap_ip = new_gw
    ip_parts = new_gw.split('.')
    if len(ip_parts) == 4:
        g_ap_broadcast_addr = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.255"

def update_reset_pin(new_pin):
    global g_reset_pin
    config = load_system_config()
    config["reset_pin"] = new_pin
    save_system_config(config)
    g_reset_pin = new_pin

def update_reset_hold_time(new_time):
    global g_reset_hold_time
    config = load_system_config()
    config["reset_hold_time"] = new_time
    save_system_config(config)
    g_reset_hold_time = new_time


# =============================================================================
# 邻居表（MAC → {ip, ttl}）
# 文件：neighbors.json
# 结构：{"AA:BB:CC:DD:EE:FF": {"ip": "192.168.1.100", "ttl": 2}, ...}
# =============================================================================

def load_neighbors():
    """读取邻居表，返回 {mac: {"ip": ip, "ttl": ttl}}"""
    try:
        with open(NEIGHBORS_FILE, "r") as f:
            data = json.load(f)
        # 确保每个条目都是字典格式
        for mac, val in data.items():
            if isinstance(val, str):
                data[mac] = {"ip": val, "ttl": 2}
            elif not isinstance(val, dict):
                data[mac] = {"ip": str(val), "ttl": 2}
        return data
    except:
        return {}

def save_neighbors(neighbors):
    """保存邻居表（全量覆盖）"""
    try:
        lock = get_file_lock(NEIGHBORS_FILE)
        with lock:  # MicroPython 支持上下文管理器
            # 写入操作（见下文原子写）
            atomic_write(NEIGHBORS_FILE, neighbors)
        # with open(NEIGHBORS_FILE, "w") as f:
        #     json.dump(neighbors, f)
        return True
    except Exception as e:
        print(f"[CONFIG] 保存系统配置失败: {e}")
        return False

def get_neighbor(mac):
    """查询指定 MAC 的 IP（不存在返回 None）"""
    mac = mac_to_str(mac)
    neighbors = load_neighbors()
    entry = neighbors.get(mac)
    return entry["ip"] if entry else None

def get_neighbor_entry(mac):
    """返回 {"ip": ip, "ttl": ttl} 或 None"""
    mac = mac_to_str(mac)
    neighbors = load_neighbors()
    return neighbors.get(mac)

def add_or_update_neighbor(mac, ip, ttl=NEIGHBOR_STEP):
    """添加或更新邻居条目，ttl 最大为 NEIGHBOR_TTL_MAX"""
    mac = mac_to_str(mac)
    if ttl > NEIGHBOR_TTL_MAX:
        ttl = NEIGHBOR_TTL_MAX
    neighbors = load_neighbors()
    neighbors[mac] = {"ip": ip, "ttl": ttl}
    save_neighbors(neighbors)
    return True

def delete_neighbor(mac):
    mac = mac_to_str(mac)
    neighbors = load_neighbors()
    if mac in neighbors:
        del neighbors[mac]
        save_neighbors(neighbors)
        return True
    return False

def delete_neighbors(mac_list):
    """
    从邻居表中批量删除多个 MAC 地址。
    参数 mac_list: 字符串列表，每个元素为 MAC 地址（可自动标准化）。
    返回实际删除的条目数量。
    """
    if not mac_list:
        return 0
    # 标准化所有 MAC
    normalized = [mac_to_str(m) for m in mac_list]
    neighbors = load_neighbors()
    deleted_count = 0
    for mac in normalized:
        if mac in neighbors:
            del neighbors[mac]
            deleted_count += 1
    if deleted_count > 0:
        save_neighbors(neighbors)
    return deleted_count

def ttl_decrement_neighbors():
    """
    将邻居表中所有条目的 TTL 减 1，删除 TTL <= 0 的条目。
    返回被删除的 MAC 列表。
    """
    neighbors = load_neighbors()
    to_delete = []
    for mac, entry in neighbors.items():
        print(f"[邻居表操作] {mac} ttl: {entry['ttl']}-1")
        entry["ttl"] -= 1
        if entry["ttl"] <= 0:
            print(f"[邻居表操作] {mac} ttl归零")
            to_delete.append(mac)
    for mac in to_delete:
        print(f"[邻居表操作] 从邻居表删除 {mac} ")
        del neighbors[mac]
    save_neighbors(neighbors)
    return to_delete

def reset_neighbors():
    """清空邻居表"""
    save_neighbors({})

def update_neighbor_advertise_interval(interval):
    """更新邻居广播间隔并保存"""
    global g_neighbor_advertise_interval
    cfg = load_neighbor_config()
    cfg["advertise_interval"] = interval
    save_neighbor_config(cfg)
    g_neighbor_advertise_interval = interval


# =============================================================================
# 邻居配置（neighbor-config.json）
# =============================================================================

def load_neighbor_config():
    try:
        with open(NEIGHBOR_CONFIG_FILE, "r") as f:
            return json.load(f)
    except:
        try:
            lock = get_file_lock(NEIGHBOR_CONFIG_FILE)
            with lock:
                atomic_write(NEIGHBOR_CONFIG_FILE, DEFAULT_NEIGHBOR_CONFIG)
        except Exception as e:
            print(f"[CONFIG] 创建默认邻居配置失败: {e}")
        # with open(NEIGHBOR_CONFIG_FILE, "w") as f:
        #     json.dump(DEFAULT_NEIGHBOR_CONFIG, f)
        return DEFAULT_NEIGHBOR_CONFIG.copy()

def save_neighbor_config(cfg):
    try:
        lock = get_file_lock(NEIGHBOR_CONFIG_FILE)
        with lock:  # MicroPython 支持上下文管理器
            # 写入操作（见下文原子写）
            atomic_write(NEIGHBOR_CONFIG_FILE, cfg)
        # with open(NEIGHBOR_CONFIG_FILE, "w") as f:
        #     json.dump(cfg, f)
        return True
    except Exception as e:
        print(f"[CONFIG] 保存邻居配置失败: {e}")
        return False

def update_route_advertise_interval(interval):
    """更新路由通告间隔并保存"""
    global g_route_advertise_interval
    cfg = load_route_config()
    cfg["advertise_interval"] = interval
    save_route_config(cfg)
    g_route_advertise_interval = interval


# =============================================================================
# 昵称表（MAC → 昵称）
# 文件：nicknames.json
# 结构：{"AA:BB:CC:DD:EE:FF": "device1", ...}
# =============================================================================

def load_nicknames():
    """读取昵称表，若本机昵称为空则自动补全为默认昵称"""
    try:
        with open(NICKNAMES_FILE, "r") as f:
            data = json.load(f)
    except:
        data = {}

    # 检查本机 MAC 是否有空昵称
    self_mac = get_self_mac()
    if self_mac in data and not data[self_mac]:
        # 空昵称，替换为默认昵称
        data[self_mac] = get_default_nickname()
        save_nicknames(data)
    return data

def save_nicknames(nicknames):
    """保存昵称表（全量覆盖）"""
    try:
        lock = get_file_lock(NICKNAMES_FILE)
        with lock:  # MicroPython 支持上下文管理器
            # 写入操作（见下文原子写）
            atomic_write(NICKNAMES_FILE, nicknames)
        # with open(NICKNAMES_FILE, "w") as f:
        #     json.dump(nicknames, f)
        return True
    except Exception as e:
        print(f"[CONFIG] 保存系统配置失败: {e}")
        return False

def reset_nicknames():
    """清空昵称表"""
    save_nicknames({})

def get_nickname(mac):
    """查询指定 MAC 的昵称（不存在返回 None）"""
    mac = mac_to_str(mac)
    nicknames = load_nicknames()
    return nicknames.get(mac)

def add_or_update_nickname(mac, nickname):
    """添加或更新一个昵称条目（MAC 自动标准化）"""
    mac = mac_to_str(mac)
    nicknames = load_nicknames()
    # 可选：检查昵称唯一性（此处不强制，由调用方决定）
    nicknames[mac] = nickname
    save_nicknames(nicknames)
    return True

def delete_nickname(mac):
    """删除指定 MAC 的昵称条目，返回是否删除成功"""
    mac = mac_to_str(mac)
    nicknames = load_nicknames()
    if mac in nicknames:
        del nicknames[mac]
        save_nicknames(nicknames)
        return True
    return False

def delete_nicknames(mac_list):
    """
    从昵称表中批量删除多个 MAC 地址。
    返回实际删除的条目数量。
    """
    if not mac_list:
        return 0
    normalized = [mac_to_str(m) for m in mac_list]
    nicknames = load_nicknames()
    deleted_count = 0
    for mac in normalized:
        if mac in nicknames:
            del nicknames[mac]
            deleted_count += 1
    if deleted_count > 0:
        save_nicknames(nicknames)
    return deleted_count

def route_ttl_decrement():
    """
    将路由表中所有条目的 TTL 减 1，删除 TTL <= 0 的条目。
    返回被删除的 MAC 列表。
    """
    table = load_route_table()
    to_delete = []
    for mac, entry in table.items():
        print(f"[路由表操作] {mac} ttl: {entry['ttl']}-1")
        entry["ttl"] -= 1
        if entry["ttl"] <= 0:
            print(f"[路由表操作] {mac} ttl归零")
            to_delete.append(mac)
    for mac in to_delete:
        print(f"[路由表操作] 从路由表删除 {mac} ")
        del table[mac]
    save_route_table(table)
    return to_delete


# =============================================================================
# 路由表（MAC → {ip, ttl}）
# 文件：route_table.json
# 结构：{"AA:BB:CC:DD:EE:FF": {"ip": "192.168.1.200", "ttl": 4, "step": 4}, ...}
# =============================================================================
# =============================================================================
# 路由表常量重新导出（供其他模块使用）
# =============================================================================
def load_route_table():
    """读取路由表"""
    try:
        with open(ROUTE_TABLE_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_route_table(table):
    """保存路由表（全量覆盖）"""
    try:
        lock = get_file_lock(ROUTE_TABLE_FILE)
        with lock:  # MicroPython 支持上下文管理器
            # 写入操作（见下文原子写）
            atomic_write(ROUTE_TABLE_FILE, table)
        # with open(ROUTE_TABLE_FILE, "w") as f:
        #     json.dump(table, f)
        return True
    except Exception as e:
        print(f"[CONFIG] 保存系统配置失败: {e}")
        return False

def reset_route_table():
    """清空路由表"""
    save_route_table({})

def get_route(mac):
    """查询指定 MAC 的路由条目（不存在返回 None）"""
    mac = mac_to_str(mac)
    table = load_route_table()
    return table.get(mac)

def add_or_update_route(mac, ip, ttl=None, step=ROUTE_STEP, source=None):
    """
    添加或更新路由条目，source 为来源 MAC（谁告诉我的）。
    """
    mac = mac_to_str(mac)
    table = load_route_table()
    if mac in table:
        table[mac]["ip"] = ip
        if ttl is not None:
            table[mac]["ttl"] = ttl
        if step is not None:
            table[mac]["step"] = step
        if source is not None:
            table[mac]["source"] = source
    else:
        table[mac] = {
            "ip": ip,
            "ttl": ttl if ttl is not None else 4,
            "step": step,
            "source": source
        }
    save_route_table(table)
    return True

def delete_route(mac):
    """删除指定 MAC 的路由条目，返回是否删除成功"""
    mac = mac_to_str(mac)
    table = load_route_table()
    if mac in table:
        del table[mac]
        save_route_table(table)
        return True
    return False

def delete_routes(mac_list):
    """
    从路由表中批量删除多个 MAC 地址。
    返回实际删除的条目数量。
    """
    if not mac_list:
        return 0
    normalized = [mac_to_str(m) for m in mac_list]
    table = load_route_table()
    deleted_count = 0
    for mac in normalized:
        if mac in table:
            del table[mac]
            deleted_count += 1
    if deleted_count > 0:
        save_route_table(table)
    return deleted_count


# =============================================================================
# 路由配置（route-config.json）
# =============================================================================

def load_route_config():
    try:
        with open(ROUTE_CONFIG_FILE, "r") as f:
            return json.load(f)
    except:
        try:
            lock = get_file_lock(ROUTE_CONFIG_FILE)
            with lock:
                atomic_write(ROUTE_CONFIG_FILE, DEFAULT_ROUTE_CONFIG)
        except Exception as e:
            print(f"[CONFIG] 创建默认路由配置失败: {e}")
        # with open(ROUTE_CONFIG_FILE, "w") as f:
        #     json.dump(DEFAULT_ROUTE_CONFIG, f)
        return DEFAULT_ROUTE_CONFIG.copy()

def save_route_config(cfg):
    try:
        lock = get_file_lock(ROUTE_CONFIG_FILE)
        with lock:  # MicroPython 支持上下文管理器
            # 写入操作（见下文原子写）
            atomic_write(ROUTE_CONFIG_FILE, cfg)
        # with open(ROUTE_CONFIG_FILE, "w") as f:
        #     json.dump(cfg, f)
        return True
    except Exception as e:
        print(f"[CONFIG] 保存路由配置失败: {e}")
        return False


# =============================================================================
# 删除设备
# =============================================================================

def delete_device(mac):
    """
    从邻居表和昵称表和路由表中同时删除指定 MAC 的设备。
    返回是否至少删除了一个表中的条目。
    """
    mac = mac_to_str(mac)
    deleted = False
    if delete_neighbor(mac):
        deleted = True
    if delete_nickname(mac):
        deleted = True
    if delete_route(mac):
        deleted = True
    return deleted

def delete_devices(mac_list):
    """
    从邻居表、昵称表、路由表中批量删除指定 MAC 地址的设备。
    返回一个字典，包含每个表删除的数量。
    """
    if not mac_list:
        return {"neighbors": 0, "nicknames": 0, "routes": 0}
    # 标准化所有 MAC
    normalized = [mac_to_str(m) for m in mac_list]
    result = {}
    result["neighbors"] = delete_neighbors(normalized)
    result["nicknames"] = delete_nicknames(normalized)
    result["routes"] = delete_routes(normalized)
    return result


# =============================================================================
# 恢复出厂设置（重置）
# =============================================================================

def reset_to_factory():
    """
    删除所有配置文件并重启设备，恢复出厂设置。
    注意：此函数会调用 machine.reset()，不会返回。
    """
    files_to_delete = [
        SYSTEM_CONFIG_FILE,
        WIFI_CONFIG_FILE,
        NEIGHBORS_FILE,
        ROUTE_TABLE_FILE,
        NICKNAMES_FILE,
        NEIGHBOR_CONFIG_FILE,
        ROUTE_CONFIG_FILE,
        CONTROL_CONFIG_FILE,
        SERVO_CONFIG_FILE,
        IR_CONFIG_FILE,
    ]
    deleted = []
    for f in files_to_delete:
        try:
            os.remove(f)
            deleted.append(f)
        except Exception as e:
            print(f"[RESET] 删除 {f} 失败: {e}")
    print(f"[RESET] 已删除 {len(deleted)} 个配置文件")
    print("[RESET] 设备即将重启...")
    time.sleep(1)
    machine.reset()


# =============================================================================
# 全局配置加载（将 system-config.json 同步到 g_* 变量）
# =============================================================================

def load_global_config():
    """
    从 system-config.json 读取配置并更新全局变量 g_*
    同时计算广播地址（基于 ap_ip）
    """
    global g_ap_ssid, g_ap_password, g_ap_ip, g_ap_subnet
    global g_udp_recv_port, g_udp_broadcast_port, g_ap_broadcast_addr
    global g_udp_poll_interval, g_led_pin, g_sta_timeout
    global g_device_nickname, g_neighbor_advertise_interval
    global g_route_advertise_interval
    global g_reset_pin, g_reset_hold_time

    config = load_system_config()
    g_ap_ssid = config["ap_ssid"]
    g_ap_password = config["ap_password"]
    g_ap_ip = config["ap_ip"]
    g_ap_subnet = config["ap_subnet"]
    g_sta_timeout = config.get("sta_timeout", DEFAULT_STA_TIMEOUT)
    g_udp_recv_port = config["udp_recv_port"]
    g_udp_broadcast_port = config["udp_broadcast_port"]
    g_udp_poll_interval = config.get("udp_poll_interval", DEFAULT_UDP_POLL_INTERVAL)
    g_led_pin = config.get("led_pin", DEFAULT_LED_PIN)
    g_device_nickname = config.get("device_nickname", get_default_nickname())  # 若缺失则生成
    g_reset_pin = config.get("reset_pin", DEFAULT_RESET_PIN)
    g_reset_hold_time = config.get("reset_hold_time", DEFAULT_RESET_HOLD_TIME)

    # 从独立配置文件读取间隔
    neighbor_cfg = load_neighbor_config()
    g_neighbor_advertise_interval = neighbor_cfg.get("advertise_interval", DEFAULT_NEIGHBOR_ADVERTISE_INTERVAL)

    route_cfg = load_route_config()
    g_route_advertise_interval = route_cfg.get("advertise_interval", DEFAULT_ROUTE_ADVERTISE_INTERVAL)


    # 根据 AP IP 计算广播地址（假设 /24）
    ip_parts = g_ap_ip.split('.')
    if len(ip_parts) == 4:
        g_ap_broadcast_addr = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.255"
    else:
        g_ap_broadcast_addr = "192.168.4.255"
    print(f"[CONFIG] 广播地址: {g_ap_broadcast_addr}")

# =============================================================================
# 7. 控制命令配置（control_config.json）
#    结构: {"commands": {"模块名": [{"cmd": "...", "desc": "..."}, ...]}}
# =============================================================================

def load_control_config():
    """
    此函数已废弃，因为命令配置已拆分为 commands/*.json。
    保留此函数仅用于兼容旧代码，实际上不会加载 control_config.json。
    推荐直接使用 loader.load_commands()。
    """
    # 不再从 control_config.json 读取
    # 返回一个空字典，避免破坏旧代码
    print("[CONFIG] load_control_config() 已废弃，请使用 loader.load_commands()")
    return {}


# =============================================================================
# 8. 舵机配置（servo-config.json）
#    结构: {"舵机名称": {"pin": 引脚, "init_angle": 角度, "groups": {"动作组名": [角度列表]}}, ...}
# =============================================================================

def load_servo_config():
    """负载伺服配置"""
    try:
        with open(SERVO_CONFIG_FILE, "r") as f:
            return json.load(f)
    except (OSError, ValueError):
        try:
            lock = get_file_lock(SERVO_CONFIG_FILE)
            with lock:
                atomic_write(SERVO_CONFIG_FILE, {})
        except Exception as e:
            print(f"[CONFIG] 创建负载伺服配置失败: {e}")
        # with open(SERVO_CONFIG_FILE, "w") as f:
        #     json.dump({}, f)
        print("[CONFIG] 已创建空 servo-config.json")
        return {}

def save_servo_config(servo_config):
    """保存伺服配置"""
    try:
        lock = get_file_lock(SERVO_CONFIG_FILE)
        with lock:  # MicroPython 支持上下文管理器
            # 写入操作（见下文原子写）
            atomic_write(SERVO_CONFIG_FILE, servo_config)
        # with open(SERVO_CONFIG_FILE, "w") as f:
        #     json.dump(servo_config, f)
        return True
    except Exception as e:
        print(f"[舵机配置] 保存失败: {e}")
        return False


# =============================================================================
# 8. 红外配置（ir05t-config.json）
#    结构: {设备名: {tx_pin, rx_pin, baudrate, timeout, data}}
# =============================================================================

def load_ir_config():
    """加载 IR 设备配置，返回字典 {设备名: {tx_pin, rx_pin, baudrate, timeout, data}}"""
    try:
        with open(IR_CONFIG_FILE, "r") as f:
            return json.load(f)
    except (OSError, ValueError):
        # 文件不存在或损坏，创建空配置
        try:
            lock = get_file_lock(IR_CONFIG_FILE)
            with lock:
                atomic_write(IR_CONFIG_FILE, {})
        except Exception as e:
            print(f"[CONFIG] 创建负载伺服配置失败: {e}")
        # with open(IR_CONFIG_FILE, "w") as f:
        #     json.dump({}, f)
        return {}

def save_ir_config(config_dict):
    """保存 IR 设备配置"""
    try:
        lock = get_file_lock(IR_CONFIG_FILE)
        with lock:  # MicroPython 支持上下文管理器
            # 写入操作（见下文原子写）
            atomic_write(IR_CONFIG_FILE, config_dict)
        # with open(IR_CONFIG_FILE, "w") as f:
        #     json.dump(config_dict, f)
        return True
    except Exception as e:
        print(f"[IR] 保存配置失败: {e}")
        return False

def get_ir_device(name):
    """获取指定设备的配置，不存在返回 None"""
    cfg = load_ir_config()
    return cfg.get(name)

def set_ir_device(name, tx_pin, rx_pin, baudrate=None, timeout=None, uart_id=None):
    if baudrate is None:
        baudrate = DEFAULT_IR_BAUDRATE
    if timeout is None:
        timeout = DEFAULT_IR_TIMEOUT
    if uart_id is None:
        uart_id = 1
    cfg = load_ir_config()
    if name not in cfg:
        cfg[name] = {"tx_pin": tx_pin, "rx_pin": rx_pin,
                     "baudrate": baudrate, "timeout": timeout,
                     "uart_id": uart_id, "data": {}}
    else:
        cfg[name]["tx_pin"] = tx_pin
        cfg[name]["rx_pin"] = rx_pin
        cfg[name]["baudrate"] = baudrate
        cfg[name]["timeout"] = timeout
        cfg[name]["uart_id"] = uart_id
    return save_ir_config(cfg)

def delete_ir_device(name):
    """删除设备及其所有数据"""
    cfg = load_ir_config()
    if name not in cfg:
        return False
    del cfg[name]
    return save_ir_config(cfg)

def list_ir_devices():
    """返回设备名称列表"""
    cfg = load_ir_config()
    return list(cfg.keys())

def get_ir_data(device_name, data_name):
    """获取指定设备下的学习数据，返回 hex 字符串或 None"""
    cfg = load_ir_config()
    dev = cfg.get(device_name)
    if dev:
        return dev.get("data", {}).get(data_name)
    return None

def set_ir_data(device_name, data_name, hex_data):
    """保存学习数据到指定设备"""
    cfg = load_ir_config()
    if device_name not in cfg:
        return False
    if "data" not in cfg[device_name]:
        cfg[device_name]["data"] = {}
    cfg[device_name]["data"][data_name] = hex_data
    return save_ir_config(cfg)

def delete_ir_data(device_name, data_name):
    """删除指定设备下的某条数据"""
    cfg = load_ir_config()
    dev = cfg.get(device_name)
    if not dev:
        return False
    data = dev.get("data", {})
    if data_name in data:
        del data[data_name]
        return save_ir_config(cfg)
    return False

def list_ir_data_names(device_name):
    """返回指定设备下所有数据名称"""
    cfg = load_ir_config()
    dev = cfg.get(device_name)
    if dev:
        return list(dev.get("data", {}).keys())
    return []


# =============================================================================
# 引脚冲突检查
# =============================================================================

def get_all_pins_from_configs():
    """
    遍历所有配置文件，收集所有已使用的引脚。
    返回字典：{pin: [ (owner, type), ... ]}
    """
    pins_info = {}
    # 舵机配置
    servo_cfg = load_servo_config()
    for name, cfg in servo_cfg.items():
        pin = cfg.get('pin')
        if pin is not None:
            pins_info.setdefault(pin, []).append((f"舵机-{name}", "servo"))
    # IR 配置
    ir_cfg = load_ir_config()
    for name, cfg in ir_cfg.items():
        tx = cfg.get('tx_pin')
        rx = cfg.get('rx_pin')
        if tx is not None:
            pins_info.setdefault(tx, []).append((f"IR-{name}-TX", "ir"))
        if rx is not None:
            pins_info.setdefault(rx, []).append((f"IR-{name}-RX", "ir"))
    # 后续可扩展其他设备（如 LED 等，但 LED 是固定的，不纳入配置）
    return pins_info

def check_pin_conflicts(pin=None, exclude_owners=None):
    """
    检查所有引脚冲突情况。
    如果指定 pin，则检查该引脚是否被其他设备占用。
    exclude_owners: 要排除的 owner 列表（字符串），这些 owner 视为不冲突。
    返回字典：
        conflicts: {pin: [owners]}   # 存在冲突的引脚
        has_conflict: bool
        pin_info: {pin: [owners]}   # 所有引脚信息
    """
    pins_info = get_all_pins_from_configs()
    conflicts = {}
    for p, owners in pins_info.items():
        # 如果指定了排除列表，过滤掉这些 owner
        filtered = [o for o in owners if o[0] not in (exclude_owners or [])]
        if len(filtered) > 0:
            conflicts[p] = filtered
    if pin is not None:
        # 检查该 pin 是否在冲突中
        if pin in conflicts:
            return {'conflicts': {pin: conflicts[pin]}, 'has_conflict': True, 'pin_info': pins_info}
        elif pin in pins_info:
            # 被占用但无冲突（只有一个 owner 或排除后只剩一个）
            return {'conflicts': {}, 'has_conflict': False, 'pin_info': pins_info}
        else:
            return {'conflicts': {}, 'has_conflict': False, 'pin_info': pins_info}
    else:
        return {'conflicts': conflicts, 'has_conflict': bool(conflicts), 'pin_info': pins_info}


# =============================================================================
# 10. 统一加载入口（供 app.py 调用）
# =============================================================================

def load_all_configs():
    """
    加载所有配置文件，若文件不存在则自动创建。
    包括系统、WiFi、控制、舵机、IR、邻居、路由、昵称。
    """
    ensure_config_dir(CONFIG_DIR)
    load_global_config()          # 加载系统配置并更新全局变量
    load_wifi_config()            # 加载 STA 凭据
    load_neighbors()              # 加载邻居表（如缺失则返回空字典）
    load_neighbor_config()
    load_route_table()            # 加载路由表（如缺失则返回空字典）
    load_route_config()
    load_nicknames()              # 加载昵称表（如缺失则返回空字典）

    load_control_config()         # 加载控制命令
    load_servo_config()           # 创建空舵机配置（如缺失）
    load_ir_config()                # 创建空IR配置（如缺失）

    print("[CONFIG] 所有配置加载完成（缺失文件已自动创建）")