# config.py - 配置管理、全局变量、工具函数
# 提供所有配置文件的 CRUD（增删改查）操作

import json
import os
import time
import _thread
import machine
from util import mac_to_str, get_mac_short, get_default_nickname, get_self_mac
from constants import (
    DEFAULT_AP_IP, DEFAULT_AP_SUBNET,
    DEFAULT_STA_SSID, DEFAULT_STA_PASSWORD, DEFAULT_AP_SSID_PREFIX,
    DEFAULT_UDP_RECV_PORT, DEFAULT_UDP_BROADCAST_PORT,
    DEFAULT_UDP_POLL_INTERVAL, DEFAULT_LED_PIN,
    DEFAULT_STA_TIMEOUT,
    ROUTE_TTL_MAX, ROUTE_STEP, NEIGHBOR_TTL_MAX, HEARTBEAT_TIMEOUT,
    DEFAULT_NEIGHBOR_ADVERTISE_INTERVAL, DEFAULT_ROUTE_ADVERTISE_INTERVAL, DEFAULT_COMMANDS,
    DEFAULT_IR_BAUDRATE, DEFAULT_IR_TIMEOUT, DEFAULT_RESET_PIN, DEFAULT_RESET_HOLD_TIME
)

# =============================================================================
# 文件路径常量
# =============================================================================
SYSTEM_CONFIG_FILE = "system-config.json" # AP / UDP / LED 等系统参数
WIFI_CONFIG_FILE = "wifi-config.json"          # STA 模式凭据
NICKNAMES_FILE = "nicknames.json"         # 昵称表（MAC → 昵称）
NEIGHBORS_FILE = "neighbors.json"         # 邻居表（MAC → IP）
ROUTE_TABLE_FILE = "route_table.json"     # 路由表（MAC → {ip, ttl}）
NEIGHBOR_CONFIG_FILE = "neighbor-config.json"
ROUTE_CONFIG_FILE = "route-config.json"


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


# 控制配置全局变量
g_commands = DEFAULT_COMMANDS

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
        with open(WIFI_CONFIG_FILE, "w") as f:
            json.dump(DEFAULT_STA_CONFIG, f)
    print(f"[CONFIG] STA 配置: SSID='{ssid}'")
    return ssid, password

def save_wifi_config(ssid, password):
    """保存 WiFi 配置并更新全局变量"""
    global  g_sta_ssid, g_sta_password
    try:
        data = {"ssid": ssid, "password": password}
        with open(WIFI_CONFIG_FILE, "w") as f:
            json.dump(data, f)
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
            with open(SYSTEM_CONFIG_FILE, "w") as f:
                json.dump(config, f)
        return config
    except:
        # 文件不存在，创建默认，并生成 device_nickname
        default = DEFAULT_SYSTEM_CONFIG.copy()
        save_system_config(default)
        return default

def save_system_config(config):
    """保存系统配置，成功返回 True，失败返回 False"""
    try:
        with open(SYSTEM_CONFIG_FILE, "w") as f:
            json.dump(config, f)
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

# 心跳相关
_heartbeat_lock = _thread.allocate_lock()
heartbeat = {
    'udp_receiver': time.time(),
    'udp_neighbor': time.time(),
    'web_server': time.time(),
}

def update_heartbeat(name):
    """更新指定线程的心跳时间"""
    with _heartbeat_lock:
        heartbeat[name] = time.time()


def get_heartbeat(name):
    """获取指定线程的心跳时间"""
    with _heartbeat_lock:
        return heartbeat.get(name, 0)


def check_heartbeats():
    """检查所有线程心跳，超时返回需要重启的线程名列表"""
    now = time.time()
    dead = []
    with _heartbeat_lock:
        for name, last in heartbeat.items():
            if now - last > HEARTBEAT_TIMEOUT:
                dead.append(name)
    return dead


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
        with open(NEIGHBORS_FILE, "w") as f:
            json.dump(neighbors, f)
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

def add_or_update_neighbor(mac, ip, ttl=2):
    """添加或更新邻居条目，ttl 最大为 2"""
    mac = mac_to_str(mac)
    if ttl > 2:
        ttl = 2
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

def ttl_decrement_neighbors():
    """遍历邻居表，将所有条目的 TTL 减 1，删除 TTL <= 0 的条目，返回删除数量"""
    neighbors = load_neighbors()
    to_delete = []
    for mac, entry in neighbors.items():
        entry["ttl"] -= 1
        if entry["ttl"] <= 0:
            to_delete.append(mac)
    for mac in to_delete:
        del neighbors[mac]
    if to_delete:
        save_neighbors(neighbors)
    return len(to_delete)

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
        with open(NEIGHBOR_CONFIG_FILE, "w") as f:
            json.dump(DEFAULT_NEIGHBOR_CONFIG, f)
        return DEFAULT_NEIGHBOR_CONFIG.copy()

def save_neighbor_config(cfg):
    try:
        with open(NEIGHBOR_CONFIG_FILE, "w") as f:
            json.dump(cfg, f)
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
        with open(NICKNAMES_FILE, "w") as f:
            json.dump(nicknames, f)
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


def route_ttl_decrement():
    """
    遍历路由表，将所有条目的 TTL 减 1，删除 TTL <= 0 的条目。
    返回被删除的条目数量。
    """
    table = load_route_table()
    to_delete = []
    for mac, entry in table.items():
        entry["ttl"] -= 1
        if entry["ttl"] <= 0:
            to_delete.append(mac)
    for mac in to_delete:
        del table[mac]
    save_route_table(table)
    return len(to_delete)


# =============================================================================
# 路由表（MAC → {ip, ttl}）
# 文件：route_table.json
# 结构：{"AA:BB:CC:DD:EE:FF": {"ip": "192.168.1.200", "ttl": 4, "step": 4}, ...}
# =============================================================================
# =============================================================================
# 路由表常量重新导出（供其他模块使用）
# =============================================================================
ROUTE_TTL_MAX = ROUTE_TTL_MAX
ROUTE_STEP = ROUTE_STEP
NEIGHBOR_TTL_MAX = NEIGHBOR_TTL_MAX

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
        with open(ROUTE_TABLE_FILE, "w") as f:
            json.dump(table, f)
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

def add_or_update_route(mac, ip, ttl=None, step=ROUTE_STEP):
    """
    添加或更新一个路由条目
    - mac 自动标准化
    - 如果 ttl 为 None，则使用当前 TTL（若存在）或默认 4
    """
    mac = mac_to_str(mac)
    table = load_route_table()
    if mac in table:
        # 更新 IP，保留原 TTL（或使用指定 ttl）
        table[mac]["ip"] = ip
        if ttl is not None:
            table[mac]["ttl"] = ttl
        if step is not None:
            table[mac]["step"] = step
    else:
        # 新增，ttl 默认为 4
        table[mac] = {"ip": ip, "ttl": ttl if ttl is not None else 4, "step": step}
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

# =============================================================================
# 路由配置（route-config.json）
# =============================================================================

def load_route_config():
    try:
        with open(ROUTE_CONFIG_FILE, "r") as f:
            return json.load(f)
    except:
        with open(ROUTE_CONFIG_FILE, "w") as f:
            json.dump(DEFAULT_ROUTE_CONFIG, f)
        return DEFAULT_ROUTE_CONFIG.copy()

def save_route_config(cfg):
    try:
        with open(ROUTE_CONFIG_FILE, "w") as f:
            json.dump(cfg, f)
        return True
    except Exception as e:
        print(f"[CONFIG] 保存路由配置失败: {e}")
        return False


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
# 10. 统一加载入口（供 app.py 调用）
# =============================================================================

def load_all_configs():
    """
    加载所有配置文件，若文件不存在则自动创建。
    包括系统、WiFi、控制、舵机、IR、邻居、路由、昵称。
    """
    load_global_config()          # 加载系统配置并更新全局变量
    load_wifi_config()            # 加载 STA 凭据
    load_neighbors()              # 加载邻居表（如缺失则返回空字典）
    load_neighbor_config()
    load_route_table()            # 加载路由表（如缺失则返回空字典）
    load_route_config()
    load_nicknames()              # 加载昵称表（如缺失则返回空字典）

    print("[CONFIG] 所有配置加载完成（缺失文件已自动创建）")