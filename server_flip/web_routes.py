# web_routes.py - HTTP 路由（页面 + API）
"""
提供所有 Web 页面和 API 接口。
配置通过 config 模块动态获取，确保运行中对 system-config.json 的修改立即生效。
"""

# =============================================================================
# 导入所需模块
# =============================================================================
import json
import time
import _thread
import machine
import network
import config                     # 通过模块引用访问配置，确保动态更新
import util
from util import mac_to_str, gc_wrapper
import wifi
import udp
import neighbor
import route
from constants import MIN_PORT, MAX_PORT


def get_request_param(request, key, default=""):
    if request.method == "POST":
        # 尝试 JSON
        if request.headers.get("Content-Type", "").startswith("application/json"):
            try:
                data = request.json
                if data and key in data:
                    return data.get(key, default)
            except:
                pass  # JSON 解析失败
        # 尝试 form
        val = request.form.get(key)
        if val is not None:
            return val
    # GET 或 fallback
    args = request.args if request.args is not None else {}
    return args.get(key, default)

# =============================================================================
# 路由注册函数
# =============================================================================

def setup_routes(app):
    """
    向 EasyWeb 应用注册所有路由（页面 + API）。
    此函数由 main.py 调用。
    """

    # ========================================================================
    # 页面路由（HTML 页面）
    # ========================================================================

    @app.route("/")
    @gc_wrapper
    def index(request):
        """主页：显示 STA 连接状态"""
        print("[WEB] 访问根路径 /")
        try:
            status = wifi.get_sta_status_text()
            with open('index.html', 'r') as f:
                html = f.read()
            html = html.replace('{{STATUS}}', status)
            return html
        except Exception as e:
            import sys
            print("[WEB] 根页面错误:")
            sys.print_exception(e)
            return f"<h2>服务器内部错误: {repr(e)}</h2>", 500, {'Content-Type': 'text/plain; charset=utf-8'}

    @app.route("/udp_broadcast")
    @gc_wrapper
    def udp_broadcast_page(request):
        """UDP 广播控制页面"""
        try:
            with open('udp_broadcast.html', 'r') as f:
                return f.read()
        except Exception:
            return "UDP Broadcast page not found", 404, {'Content-Type': 'text/plain; charset=utf-8'}
    @app.route("/udp_unicast")
    @gc_wrapper
    def udp_unicast_page(request):
        """UDP 单播控制页面"""
        try:
            with open('udp_unicast.html', 'r') as f:
                return f.read()
        except Exception:
            return "UDP Unicast page not found", 404, {'Content-Type': 'text/plain; charset=utf-8'}
    @app.route("/neighbor")
    @gc_wrapper
    def neighbor_page(request):
        """邻居表管理页面"""
        try:
            with open('neighbor.html', 'r') as f:
                return f.read()
        except Exception:
            return "Neighbor page not found", 404, {'Content-Type': 'text/plain; charset=utf-8'}
    @app.route("/route")
    @gc_wrapper
    def route_page(request):
        """路由表管理页面"""
        try:
            with open('route.html', 'r') as f:
                return f.read()
        except Exception:
            return "Route page not found", 404, {'Content-Type': 'text/plain; charset=utf-8'}
    @app.route("/settings/ap")
    @gc_wrapper
    def settings_ap(request):
        """AP 配置页面"""
        try:
            with open('settings/ap.html', 'r') as f:
                return f.read()
        except Exception:
            return "AP settings page not found", 404, {'Content-Type': 'text/plain; charset=utf-8'}
    @app.route("/settings/sta")
    @gc_wrapper
    def settings_sta(request):
        """STA 配置页面"""
        try:
            with open('settings/sta.html', 'r') as f:
                return f.read()
        except Exception:
            return "STA settings page not found", 404, {'Content-Type': 'text/plain; charset=utf-8'}
    @app.route("/settings/udp")
    @gc_wrapper
    def settings_udp(request):
        """UDP 配置页面"""
        try:
            with open('settings/udp.html', 'r') as f:
                return f.read()
        except Exception:
            return "UDP settings page not found", 404, {'Content-Type': 'text/plain; charset=utf-8'}
    @app.route("/settings/system")
    @gc_wrapper
    def settings_system(request):
        """系统配置页面"""
        try:
            with open('settings/system.html', 'r') as f:
                return f.read()
        except Exception:
            return "System settings page not found", 404, {'Content-Type': 'text/plain; charset=utf-8'}
    # ========================================================================
    # 静态文件路由
    # ========================================================================

    @app.route("/script.js")
    @gc_wrapper
    def script_js(request):
        try:
            with open('script.js', 'r') as f:
                return f.read(), 200, {'Content-Type': 'application/javascript; charset=utf-8'}
        except Exception:
            return "Not found", 404, {'Content-Type': 'text/plain; charset=utf-8'}
    @app.route("/style.css")
    @gc_wrapper
    def style_css(request):
        try:
            with open('style.css', 'r') as f:
                return f.read(), 200, {'Content-Type': 'text/css; charset=utf-8'}
        except Exception:
            return "Not found", 404, {'Content-Type': 'text/plain; charset=utf-8'}
    # ========================================================================
    # 兼容性路由（旧版 /set）
    # ========================================================================

    @app.route("/set")
    @gc_wrapper
    def set_wifi(request):
        """旧版 WiFi 配置接口（兼容保留）"""
        ssid = get_request_param(request, "ssid")
        password = get_request_param(request, "password")
        if not ssid:
            return "错误：缺少 ssid 参数", 400, {'Content-Type': 'text/plain; charset=utf-8'}
        # 若参数为列表（兼容旧版）则取第一个
        if isinstance(ssid, list):
            ssid = ssid[0] if ssid else ""
        if isinstance(password, list):
            password = password[0] if password else ""
        if isinstance(ssid, bytes):
            ssid = ssid.decode()
        if isinstance(password, bytes):
            password = password.decode()
        if ssid:
            config.save_wifi_config(ssid, password)
            return "Wi-Fi 配置已保存，请重启设备（按 RST 键）。", 200, {'Content-Type': 'text/plain; charset=utf-8'}
        else:
            return "错误：ssid 不能为空", 400, {'Content-Type': 'text/plain; charset=utf-8'}
    # ========================================================================
    # API：系统配置修改
    # ========================================================================

    @app.route("/api/set_ap_ip")
    @gc_wrapper
    def set_ap_ip(request):
        """修改 AP IP 地址"""
        new_ip = get_request_param(request, "ip")
        if not new_ip:
            return "缺少 ip 参数", 400, {'Content-Type': 'text/plain; charset=utf-8'}
        parts = new_ip.split('.')
        if len(parts) != 4:
            return "IP 格式无效", 400, {'Content-Type': 'text/plain; charset=utf-8'}
        for p in parts:
            if not p.isdigit() or int(p) < 0 or int(p) > 255:
                return "IP 格式无效", 400, {'Content-Type': 'text/plain; charset=utf-8'}
        cfg = config.load_system_config()
        cfg["ap_ip"] = new_ip
        config.save_system_config(cfg)
        config.load_global_config()
        return f"AP IP 已更改为 {new_ip}，请重启设备生效。", 200, {'Content-Type': 'text/plain; charset=utf-8'}

    @app.route("/api/set_ap_ssid_password")
    @gc_wrapper
    def set_ap_ssid_password(request):
        """修改 AP SSID 和密码"""
        ssid = get_request_param(request, "ssid")
        password = get_request_param(request, "password")
        if not ssid:
            return "缺少 ssid 参数", 400, {'Content-Type': 'text/plain; charset=utf-8'}
        cfg = config.load_system_config()
        cfg["ap_ssid"] = ssid
        cfg["ap_password"] = password
        config.save_system_config(cfg)
        return f"AP SSID 已改为 '{ssid}'，密码已更新，请重启设备生效。", 200, {'Content-Type': 'text/plain; charset=utf-8'}

    @app.route("/api/set_udp_recv_port")
    @gc_wrapper
    def set_udp_recv_port(request):
        """修改 UDP 接收端口"""
        port_str = get_request_param(request, "port")
        if not port_str:
            return "缺少 port 参数", 400, {'Content-Type': 'text/plain; charset=utf-8'}
        try:
            port = int(port_str)
            if port < MIN_PORT or port > MAX_PORT:
                raise ValueError
        except:
            return "端口号必须是 1-65535 的整数", 400, {'Content-Type': 'text/plain; charset=utf-8'}
        cfg = config.load_system_config()
        cfg["udp_recv_port"] = port
        config.save_system_config(cfg)
        return f"UDP 接收端口已改为 {port}，请重启设备生效。", 200, {'Content-Type': 'text/plain; charset=utf-8'}

    @app.route("/api/set_udp_broadcast_port")
    @gc_wrapper
    def set_udp_broadcast_port(request):
        """修改 UDP 广播/单播目标端口"""
        port_str = get_request_param(request, "port")
        if not port_str:
            return "缺少 port 参数", 400, {'Content-Type': 'text/plain; charset=utf-8'}
        try:
            port = int(port_str)
            if port < MIN_PORT or port > MAX_PORT:
                raise ValueError
        except:
            return "端口号必须是 1-65535 的整数", 400, {'Content-Type': 'text/plain; charset=utf-8'}
        cfg = config.load_system_config()
        cfg["udp_broadcast_port"] = port
        config.save_system_config(cfg)
        return f"UDP 广播/单播目标端口已改为 {port}，请重启设备生效。", 200, {'Content-Type': 'text/plain; charset=utf-8'}

    @app.route("/api/reset_ap_config")
    @gc_wrapper
    def reset_ap_config(request):
        """重置 AP 配置为默认值"""
        config.reset_system_config()
        config.load_global_config()
        return "AP 配置已重置为默认值，请重启设备生效。", 200, {'Content-Type': 'text/plain; charset=utf-8'}
    @app.route("/api/set_led_pin")
    @gc_wrapper
    def set_led_pin(request):
        """修改 LED 引脚"""
        pin_str = get_request_param(request, "pin")
        if not pin_str:
            return "缺少 pin 参数", 400, {'Content-Type': 'text/plain; charset=utf-8'}
        try:
            pin = int(pin_str)
            if pin < 0 or pin > 21 or pin in range(12, 18):
                return "引脚无效或为 Flash 专用引脚", 400, {'Content-Type': 'text/plain; charset=utf-8'}
        except:
            return "引脚必须是整数", 400, {'Content-Type': 'text/plain; charset=utf-8'}
        cfg = config.load_system_config()
        cfg["led_pin"] = pin
        config.save_system_config(cfg)
        # 更新全局变量（供其他模块使用）
        config.g_led_pin = pin
        return f"LED 引脚已更改为 GPIO{pin}，请重启设备生效。", 200, {'Content-Type': 'text/plain; charset=utf-8'}

    @app.route("/api/get_led_pin")
    @gc_wrapper
    def get_led_pin(request):
        """获取当前 LED 引脚"""
        return json.dumps({"pin": config.g_led_pin}), 200, {'Content-Type': 'application/json; charset=utf-8'}

    @app.route("/api/get_self_mac")
    @gc_wrapper
    def get_self_mac(request):
        """获取本机 MAC 地址"""
        mac_str = util.get_self_mac()
        return json.dumps({"mac": mac_str}), 200, {'Content-Type': 'application/json; charset=utf-8'}

    @app.route("/api/get_led_status")
    @gc_wrapper
    def get_led_status(request):
        """获取 LED 状态（根据 STA 连接状态）"""
        sta = network.WLAN(network.STA_IF)
        connected = sta.isconnected()
        status = "ON" if connected else "OFF"
        return json.dumps({"status": status}), 200, {'Content-Type': 'application/json; charset=utf-8'}

    @app.route("/api/get_max_udp_messages")
    @gc_wrapper
    def get_max_udp_messages(request):
        """获取 UDP 消息最大保留条数"""
        return json.dumps({"value": config.g_max_udp_messages}), 200, {'Content-Type': 'application/json; charset=utf-8'}

    @app.route("/api/set_max_udp_messages")
    @gc_wrapper
    def set_max_udp_messages(request):
        """设置 UDP 消息最大保留条数"""
        val_str = get_request_param(request, "value")
        if not val_str:
            return "缺少 value 参数", 400, {'Content-Type': 'text/plain; charset=utf-8'}
        try:
            val = int(val_str)
            if val < 1:
                return "value 必须 >= 1", 400, {'Content-Type': 'text/plain; charset=utf-8'}
        except:
            return "value 必须是整数", 400, {'Content-Type': 'text/plain; charset=utf-8'}
        cfg = config.load_system_config()
        cfg["max_udp_messages"] = val
        config.save_system_config(cfg)
        config.g_max_udp_messages = val
        # 立即截断消息列表
        while len(udp.udp_messages) > val:
            udp.udp_messages.pop(0)
        return f"UDP 最大消息数已设为 {val}，已生效", 200, {'Content-Type': 'text/plain; charset=utf-8'}

    @app.route("/api/get_sta_timeout")
    @gc_wrapper
    def get_sta_timeout(request):
        """获取 STA 连接超时时间"""
        return json.dumps({"value": config.g_sta_timeout}), 200, {'Content-Type': 'application/json; charset=utf-8'}

    @app.route("/api/set_sta_timeout")
    @gc_wrapper
    def set_sta_timeout(request):
        """设置 STA 连接超时时间"""
        val_str = get_request_param(request, "value")
        if not val_str:
            return "缺少 value 参数", 400, {'Content-Type': 'text/plain; charset=utf-8'}
        try:
            val = int(val_str)
            if val < 5:
                return "超时时间必须 >= 5 秒", 400, {'Content-Type': 'text/plain; charset=utf-8'}
        except:
            return "value 必须是整数", 400, {'Content-Type': 'text/plain; charset=utf-8'}
        cfg = config.load_system_config()
        cfg["sta_timeout"] = val
        config.save_system_config(cfg)
        config.g_sta_timeout = val
        return f"STA 连接超时已设为 {val} 秒，请重启设备生效。", 200, {'Content-Type': 'text/plain; charset=utf-8'}

    @app.route("/api/set_ap_net_segment")
    @gc_wrapper
    def set_ap_net_segment(request):
        """修改 AP 网段（IP 倒数第二段）"""
        segment_str = get_request_param(request, "segment")
        if not segment_str:
            return "缺少 segment 参数", 400, {'Content-Type': 'text/plain; charset=utf-8'}
        try:
            seg = int(segment_str)
            if seg < 0 or seg > 255:
                raise ValueError
        except:
            return "segment 必须是 0-255 的整数", 400, {'Content-Type': 'text/plain; charset=utf-8'}
        ip_parts = config.g_ap_ip.split('.')
        ip_parts[2] = str(seg)
        new_ip = '.'.join(ip_parts)
        cfg = config.load_system_config()
        cfg["ap_ip"] = new_ip
        config.save_system_config(cfg)
        config.load_global_config()
        return f"AP 网段已改为 {seg}，新 IP 将为 {new_ip}，请重启设备生效。", 200, {'Content-Type': 'text/plain; charset=utf-8'}

    @app.route("/api/set_udp_poll_interval")
    @gc_wrapper
    def set_udp_poll_interval(request):
        """设置 UDP 轮询间隔（前端使用）"""
        interval_str = get_request_param(request, "interval")
        if not interval_str:
            return "缺少 interval 参数", 400, {'Content-Type': 'text/plain; charset=utf-8'}
        try:
            interval = int(interval_str)
            if interval < 500:
                return "间隔不能小于 500 毫秒", 400, {'Content-Type': 'text/plain; charset=utf-8'}
        except:
            return "interval 必须是正整数", 400, {'Content-Type': 'text/plain; charset=utf-8'}
        cfg = config.load_system_config()
        cfg["udp_poll_interval"] = interval
        config.save_system_config(cfg)
        config.g_udp_poll_interval = interval
        return f"轮询间隔已设为 {interval} 毫秒，请刷新页面以应用新间隔", 200, {'Content-Type': 'text/plain; charset=utf-8'}

    # ========================================================================
    # API：状态查询
    # ========================================================================

    @app.route("/api/get_ap_status")
    @gc_wrapper
    def get_ap_status(request):
        """获取 AP 状态"""
        ap = network.WLAN(network.AP_IF)
        active = ap.active()
        return json.dumps({
            "active": active,
            "ssid": config.g_ap_ssid,
            "ip": config.g_ap_ip,
            "subnet": config.g_ap_subnet
        }), 200, {'Content-Type': 'application/json; charset=utf-8'}

    @app.route("/api/get_sta_status")
    @gc_wrapper
    def get_sta_status(request):
        """获取 STA 状态"""
        sta = network.WLAN(network.STA_IF)
        connected = sta.isconnected()
        ssid = ""
        ip = ""
        if connected:
            ssid = sta.config('essid')
            if isinstance(ssid, bytes):
                ssid = ssid.decode()
            ip = sta.ifconfig()[0]
        return json.dumps({
            "connected": connected,
            "ssid": ssid,
            "ip": ip
        }), 200, {'Content-Type': 'application/json; charset=utf-8'}

    @app.route("/api/get_ap_ssid_password")
    @gc_wrapper
    def get_ap_ssid_password(request):
        """获取 AP SSID 和密码"""
        return json.dumps({
            "ssid": config.g_ap_ssid,
            "password": config.g_ap_password
        }), 200, {'Content-Type': 'application/json; charset=utf-8'}

    @app.route("/api/get_sta_ssid_password")
    @gc_wrapper
    def get_sta_ssid_password(request):
        """获取 STA SSID 和密码"""
        cfg = config.load_wifi_config()
        return json.dumps({"ssid": cfg[0], "password": cfg[1]}), 200, {'Content-Type': 'application/json; charset=utf-8'}

    @app.route("/api/set_sta_ssid_password")
    @gc_wrapper
    def set_sta_ssid_password(request):
        """设置 STA SSID 和密码"""
        ssid = get_request_param(request, "ssid")
        password = get_request_param(request, "password")
        if not ssid:
            return "缺少 ssid 参数", 400, {'Content-Type': 'text/plain; charset=utf-8'}
        config.save_wifi_config(ssid, password)
        return f"STA SSID/密码已更新，请重启设备生效。", 200, {'Content-Type': 'text/plain; charset=utf-8'}

    @app.route("/api/get_udp_recv_port")
    @gc_wrapper
    def get_udp_recv_port(request):
        """获取 UDP 接收端口"""
        return json.dumps({"value": config.g_udp_recv_port}), 200, {'Content-Type': 'application/json; charset=utf-8'}

    @app.route("/api/get_udp_broadcast_port")
    @gc_wrapper
    def get_udp_broadcast_port(request):
        """获取 UDP 广播/单播目标端口"""
        return json.dumps({"value": config.g_udp_broadcast_port}), 200, {'Content-Type': 'application/json; charset=utf-8'}

    @app.route("/api/get_udp_poll_interval")
    @gc_wrapper
    def get_udp_poll_interval(request):
        """获取 UDP 轮询间隔"""
        return json.dumps({"interval": config.g_udp_poll_interval}), 200, {'Content-Type': 'application/json; charset=utf-8'}

    @app.route("/api/get_nicknames")
    @gc_wrapper
    def get_nicknames(request):
        """获取所有昵称"""
        return json.dumps(neighbor.load_nicknames()), 200, {'Content-Type': 'application/json; charset=utf-8'}

    @app.route("/api/get_macs")
    @gc_wrapper
    def get_macs(request):
        """获取当前连接设备的 MAC 列表"""
        ap = network.WLAN(network.AP_IF)
        stations = ap.status('stations')
        nicknames = neighbor.load_nicknames()
        if not stations:
            return "当前没有设备连接", 200, {'Content-Type': 'text/plain; charset=utf-8'}
        lines = []
        for mac in stations:
            mac_str = mac_to_str(mac)
            nick = nicknames.get(mac_str, '')
            lines.append(f"{mac_str}  昵称:{nick if nick else '未设置'}")
        return "\n".join(lines), 200

    @app.route("/api/list_auth")
    @gc_wrapper
    def list_auth(request):
        """获取已认证设备列表"""
        devices = neighbor.get_auth_devices()
        if not devices:
            return "暂无已注册设备", 200, {'Content-Type': 'text/plain; charset=utf-8'}
        lines = []
        for dev in devices:
            lines.append(f"{dev['mac']}  IP:{dev['ip']}  昵称:{dev['nickname'] or '未设置'}")
        return "\n".join(lines), 200

    @app.route("/api/memory")
    @gc_wrapper
    def get_memory(request):
        """获取内存使用情况"""
        import gc
        free = gc.mem_free()
        alloc = gc.mem_alloc()
        total = free + alloc
        data = {
            "total": total,
            "used": alloc,
            "free": free,
            "percent_used": round(alloc / total * 100, 1)
        }
        return json.dumps(data), 200, {'Content-Type': 'application/json; charset=utf-8'}

    # ========================================================================
    # API：邻居表操作
    # ========================================================================

    @app.route("/api/clear_neighbors")
    @gc_wrapper
    def clear_neighbors(request):
        """清空邻居表"""
        nb = neighbor.load_neighbors()
        if not nb:
            return "邻居表已为空", 200, {'Content-Type': 'text/plain; charset=utf-8'}
        neighbor.save_neighbors({})
        return "邻居表已清空", 200, {'Content-Type': 'text/plain; charset=utf-8'}
    @app.route("/api/clear_unauth")
    @gc_wrapper
    def clear_unauth_api(request):
        """清除未认证设备"""
        count = neighbor.clear_unauth()
        return f"已清除 {count} 个未注册设备", 200, {'Content-Type': 'text/plain; charset=utf-8'}

    @app.route("/api/delete_device")
    @gc_wrapper
    def delete_device_api(request):
        """删除设备（从邻居表和昵称表）"""
        mac = get_request_param(request, "mac")
        if not mac:
            return "缺少 mac 参数", 400, {'Content-Type': 'text/plain; charset=utf-8'}
        mac = mac_to_str(mac)
        if neighbor.delete_device(mac):
            return f"设备 {mac} 已删除", 200, {'Content-Type': 'text/plain; charset=utf-8'}
        else:
            return "设备不存在", 404, {'Content-Type': 'text/plain; charset=utf-8'}
    @app.route("/api/set_nickname")
    @gc_wrapper
    def set_nickname_api(request):
        """设置设备昵称"""
        mac = get_request_param(request, "mac")
        nickname = get_request_param(request, "nickname")
        if not mac or not nickname:
            return "缺少 mac 或 nickname 参数", 400, {'Content-Type': 'text/plain; charset=utf-8'}
        mac = mac_to_str(mac)
        if neighbor.set_nickname(mac, nickname):
            return f"昵称设置成功: {mac} -> {nickname}", 200, {'Content-Type': 'text/plain; charset=utf-8'}
        else:
            return "设备未认证或不存在", 404, {'Content-Type': 'text/plain; charset=utf-8'}
    # ========================================================================
    # API：路由表操作
    # ========================================================================

    @app.route("/api/route_table")
    @gc_wrapper
    def get_route_table(request):
        """获取路由表"""
        return json.dumps(route.load_route_table()), 200, {'Content-Type': 'application/json; charset=utf-8'}

    @app.route("/api/route_table_with_nick")
    @gc_wrapper
    def route_table_with_nick(request):
        """获取路由表（含昵称）"""
        table = route.load_route_table()
        nicknames = neighbor.load_nicknames()
        result = {}
        for mac, entry in table.items():
            result[mac] = {
                "ip": entry["ip"],
                "ttl": entry["ttl"],
                "nickname": nicknames.get(mac, "")
            }
        return json.dumps(result), 200, {'Content-Type': 'application/json; charset=utf-8'}

    @app.route("/api/route_delete")
    @gc_wrapper
    def route_delete_api(request):
        """删除路由条目"""
        mac = get_request_param(request, "mac")
        if not mac:
            return "缺少 mac 参数", 400, {'Content-Type': 'text/plain; charset=utf-8'}
        mac = mac_to_str(mac)
        if route.route_delete(mac):
            return f"路由 {mac} 已删除", 200, {'Content-Type': 'text/plain; charset=utf-8'}
        else:
            return "路由不存在", 404, {'Content-Type': 'text/plain; charset=utf-8'}
    @app.route("/api/route_clear")
    @gc_wrapper
    def route_clear_api(request):
        """清空路由表"""
        route.save_route_table({})
        return "路由表已清空", 200, {'Content-Type': 'text/plain; charset=utf-8'}
    # ========================================================================
    # API：UDP 操作
    # ========================================================================

    @app.route("/api/udp_messages")
    @gc_wrapper
    def get_udp_messages(request):
        """获取收到的 UDP 消息列表"""
        msgs = udp.get_udp_messages()
        return json.dumps(msgs), 200, {'Content-Type': 'application/json; charset=utf-8'}

    @app.route("/api/clear_udp_messages")
    @gc_wrapper
    def clear_udp_messages(request):
        """清空 UDP 消息列表"""
        udp.clear_udp_messages()
        return "UDP 消息已清空", 200, {'Content-Type': 'text/plain; charset=utf-8'}
    # ========================================================================
    # API：UDP 单播
    # ========================================================================

    @app.route("/api/udp_send_ip", methods=["GET", "POST"])
    @gc_wrapper
    def udp_send_ip(request):
        target_ip = get_request_param(request, "ip")
        content = get_request_param(request, "content")
        if not target_ip or not content:
            return "缺少 ip 或 content 参数", 400, {'Content-Type': 'text/plain; charset=utf-8'}
        success = udp.udp_send_to_ip(target_ip, content)
        return "发送成功" if success else "发送失败", 200 if success else 500

    @app.route("/api/udp_send_ap", methods=["GET", "POST"])
    @gc_wrapper
    def udp_send_ap(request):
        ip_tail = get_request_param(request, "ip_tail")
        content = get_request_param(request, "content")
        if not ip_tail or not content:
            return "缺少 ip_tail 或 content 参数", 400, {'Content-Type': 'text/plain; charset=utf-8'}
        prefix = '.'.join(config.g_ap_ip.split('.')[:-1])
        target_ip = f"{prefix}.{ip_tail}"
        success = udp.udp_send_to_ip(target_ip, content)
        return "发送成功" if success else "发送失败", 200 if success else 500

    @app.route("/api/udp_send_sta", methods=["GET", "POST"])
    @gc_wrapper
    def udp_send_sta(request):
        ip_tail = get_request_param(request, "ip_tail")
        content = get_request_param(request, "content")
        if not ip_tail or not content:
            return "缺少 ip_tail 或 content 参数", 400, {'Content-Type': 'text/plain; charset=utf-8'}
        prefix = wifi.get_sta_prefix()
        if prefix is None:
            return "STA 未连接，无法获取网段", 400, {'Content-Type': 'text/plain; charset=utf-8'}
        target_ip = f"{prefix}.{ip_tail}"
        success = udp.udp_send_to_ip(target_ip, content)
        return "发送成功" if success else "发送失败", 200 if success else 500

    @app.route("/api/send_to_nick", methods=["GET", "POST"])
    @gc_wrapper
    def send_to_nick(request):
        nickname = get_request_param(request, "nickname")
        content = get_request_param(request, "content")
        if not nickname or not content:
            return "缺少 nickname 或 content 参数", 400, {'Content-Type': 'text/plain; charset=utf-8'}
        nicknames = neighbor.load_nicknames()
        mac = None
        for m, n in nicknames.items():
            if n == nickname:
                mac = m
                break
        if not mac:
            return "昵称不存在", 404, {'Content-Type': 'text/plain; charset=utf-8'}
        neighbors = neighbor.load_neighbors()
        entry = neighbors.get(mac)
        if not entry:
            return "设备未在邻居表注册或IP未知", 404, {'Content-Type': 'text/plain; charset=utf-8'}
        target_ip = entry.get("ip")
        if not target_ip:
            return "设备未在邻居表注册或IP未知", 404, {'Content-Type': 'text/plain; charset=utf-8'}
        success = udp.udp_send_to_ip(target_ip, content)
        if success:
            return f"消息已发送给昵称 '{nickname}'", 200, {'Content-Type': 'text/plain; charset=utf-8'}
        else:
            return "发送失败", 500, {'Content-Type': 'text/plain; charset=utf-8'}
    # ========================================================================
    # API：UDP 路由单播
    # ========================================================================

    @app.route("/api/send_route_message", methods=["GET", "POST"])
    @gc_wrapper
    def send_route_message(request):
        dst_mac = get_request_param(request, "dst_mac")
        cmd_msg = get_request_param(request, "cmd_msg")
        if not dst_mac or not cmd_msg:
            return "缺少 dst_mac 或 cmd_msg 参数", 400, {'Content-Type': 'text/plain; charset=utf-8'}
        dst_mac = mac_to_str(dst_mac)
        ap_if = network.WLAN(network.AP_IF)
        src_mac = mac_to_str(ap_if.config('mac'))
        if dst_mac == src_mac:
            return "不能发送给自己", 400, {'Content-Type': 'text/plain; charset=utf-8'}
        success = udp.send_route_message(dst_mac, cmd_msg)
        if success:
            return "路由消息已发送", 200, {'Content-Type': 'text/plain; charset=utf-8'}
        else:
            return "发送失败，目标不可达", 404, {'Content-Type': 'text/plain; charset=utf-8'}
    # ========================================================================
    # API：UDP 广播
    # ========================================================================

    @app.route("/api/udp_broadcast", methods=["GET", "POST"])
    @gc_wrapper
    def udp_broadcast(request):
        content = get_request_param(request, "content")
        if not content:
            return "缺少 content 参数", 400, {'Content-Type': 'text/plain; charset=utf-8'}
        success = udp.send_broadcast_once(content)
        return "发送成功" if success else "发送失败", 200 if success else 500

    @app.route("/api/udp_broadcast_sta", methods=["GET", "POST"])
    @gc_wrapper
    def udp_broadcast_sta(request):
        content = get_request_param(request, "content")
        if not content:
            return "缺少 content 参数", 400, {'Content-Type': 'text/plain; charset=utf-8'}
        prefix = wifi.get_sta_prefix()
        if prefix is None:
            return "STA 未连接，无法获取网段", 400, {'Content-Type': 'text/plain; charset=utf-8'}
        success = udp.send_sta_broadcast_once(content)
        return "发送成功" if success else "发送失败", 200 if success else 500

    @app.route("/api/udp_broadcast_apsta", methods=["GET", "POST"])
    @gc_wrapper
    def udp_broadcast_apsta(request):
        content = get_request_param(request, "content")
        if not content:
            return "缺少 content 参数", 400, {'Content-Type': 'text/plain; charset=utf-8'}
        success = udp.send_both_broadcast_once(content)
        return "发送成功" if success else "发送失败", 200 if success else 500

    # ========================================================================
    # API：UDP 邻居表操作
    # ========================================================================

    @app.route("/api/auth_request")
    @gc_wrapper
    def auth_request(request):
        """在 AP 网段发送邻居注册请求"""
        udp.send_neighbor_register_request("AP")
        return "AP 邻居表注册请求已发送", 200, {'Content-Type': 'text/plain; charset=utf-8'}
    @app.route("/api/auth_request_sta")
    @gc_wrapper
    def auth_request_sta(request):
        """在 STA 网段发送邻居注册请求"""
        prefix = wifi.get_sta_prefix()
        if prefix is None:
            return "STA 未连接，无法获取网段", 400, {'Content-Type': 'text/plain; charset=utf-8'}
        udp.send_neighbor_register_request("STA")
        return "STA 邻居表注册请求已发送", 200, {'Content-Type': 'text/plain; charset=utf-8'}
    @app.route("/api/auth_request_apsta")
    @gc_wrapper
    def auth_request_apsta(request):
        """在 AP 和 STA 双网段发送邻居注册请求"""
        neighbor.ttl_decrement_neighbors()
        udp.send_neighbor_register_request("STA")
        udp.send_neighbor_register_request("AP")
        return "AP+STA 邻居表注册请求已发送", 200, {'Content-Type': 'text/plain; charset=utf-8'}
    @app.route("/api/neighbor_sta_update_request")
    @gc_wrapper
    def neighbor_sta_update_request(request):
        """在 STA 网段发送邻居表更新请求"""
        sta = network.WLAN(network.STA_IF)
        if not sta.isconnected():
            return "STA 未连接", 400, {'Content-Type': 'text/plain; charset=utf-8'}
        udp.send_neighbor_update_request("STA")
        return "邻居表 STA 更新请求已发送", 200, {'Content-Type': 'text/plain; charset=utf-8'}
    @app.route("/api/neighbor_ap_update_request")
    @gc_wrapper
    def neighbor_ap_update_request(request):
        """在 STA 网段发送邻居表更新请求"""
        udp.send_neighbor_update_request("AP")
        return "邻居表 AP 更新请求已发送", 200, {'Content-Type': 'text/plain; charset=utf-8'}
    # ========================================================================
    # API：UDP 路由表操作
    # ========================================================================

    @app.route("/api/route_ap_register_request")
    @gc_wrapper
    def route_ap_register_request(request):
        """在 AP 网段发送路由注册请求"""
        route.route_ttl_decrement()
        udp.send_route_register_request()  # 已在 udp.py 中实现
        return "AP 路由表注册请求已发送", 200, {'Content-Type': 'text/plain; charset=utf-8'}
    @app.route("/api/route_sta_update_request")
    @gc_wrapper
    def route_sta_update_request(request):
        """在 STA 网段发送路由更新请求"""
        sta = network.WLAN(network.STA_IF)
        if not sta.isconnected():
            return "STA 未连接", 400, {'Content-Type': 'text/plain; charset=utf-8'}
        udp.send_route_update_request()
        return "STA 路由表更新请求已发送", 200, {'Content-Type': 'text/plain; charset=utf-8'}
    @app.route("/api/route_sta_learn_request")
    @gc_wrapper
    def route_sta_learn_request(request):
        """在 STA 网段发送路由学习请求"""
        sta = network.WLAN(network.STA_IF)
        if not sta.isconnected():
            return "STA 未连接", 400, {'Content-Type': 'text/plain; charset=utf-8'}
        udp.send_route_learn_request()  # 已在 udp.py 中实现
        return "STA 路由表学习请求已发送", 200, {'Content-Type': 'text/plain; charset=utf-8'}
    @app.route("/api/route_sta_advertise_request")
    @gc_wrapper
    def route_sta_advertise_request(request):
        """在 STA 网段发送路由通告"""
        table = route.load_route_table()
        if not table:
            return "路由表为空", 200, {'Content-Type': 'text/plain; charset=utf-8'}
        sta = network.WLAN(network.STA_IF)
        if not sta.isconnected():
            return "STA 未连接", 400, {'Content-Type': 'text/plain; charset=utf-8'}
        udp.send_route_advertise()
        return "STA 路由表通告已发送", 200, {'Content-Type': 'text/plain; charset=utf-8'}
    @app.route("/api/route_sta_sync_request")
    @gc_wrapper
    def route_sta_sync_request(request):
        """在 STA 网段同步路由表（通告 + 学习）"""
        table = route.load_route_table()
        if table:
            sta = network.WLAN(network.STA_IF)
            if sta.isconnected():
                udp.send_route_advertise()
        sta = network.WLAN(network.STA_IF)
        if not sta.isconnected():
            return "STA 未连接", 400, {'Content-Type': 'text/plain; charset=utf-8'}
        udp.send_route_learn_request()
        return "STA 路由表同步请求已发送（通告+学习）", 200, {'Content-Type': 'text/plain; charset=utf-8'}
    # ========================================================================
    # API：系统操作
    # ========================================================================

    @app.route("/api/reboot")
    @gc_wrapper
    def reboot_device(request):
        """重启设备"""
        def _do_reboot():
            time.sleep(0.1)
            machine.reset()
        _thread.start_new_thread(_do_reboot, ())
        return "设备正在重启...", 200, {'Content-Type': 'text/plain; charset=utf-8'}