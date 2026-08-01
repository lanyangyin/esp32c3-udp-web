# config.py - 配置管理、全局变量、工具函数
# 提供所有配置文件的 CRUD（增删改查）操作

import json
from util import mac_to_str, get_mac_short, get_default_nickname
from constants import (
    DEFAULT_AP_IP, DEFAULT_AP_SUBNET,
    DEFAULT_UDP_RECV_PORT, DEFAULT_UDP_BROADCAST_PORT,
    DEFAULT_UDP_POLL_INTERVAL, DEFAULT_LED_PIN,
    DEFAULT_MAX_UDP_MESSAGES, DEFAULT_STA_TIMEOUT,
    ROUTE_TTL_MAX, ROUTE_STEP, NEIGHBOR_TTL_MAX,
    DEFAULT_NEIGHBOR_ADVERTISE_INTERVAL, DEFAULT_ROUTE_ADVERTISE_INTERVAL
)

# =============================================================================
# 文件路径常量
# =============================================================================
SYSTEM_CONFIG_FILE = "system-config.json" # AP / UDP / LED 等系统参数
WIFI_CONFIG_FILE = "wifi-config.json"          # STA 模式凭据
NICKNAMES_FILE = "nicknames.json"         # 昵称表（MAC → 昵称）
NEIGHBORS_FILE = "neighbors.json"         # 邻居表（MAC → IP）
ROUTE_TABLE_FILE = "route_table.json"     # 路由表（MAC → {ip, ttl}）

# =============================================================================
# 默认系统配置
# =============================================================================
DEFAULT_SYSTEM_CONFIG = {
    "ap_ssid": f"ESP32-C3-Setup-{get_mac_short()}",
    "ap_password": "",
    "ap_ip": DEFAULT_AP_IP,
    "ap_subnet": DEFAULT_AP_SUBNET,
    "udp_recv_port": DEFAULT_UDP_RECV_PORT,
    "udp_broadcast_port": DEFAULT_UDP_BROADCAST_PORT,
    "udp_poll_interval": DEFAULT_UDP_POLL_INTERVAL,
    "led_pin": DEFAULT_LED_PIN,
    "max_udp_messages": DEFAULT_MAX_UDP_MESSAGES,
    "sta_timeout": DEFAULT_STA_TIMEOUT,
    "device_nickname": get_default_nickname(),
    "neighbor_advertise_interval": DEFAULT_NEIGHBOR_ADVERTISE_INTERVAL,
    "route_advertise_interval": DEFAULT_ROUTE_ADVERTISE_INTERVAL,
}

# =============================================================================
# 全局配置变量（由 load_global_config() 从 system-config.json 加载）
# =============================================================================
g_ap_ssid = DEFAULT_SYSTEM_CONFIG["ap_ssid"]
g_ap_password = ""
g_ap_ip = DEFAULT_AP_IP
g_ap_subnet = DEFAULT_AP_SUBNET
g_ap_broadcast_addr = "192.168.4.255"   # 将在 load_global_config 中计算
g_sta_timeout = DEFAULT_STA_TIMEOUT
g_udp_recv_port = DEFAULT_UDP_RECV_PORT
g_udp_broadcast_port = DEFAULT_UDP_BROADCAST_PORT
g_udp_poll_interval = DEFAULT_UDP_POLL_INTERVAL
g_max_udp_messages = DEFAULT_MAX_UDP_MESSAGES
g_led_pin = DEFAULT_LED_PIN
g_device_nickname = ""
g_neighbor_advertise_interval = DEFAULT_NEIGHBOR_ADVERTISE_INTERVAL
g_route_advertise_interval = DEFAULT_ROUTE_ADVERTISE_INTERVAL


# STA 凭据全局变量（由 load_wifi_config 更新）
g_sta_ssid = ""
g_sta_password = ""

# =============================================================================
# WiFi 配置（STA 凭据）
# 文件：wifi-config.json
# 结构：{"ssid": "...", "password": "..."}
# =============================================================================

def load_wifi_config():
    """读取 WiFi 配置，更新全局 g_sta_ssid/g_sta_password，返回 (ssid, password)"""
    global g_sta_ssid, g_sta_password
    try:
        with open(WIFI_CONFIG_FILE, "r") as f:
            data = json.load(f)
        ssid = data.get("ssid", "")
        password = data.get("password", "")
        print(f"[CONFIG] 读取 STA 配置: SSID='{ssid}'")
        return (ssid, password) if ssid else (None, None)
    except Exception as e:
        print(f"[CONFIG] 读取 STA 配置失败: {e}")
        ssid = ""
        password = ""
        # 创建空配置
        with open(WIFI_CONFIG_FILE, "w") as f:
            json.dump({"ssid": "", "password": ""}, f)
    g_sta_ssid = ssid
    g_sta_password = password
    print(f"[CONFIG] STA 配置: SSID='{ssid}'")
    return ssid, password

def save_wifi_config(ssid, password):
    """保存 WiFi 配置并更新全局变量"""
    try:
        data = {"ssid": ssid, "password": password}
        with open(WIFI_CONFIG_FILE, "w") as f:
            json.dump(data, f)
        global g_sta_ssid, g_sta_password
        g_sta_ssid = ssid
        g_sta_password = password
        print(f"[CONFIG] STA 配置已保存: SSID='{ssid}'")
        return True
    except Exception as e:
        print(f"[CONFIG] 保存系统配置失败: {e}")
        return False

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

def update_neighbor_broadcast_interval(new_interval):
    """更新广播间隔并保存到配置文件"""
    global g_neighbor_advertise_interval
    config = load_system_config()
    config["neighbor_broadcast_interval"] = new_interval
    save_system_config(config)
    g_neighbor_advertise_interval = new_interval


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


# =============================================================================
# 昵称表（MAC → 昵称）
# 文件：nicknames.json
# 结构：{"AA:BB:CC:DD:EE:FF": "device1", ...}
# =============================================================================

def load_nicknames():
    """读取昵称表"""
    try:
        with open(NICKNAMES_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

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
# 全局配置加载（将 system-config.json 同步到 g_* 变量）
# =============================================================================

def load_global_config():
    """
    从 system-config.json 读取配置并更新全局变量 g_*
    同时计算广播地址（基于 ap_ip）
    """
    global g_ap_ssid, g_ap_password, g_ap_ip, g_ap_subnet
    global g_udp_recv_port, g_udp_broadcast_port, g_ap_broadcast_addr
    global g_udp_poll_interval, g_led_pin, g_max_udp_messages, g_sta_timeout
    global g_device_nickname, g_neighbor_advertise_interval
    global g_route_advertise_interval

    config = load_system_config()
    g_ap_ssid = config["ap_ssid"]
    g_ap_password = config["ap_password"]
    g_ap_ip = config["ap_ip"]
    g_ap_subnet = config["ap_subnet"]
    g_udp_recv_port = config["udp_recv_port"]
    g_udp_broadcast_port = config["udp_broadcast_port"]
    g_udp_poll_interval = config.get("udp_poll_interval", 2000)
    g_led_pin = config.get("led_pin", 8)
    g_max_udp_messages = config.get("max_udp_messages", 5)
    g_sta_timeout = config.get("sta_timeout", 60)
    g_device_nickname = config.get("device_nickname", get_default_nickname())  # 若缺失则生成
    g_neighbor_advertise_interval = config.get("neighbor_advertise_interval", 120)
    g_route_advertise_interval = config.get("route_advertise_interval", 120)


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
    load_route_table()            # 加载路由表（如缺失则返回空字典）
    load_nicknames()              # 加载昵称表（如缺失则返回空字典）

    print("[CONFIG] 所有配置加载完成（缺失文件已自动创建）")