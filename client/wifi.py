# wifi.py - Wi-Fi 连接和 AP 管理模块
"""
提供 Wi-Fi 接入点（AP）启动、STA 模式连接、状态查询等功能。
所有配置从 config 模块动态获取，确保 system-config.json 中的值生效。
"""

import network
import time
import config   # 导入整个模块以动态获取配置


# =============================================================================
# AP 模式管理
# =============================================================================

def start_ap():
    """
    启动 SoftAP 模式，使用 config 模块中的全局配置（SSID、密码、IP、子网）。
    返回 AP 的 IP 地址。
    """
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid=config.g_ap_ssid, password=config.g_ap_password)
    ap.ifconfig((config.g_ap_ip, config.g_ap_subnet, config.g_ap_ip, config.g_ap_ip))
    print(f"[AP] AP 已启动，SSID: '{config.g_ap_ssid}'，IP: {config.g_ap_ip}")
    return config.g_ap_ip


# =============================================================================
# STA 模式连接
# =============================================================================

def connect_wifi(ssid, password, timeout=None):
    """
    连接指定的 Wi-Fi 网络（STA 模式）。
    参数：
        ssid      : 要连接的 Wi-Fi SSID
        password  : 密码
        timeout   : 超时秒数，默认使用 config.g_sta_timeout
    返回：
        True  : 连接成功
        False : 超时或失败
    """
    if timeout is None:
        timeout = config.g_sta_timeout
    wlan = network.WLAN(network.STA_IF)

    # ---- 彻底复位接口 ----
    wlan.active(False)
    time.sleep(1)          # 增加延时确保硬件释放
    wlan.active(True)
    time.sleep(1)

    # 如果已连接且是同一个 SSID，直接返回
    if wlan.isconnected():
        current_ssid = wlan.config('essid')
        if isinstance(current_ssid, bytes):
            current_ssid = current_ssid.decode()
        if current_ssid == ssid:
            print("[WiFi] 已连接到指定 SSID，IP:", wlan.ifconfig()[0])
            return True
        else:
            print("[WiFi] 连接到其他网络，断开...")
            wlan.disconnect()
            time.sleep(1)

    # ---- 带重试的连接 ----
    for attempt in range(3):
        try:
            print(f"[WiFi] 尝试连接 SSID='{ssid}' (第{attempt+1}次)...")
            wlan.connect(ssid, password)
            break
        except OSError as e:
            print(f"[WiFi] 连接异常: {e}")
            if attempt == 2:
                return False
            # 复位并等待
            wlan.active(False)
            time.sleep(1)
            wlan.active(True)
            time.sleep(1)

    # ---- 等待连接完成 ----
    start = time.time()
    while not wlan.isconnected():
        if time.time() - start > timeout:
            print("[WiFi] 连接超时")
            return False
        time.sleep(0.1)

    ip = wlan.ifconfig()[0]
    print(f"[WiFi] 连接成功，IP: {ip}")
    print(f"[WEB] http://{ip}")
    return True


# =============================================================================
# STA 状态查询
# =============================================================================

def get_sta_prefix():
    """
    获取 STA 接口的网段前缀（例如 "192.168.8"）。
    若 STA 未连接或 IP 无效，返回 None。
    """
    sta = network.WLAN(network.STA_IF)
    if sta.active() and sta.isconnected():
        ip = sta.ifconfig()[0]
        if ip and ip != '0.0.0.0':
            return '.'.join(ip.split('.')[:-1])
    return None


def get_sta_status_text():
    """
    返回 STA 状态的可读文本（如 "已连接 MyWiFi (192.168.1.100)" 或 "未连接"）。
    """
    sta = network.WLAN(network.STA_IF)
    if sta.isconnected():
        ssid = sta.config('essid')
        if isinstance(ssid, bytes):
            ssid = ssid.decode()
        ip = sta.ifconfig()[0]
        return f"已连接 {ssid} ({ip})"
    else:
        return "未连接"