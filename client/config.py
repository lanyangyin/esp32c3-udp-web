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
    DEFAULT_NEIGHBOR_ADVERTISE_INTERVAL, DEFAULT_ROUTE_ADVERTISE_INTERVAL, DEFAULT_IR_BAUDRATE, DEFAULT_IR_TIMEOUT
)

# =============================================================================
# 文件路径常量
# =============================================================================
SYSTEM_CONFIG_FILE = "system-config.json" # AP / UDP / LED 等系统参数
WIFI_CONFIG_FILE = "wifi-config.json"          # STA 模式凭据
NICKNAMES_FILE = "nicknames.json"         # 昵称表（MAC → 昵称）
NEIGHBORS_FILE = "neighbors.json"         # 邻居表（MAC → IP）
ROUTE_TABLE_FILE = "route_table.json"     # 路由表（MAC → {ip, ttl}）

CONTROL_CONFIG_FILE = "control_config.json"
SERVO_CONFIG_FILE = "servo-config.json"
IR_DATA_FILE = "ir05t-data-config.json"
IR_CONFIG_FILE = "ir05t-config.json"

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

# 控制配置全局变量
g_commands = {}

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
# 7. 控制命令配置（control_config.json）
#    结构: {"commands": {"模块名": [{"cmd": "...", "desc": "..."}, ...]}}
# =============================================================================

def load_control_config():
    global g_commands
    try:
        with open(CONTROL_CONFIG_FILE, "r") as f:
            cfg = json.load(f)
    except (OSError, ValueError):
        # 创建默认命令配置（包含所有模块的帮助信息）
        cfg = {
            "commands": {
                "servo": [
                    {"cmd": "servo,list", "desc": "列出所有舵机名称和引脚"},
                    {"cmd": "servo,set_pin,<舵机名称>,<引脚>", "desc": "设置舵机引脚（需 reload 生效）"},
                    {"cmd": "servo,delete,<舵机名称>", "desc": "删除舵机（从配置移除并释放 PWM）"},
                    {"cmd": "servo,set_init_angle,<舵机名称>,<初始化角度>", "desc": "设置舵机初始化角度（需 reload 生效）"},
                    {"cmd": "servo,set,<舵机名称>,<角度>", "desc": "直接设置指定舵机角度"},
                    {"cmd": "servo,record,<舵机名称>,<动作组名称>,<角度1>,<角度2>,...", "desc": "录制动作组（角度列表）"},
                    {"cmd": "servo,play,<舵机名称>,<动作组名称>", "desc": "执行指定动作组（每个角度间隔0.7秒）"},
                    {"cmd": "servo,stop", "desc": "停止当前正在播放的舵机动作组"},
                    {"cmd": "servo,delete_group,<舵机名称>,<动作组名称>", "desc": "删除指定动作组"},
                    {"cmd": "servo,list_groups,<舵机名称>", "desc": "列出舵机的所有动作组"}
                ],
                "ir05t": [
                    {"cmd": "ir05t,learn", "desc": "通用学习红外信号（返回数据长度）"},
                    {"cmd": "ir05t,learn,save,<名称>", "desc": "学习并保存到数据文件"},
                    {"cmd": "ir05t,list", "desc": "列出所有已保存的名称"},
                    {"cmd": "ir05t,get,<名称>", "desc": "获取指定名称的十六进制数据"},
                    {"cmd": "ir05t,send,<名称>", "desc": "发射指定名称的红外信号"},
                    {"cmd": "ir05t,delete,<名称>", "desc": "删除指定名称的数据"},
                    {"cmd": "ir05t,learn_channel,<1~5>", "desc": "指定通道学习（1~5）"},
                    {"cmd": "ir05t,send_channel,<1~5>", "desc": "发射指定通道红外"},
                    {"cmd": "ir05t,send_raw,<hex数据>", "desc": "发射原始红外数据（十六进制字符串）"},
                    {"cmd": "ir05t,set_baud,<9600|4800|57600|115200>", "desc": "修改模块波特率"},
                    {"cmd": "ir05t,set_header,<0xA0~0xFE>", "desc": "修改帧头（0xA0~0xFE）"},
                    {"cmd": "ir05t,set_timeout,<毫秒>", "desc": "修改红外学习/读取超时时间（默认2000ms）"},
                    {"cmd": "ir05t,set_tx,<引脚>", "desc": "修改 IR05T TX 引脚（需 reload 生效）"},
                    {"cmd": "ir05t,set_rx,<引脚>", "desc": "修改 IR05T RX 引脚（需 reload 生效）"}
                ],
                "system": [
                    {"cmd": "help", "desc": "显示所有模块的帮助信息"},
                    {"cmd": "servo,help", "desc": "仅显示舵机模块的帮助信息"},
                    {"cmd": "ir05t,help", "desc": "仅显示 IR05T 模块的帮助信息"},
                    {"cmd": "status", "desc": "显示当前配置信息"},
                    {"cmd": "memory", "desc": "显示内存使用情况"},
                    {"cmd": "config,get", "desc": "获取当前所有配置（JSON格式）"},
                    {"cmd": "config,save", "desc": "保存当前配置到文件并重启"},
                    {"cmd": "config,reload", "desc": "重新加载配置文件（不重启）"},
                    {"cmd": "config,set_sta,<SSID>,<密码>", "desc": "修改 STA 目标 AP 的 SSID 和密码（需重启生效）"},
                    {"cmd": "config,reset", "desc": "删除配置文件并重启（恢复出厂设置）"},
                    {"cmd": "config,set_reply_port,<端口>", "desc": "修改 UDP 回复端口（需 reload 生效）"},
                    {"cmd": "config,set_broadcast_port,<端口>", "desc": "修改 UDP 监听端口（需 reload 生效）"},
                    {"cmd": "config,set_ap_ip,<IP>", "desc": "修改 AP IP 地址（需 reload 生效）"},
                    {"cmd": "config,set_ap_netmask,<掩码>", "desc": "修改 AP 子网掩码（需 reload 生效）"},
                    {"cmd": "config,set_ap_gateway,<网关>", "desc": "修改 AP 网关（需 reload 生效）"},
                    {"cmd": "config,set_ap_ssid,<新SSID>", "desc": "修改 AP 的 SSID（需重启生效）"},
                    {"cmd": "config,set_ap_password,<新密码>", "desc": "修改 AP 的 Wi-Fi 密码（需重启生效）"},
                    {"cmd": "route,list", "desc": "显示当前路由表"},
                    {"cmd": "neighbor,list", "desc": "显示当前邻居表"},
                    {"cmd": "nickname,set,<新昵称>", "desc": "修改设备昵称（立即生效）"},
                    {"cmd": "neighbor,set_interval,<秒数>", "desc": "修改邻居请求广播间隔（默认30秒）"},
                    {"cmd": "route,set_interval,<秒数>", "desc": "修改路由通告广播间隔（默认30秒）"},
                ]
            }
        }
        with open(CONTROL_CONFIG_FILE, "w") as f:
            json.dump(cfg, f)
        print("[CONFIG] 已创建默认控制配置")

    g_commands = cfg.get("commands", {})
    # 确保 system 命令组存在
    if "system" not in g_commands:
        g_commands["system"] = []
    return cfg



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
        with open(SERVO_CONFIG_FILE, "w") as f:
            json.dump({}, f)
        print("[CONFIG] 已创建空 servo-config.json")
        return {}

def save_servo_config(servo_config):
    """保存伺服配置"""
    try:
        with open(SERVO_CONFIG_FILE, "w") as f:
            json.dump(servo_config, f)
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
        with open(IR_CONFIG_FILE, "w") as f:
            json.dump({}, f)
        return {}

def save_ir_config(config_dict):
    """保存 IR 设备配置"""
    try:
        with open(IR_CONFIG_FILE, "w") as f:
            json.dump(config_dict, f)
        return True
    except Exception as e:
        print(f"[IR] 保存配置失败: {e}")
        return False

def get_ir_device(name):
    """获取指定设备的配置，不存在返回 None"""
    cfg = load_ir_config()
    return cfg.get(name)

def set_ir_device(name, tx_pin, rx_pin, baudrate=None, timeout=None):
    """添加或更新设备配置，若 baudrate/timeout 为 None 则使用默认值"""
    if baudrate is None:
        baudrate = DEFAULT_IR_BAUDRATE
    if timeout is None:
        timeout = DEFAULT_IR_TIMEOUT
    cfg = load_ir_config()
    if name not in cfg:
        cfg[name] = {"tx_pin": tx_pin, "rx_pin": rx_pin,
                     "baudrate": baudrate, "timeout": timeout,
                     "data": {}}
    else:
        cfg[name]["tx_pin"] = tx_pin
        cfg[name]["rx_pin"] = rx_pin
        cfg[name]["baudrate"] = baudrate
        cfg[name]["timeout"] = timeout
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
# 9. IR 数据（ir05t-data-config.json）
#    结构: {"名称": "十六进制数据字符串", ...}
# =============================================================================

def load_ir_data():
    try:
        with open(IR_DATA_FILE, "r") as f:
            return json.load(f)
    except (OSError, ValueError):
        with open(IR_DATA_FILE, "w") as f:
            json.dump({}, f)
        print("[CONFIG] 已创建空 ir05t-data-config.json")
        return {}

def save_ir_data(data_dict):
    try:
        with open(IR_DATA_FILE, "w") as f:
            json.dump(data_dict, f)
        return True
    except Exception as e:
        print(f"[IR数据] 保存失败: {e}")
        return False

def get_ir_data(name):
    data = load_ir_data()
    return data.get(name)

def set_ir_data(name, hex_data):
    data = load_ir_data()
    data[name] = hex_data
    return save_ir_data(data)

def delete_ir_data(name):
    data = load_ir_data()
    if name in data:
        del data[name]
        return save_ir_data(data)
    return False

def list_ir_names():
    data = load_ir_data()
    return list(data.keys())

def is_valid_name(name):
    """检查名称是否只包含字母、数字、下划线"""
    for c in name:
        if not ((c >= 'a' and c <= 'z') or (c >= 'A' and c <= 'Z') or (c >= '0' and c <= '9') or c == '_'):
            return False
    return True


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

    load_control_config()         # 加载控制命令
    load_servo_config()           # 创建空舵机配置（如缺失）
    load_ir_config()                # 创建空IR配置（如缺失）

    print("[CONFIG] 所有配置加载完成（缺失文件已自动创建）")