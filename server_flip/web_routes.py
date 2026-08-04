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
# web_routes.py - HTTP 路由（仅 API）
"""
提供所有 API 接口，不提供网页页面。
配置通过 config 模块动态获取。
"""

# =============================================================================
# 导入所需模块
# =============================================================================
import json
import time
import _thread
import machine
import network
import config
import util
from util import mac_to_str, gc_wrapper
import wifi
import udp
import neighbor
import route
from constants import MIN_PORT, MAX_PORT
from loader import load_api_catalog, load_all_api_types


def get_request_param(request, key, default=""):
    if request.method == "POST":
        # 尝试 JSON
        if request.headers.get("Content-Type", "").startswith("application/json"):
            try:
                data = request.json
                if data is not None and isinstance(data, dict):
                    return data.get(key, default)
            except:
                pass
        # 尝试 form（确保 request.form 不为 None）
        form = request.form
        if form is not None and isinstance(form, dict):
            val = form.get(key)
            if val is not None:
                return val
    # GET 或 fallback
    args = request.args
    if args is None:
        args = {}
    return args.get(key, default)


def cors_headers():
    """返回跨域允许的响应头"""
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type"
    }


def make_response(data, status=200, content_type='text/plain'):
    """构造带 CORS 和 Content-Type 的响应"""
    headers = cors_headers()
    headers['Content-Type'] = content_type
    if isinstance(data, (dict, list)):
        data = json.dumps(data)
    return data, status, headers


def with_cors(func):
    """装饰器：处理 OPTIONS 预检请求"""
    def wrapper(request):
        if request.method == "OPTIONS":
            return make_response("", 200, content_type='text/plain')
        return func(request)
    return wrapper


def setup_routes(app):
    """注册 API 路由（仅保留 /api/*）"""

    # ========================================================================
    # 根路径：返回 API 使用说明
    # ========================================================================
    @app.route("/", methods=["GET", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def root(request):
        """返回 API 使用指引"""
        info = {
            "message": "ESP32-C3 API Server",
            "endpoints": {
                "/api": "查看所有 API 类型列表 (GET)",
                "/api/get_api?type=<类型>": "按类型获取 API 列表 (GET)",
                "/api/...": "具体 API 接口，请查看 /api 返回的类型列表"
            },
            "example": "/api/get_api?type=neighbor"
        }
        return make_response(info, content_type='application/json')

    # ========================================================================
    # API：目录（只返回类型列表）
    # ========================================================================
    @app.route("/api", methods=["GET", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def api_catalog(request):
        """返回所有 API 的分类名称列表"""
        types = load_all_api_types()
        return make_response({"types": types}, content_type='application/json')

    # ========================================================================
    # API：按类型获取详细 API 列表
    # ========================================================================
    @app.route("/api/get_api", methods=["GET", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def get_api_by_type(request):
        """根据类型返回 API 列表"""
        api_type = get_request_param(request, "type", "").strip()
        if not api_type:
            return make_response("缺少 type 参数", 400, content_type='text/plain')
        data = load_api_catalog(api_type)
        if not data:
            return make_response(
                {"error": f"未知类型 '{api_type}'，可用类型: {load_all_api_types()}"},
                404,
                content_type='application/json'
            )
        return make_response(data, content_type='application/json')

    # # ========================================================================
    # # 页面路由（显式添加，避免循环）
    # # ========================================================================
    # # ---------- 页面路由（显式添加，避免循环） ----------
    # @app.route("/home", methods=["GET"])
    # def home_page(request):
    #     try:
    #         with open("web/home.html", "r") as f:
    #             return f.read(), 200, {"Content-Type": "text/html"}
    #     except:
    #         return "Page not found", 404
    #
    # @app.route("/broadcast", methods=["GET"])
    # def broadcast_page(request):
    #     try:
    #         with open("web/broadcast.html", "r") as f:
    #             return f.read(), 200, {"Content-Type": "text/html"}
    #     except:
    #         return "Page not found", 404
    #
    # @app.route("/unicast", methods=["GET"])
    # def unicast_page(request):
    #     try:
    #         with open("web/unicast.html", "r") as f:
    #             return f.read(), 200, {"Content-Type": "text/html"}
    #     except:
    #         return "Page not found", 404
    #
    # @app.route("/neighbor", methods=["GET"])
    # def neighbor_page(request):
    #     try:
    #         with open("web/neighbor.html", "r") as f:
    #             return f.read(), 200, {"Content-Type": "text/html"}
    #     except:
    #         return "Page not found", 404
    #
    # @app.route("/route", methods=["GET"])
    # def route_page(request):
    #     try:
    #         with open("web/route.html", "r") as f:
    #             return f.read(), 200, {"Content-Type": "text/html"}
    #     except:
    #         return "Page not found", 404
    #
    # @app.route("/ap", methods=["GET"])
    # def ap_page(request):
    #     try:
    #         with open("web/ap.html", "r") as f:
    #             return f.read(), 200, {"Content-Type": "text/html"}
    #     except:
    #         return "Page not found", 404
    #
    # @app.route("/sta", methods=["GET"])
    # def sta_page(request):
    #     try:
    #         with open("web/sta.html", "r") as f:
    #             return f.read(), 200, {"Content-Type": "text/html"}
    #     except:
    #         return "Page not found", 404
    #
    # @app.route("/udp", methods=["GET"])
    # def udp_page(request):
    #     try:
    #         with open("web/udp.html", "r") as f:
    #             return f.read(), 200, {"Content-Type": "text/html"}
    #     except:
    #         return "Page not found", 404
    #
    # @app.route("/system", methods=["GET"])
    # def system_page(request):
    #     try:
    #         with open("web/system.html", "r") as f:
    #             return f.read(), 200, {"Content-Type": "text/html"}
    #     except:
    #         return "Page not found", 404

    # ========================================================================
    # API：系统配置修改
    # ========================================================================

    @app.route("/api/set_ap_ip", methods=["POST", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def set_ap_ip(request):
        new_ip = get_request_param(request, "ip")
        if not new_ip:
            return make_response("缺少 ip 参数", 400, content_type='text/plain; charset=utf-8')
        parts = new_ip.split('.')
        if len(parts) != 4:
            return make_response("IP 格式无效", 400, content_type='text/plain; charset=utf-8')
        for p in parts:
            if not p.isdigit() or int(p) < 0 or int(p) > 255:
                return make_response("IP 格式无效", 400, content_type='text/plain; charset=utf-8')
        cfg = config.load_system_config()
        cfg["ap_ip"] = new_ip
        config.save_system_config(cfg)
        config.load_global_config()
        return make_response(f"AP IP 已更改为 {new_ip}，请重启设备生效。", 200, content_type='text/plain; charset=utf-8')

    @app.route("/api/set_ap_ssid_password", methods=["POST", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def set_ap_ssid_password(request):
        ssid = get_request_param(request, "ssid")
        password = get_request_param(request, "password")
        if not ssid:
            return make_response("缺少 ssid 参数", 400, content_type='text/plain; charset=utf-8')
        cfg = config.load_system_config()
        cfg["ap_ssid"] = ssid
        cfg["ap_password"] = password
        config.save_system_config(cfg)
        return make_response(f"AP SSID 已改为 '{ssid}'，密码已更新，请重启设备生效。", 200, content_type='text/plain; charset=utf-8')

    @app.route("/api/set_udp_recv_port", methods=["POST", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def set_udp_recv_port(request):
        port_str = get_request_param(request, "port")
        if not port_str:
            return make_response("缺少 port 参数", 400, content_type='text/plain; charset=utf-8')
        try:
            port = int(port_str)
            if port < MIN_PORT or port > MAX_PORT:
                raise ValueError
        except:
            return make_response("端口号必须是 1-65535 的整数", 400, content_type='text/plain; charset=utf-8')
        cfg = config.load_system_config()
        cfg["udp_recv_port"] = port
        config.save_system_config(cfg)
        return make_response(f"UDP 接收端口已改为 {port}，请重启设备生效。", 200, content_type='text/plain; charset=utf-8')

    @app.route("/api/set_udp_broadcast_port", methods=["POST", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def set_udp_broadcast_port(request):
        port_str = get_request_param(request, "port")
        if not port_str:
            return make_response("缺少 port 参数", 400, content_type='text/plain; charset=utf-8')
        try:
            port = int(port_str)
            if port < MIN_PORT or port > MAX_PORT:
                raise ValueError
        except:
            return make_response("端口号必须是 1-65535 的整数", 400, content_type='text/plain; charset=utf-8')
        cfg = config.load_system_config()
        cfg["udp_broadcast_port"] = port
        config.save_system_config(cfg)
        return make_response(f"UDP 广播/单播目标端口已改为 {port}，请重启设备生效。", 200, content_type='text/plain; charset=utf-8')

    @app.route("/api/reset_ap_config", methods=["POST", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def reset_ap_config(request):
        config.reset_system_config()
        config.load_global_config()
        return make_response("AP 配置已重置为默认值，请重启设备生效。", 200, content_type='text/plain; charset=utf-8')

    @app.route("/api/set_led_pin", methods=["POST", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def set_led_pin(request):
        pin_str = get_request_param(request, "pin")
        if not pin_str:
            return make_response("缺少 pin 参数", 400, content_type='text/plain; charset=utf-8')
        try:
            pin = int(pin_str)
            if pin < 0 or pin > 21 or pin in range(12, 18):
                return make_response("引脚无效或为 Flash 专用引脚", 400, content_type='text/plain; charset=utf-8')
        except:
            return make_response("引脚必须是整数", 400, content_type='text/plain; charset=utf-8')
        cfg = config.load_system_config()
        cfg["led_pin"] = pin
        config.save_system_config(cfg)
        config.g_led_pin = pin
        return make_response(f"LED 引脚已更改为 GPIO{pin}，请重启设备生效。", 200, content_type='text/plain; charset=utf-8')

    @app.route("/api/get_led_pin", methods=["GET", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def get_led_pin(request):
        return make_response({"pin": config.g_led_pin}, 200, content_type='application/json; charset=utf-8')

    @app.route("/api/get_self_mac", methods=["GET", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def get_self_mac(request):
        mac_str = util.get_self_mac()
        return make_response({"mac": mac_str}, 200, content_type='application/json; charset=utf-8')

    @app.route("/api/set_ap_netmask", methods=["POST", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def set_ap_netmask(request):
        mask = get_request_param(request, "netmask")
        if not mask:
            return make_response("缺少 netmask 参数", 400, content_type='text/plain; charset=utf-8')
        parts = mask.split('.')
        if len(parts) != 4 or not all(p.isdigit() and 0 <= int(p) <= 255 for p in parts):
            return make_response("无效子网掩码格式", 400, content_type='text/plain; charset=utf-8')
        config.update_ap_netmask(mask)
        return make_response(f"AP 子网掩码已设为 {mask}，需重启生效", 200, content_type='text/plain; charset=utf-8')

    @app.route("/api/set_ap_gateway", methods=["POST", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def set_ap_gateway(request):
        gateway = get_request_param(request, "gateway")
        if not gateway:
            return make_response("缺少 gateway 参数", 400, content_type='text/plain; charset=utf-8')
        parts = gateway.split('.')
        if len(parts) != 4 or not all(p.isdigit() and 0 <= int(p) <= 255 for p in parts):
            return make_response("无效网关地址格式", 400, content_type='text/plain; charset=utf-8')
        config.update_ap_gateway(gateway)
        return make_response(f"AP 网关已设为 {gateway}，需重启生效", 200, content_type='text/plain; charset=utf-8')

    @app.route("/api/config_get", methods=["GET", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def config_get(request):
        sys_cfg = config.load_system_config()
        wifi_cfg = config.load_wifi_config()
        neighbor_cfg = config.load_neighbor_config()
        route_cfg = config.load_route_config()
        return make_response({
            "system": sys_cfg,
            "wifi": {"ssid": wifi_cfg[0], "password": wifi_cfg[1]},
            "neighbor": neighbor_cfg,
            "route": route_cfg
        }, 200, content_type='application/json; charset=utf-8')

    @app.route("/api/set_self_nickname", methods=["POST", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def set_self_nickname(request):
        nickname = get_request_param(request, "nickname")
        if not nickname:
            return make_response("缺少 nickname 参数", 400, content_type='text/plain; charset=utf-8')
        nickname = nickname.strip()
        if not nickname:
            return make_response("昵称不能为空", 400, content_type='text/plain; charset=utf-8')
        try:
            config.update_device_nickname(nickname)
            from neighbor import update_self_nickname
            update_self_nickname()
            return make_response(f"本机昵称已更新为 '{nickname}'", 200, content_type='text/plain; charset=utf-8')
        except Exception as e:
            return make_response(f"更新失败: {e}", 500, content_type='text/plain; charset=utf-8')

    @app.route("/api/get_led_status", methods=["GET", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def get_led_status(request):
        sta = network.WLAN(network.STA_IF)
        connected = sta.isconnected()
        status = "ON" if connected else "OFF"
        return make_response({"status": status}, 200, content_type='application/json; charset=utf-8')

    @app.route("/api/get_max_udp_messages", methods=["GET", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def get_max_udp_messages(request):
        return make_response({"value": config.g_max_udp_messages}, 200, content_type='application/json; charset=utf-8')

    @app.route("/api/set_max_udp_messages", methods=["POST", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def set_max_udp_messages(request):
        val_str = get_request_param(request, "value")
        if not val_str:
            return make_response("缺少 value 参数", 400, content_type='text/plain; charset=utf-8')
        try:
            val = int(val_str)
            if val < 1:
                return make_response("value 必须 >= 1", 400, content_type='text/plain; charset=utf-8')
        except:
            return make_response("value 必须是整数", 400, content_type='text/plain; charset=utf-8')
        cfg = config.load_system_config()
        cfg["max_udp_messages"] = val
        config.save_system_config(cfg)
        config.g_max_udp_messages = val
        while len(udp.udp_messages) > val:
            udp.udp_messages.pop(0)
        return make_response(f"UDP 最大消息数已设为 {val}，已生效", 200, content_type='text/plain; charset=utf-8')

    @app.route("/api/get_sta_timeout", methods=["GET", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def get_sta_timeout(request):
        return make_response({"value": config.g_sta_timeout}, 200, content_type='application/json; charset=utf-8')

    @app.route("/api/set_sta_timeout", methods=["POST", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def set_sta_timeout(request):
        val_str = get_request_param(request, "value")
        if not val_str:
            return make_response("缺少 value 参数", 400, content_type='text/plain; charset=utf-8')
        try:
            val = int(val_str)
            if val < 5:
                return make_response("超时时间必须 >= 5 秒", 400, content_type='text/plain; charset=utf-8')
        except:
            return make_response("value 必须是整数", 400, content_type='text/plain; charset=utf-8')
        cfg = config.load_system_config()
        cfg["sta_timeout"] = val
        config.save_system_config(cfg)
        config.g_sta_timeout = val
        return make_response(f"STA 连接超时已设为 {val} 秒，请重启设备生效。", 200, content_type='text/plain; charset=utf-8')

    @app.route("/api/set_ap_net_segment", methods=["POST", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def set_ap_net_segment(request):
        segment_str = get_request_param(request, "segment")
        if not segment_str:
            return make_response("缺少 segment 参数", 400, content_type='text/plain; charset=utf-8')
        try:
            seg = int(segment_str)
            if seg < 0 or seg > 255:
                raise ValueError
        except:
            return make_response("segment 必须是 0-255 的整数", 400, content_type='text/plain; charset=utf-8')
        ip_parts = config.g_ap_ip.split('.')
        ip_parts[2] = str(seg)
        new_ip = '.'.join(ip_parts)
        cfg = config.load_system_config()
        cfg["ap_ip"] = new_ip
        config.save_system_config(cfg)
        config.load_global_config()
        return make_response(f"AP 网段已改为 {seg}，新 IP 将为 {new_ip}，请重启设备生效。", 200, content_type='text/plain; charset=utf-8')

    @app.route("/api/set_udp_poll_interval", methods=["POST", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def set_udp_poll_interval(request):
        interval_str = get_request_param(request, "interval")
        if not interval_str:
            return make_response("缺少 interval 参数", 400, content_type='text/plain; charset=utf-8')
        try:
            interval = int(interval_str)
            if interval < 500:
                return make_response("间隔不能小于 500 毫秒", 400, content_type='text/plain; charset=utf-8')
        except:
            return make_response("interval 必须是正整数", 400, content_type='text/plain; charset=utf-8')
        cfg = config.load_system_config()
        cfg["udp_poll_interval"] = interval
        config.save_system_config(cfg)
        config.g_udp_poll_interval = interval
        return make_response(f"轮询间隔已设为 {interval} 毫秒，请刷新页面以应用新间隔", 200, content_type='text/plain; charset=utf-8')

    # ========================================================================
    # API：状态查询
    # ========================================================================

    @app.route("/api/get_ap_status", methods=["GET", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def get_ap_status(request):
        ap = network.WLAN(network.AP_IF)
        active = ap.active()
        return make_response({
            "active": active,
            "ssid": config.g_ap_ssid,
            "ip": config.g_ap_ip,
            "subnet": config.g_ap_subnet
        }, 200, content_type='application/json; charset=utf-8')

    @app.route("/api/get_sta_status", methods=["GET", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def get_sta_status(request):
        sta = network.WLAN(network.STA_IF)
        connected = sta.isconnected()
        ssid = ""
        ip = ""
        if connected:
            ssid = sta.config('essid')
            if isinstance(ssid, bytes):
                ssid = ssid.decode()
            ip = sta.ifconfig()[0]
        return make_response({
            "connected": connected,
            "ssid": ssid,
            "ip": ip
        }, 200, content_type='application/json; charset=utf-8')

    @app.route("/api/get_ap_ssid_password", methods=["GET", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def get_ap_ssid_password(request):
        return make_response({
            "ssid": config.g_ap_ssid,
            "password": config.g_ap_password
        }, 200, content_type='application/json; charset=utf-8')

    @app.route("/api/get_sta_ssid_password", methods=["GET", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def get_sta_ssid_password(request):
        cfg = config.load_wifi_config()
        return make_response({"ssid": cfg[0], "password": cfg[1]}, 200, content_type='application/json; charset=utf-8')

    @app.route("/api/set_sta_ssid_password", methods=["POST", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def set_sta_ssid_password(request):
        ssid = get_request_param(request, "ssid")
        password = get_request_param(request, "password")
        if not ssid:
            return make_response("缺少 ssid 参数", 400, content_type='text/plain; charset=utf-8')
        if ssid == "":
            return make_response("ssid 不能为空", 400, content_type='text/plain; charset=utf-8')
        config.save_wifi_config(ssid, password)
        return make_response("STA SSID/密码已更新，请重启设备生效。", 200, content_type='text/plain; charset=utf-8')

    @app.route("/api/get_udp_recv_port", methods=["GET", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def get_udp_recv_port(request):
        return make_response({"value": config.g_udp_recv_port}, 200, content_type='application/json; charset=utf-8')

    @app.route("/api/get_udp_broadcast_port", methods=["GET", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def get_udp_broadcast_port(request):
        return make_response({"value": config.g_udp_broadcast_port}, 200, content_type='application/json; charset=utf-8')

    @app.route("/api/get_udp_poll_interval", methods=["GET", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def get_udp_poll_interval(request):
        return make_response({"interval": config.g_udp_poll_interval}, 200, content_type='application/json; charset=utf-8')

    @app.route("/api/get_nicknames", methods=["GET", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def get_nicknames(request):
        return make_response(neighbor.load_nicknames(), 200, content_type='application/json; charset=utf-8')

    @app.route("/api/get_macs", methods=["GET", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def get_macs(request):
        ap = network.WLAN(network.AP_IF)
        stations = ap.status('stations')
        nicknames = neighbor.load_nicknames()
        if not stations:
            return make_response("当前没有设备连接", 200, content_type='text/plain; charset=utf-8')
        lines = []
        for mac in stations:
            mac_str = mac_to_str(mac)
            nick = nicknames.get(mac_str, '')
            lines.append(f"{mac_str}  昵称:{nick if nick else '未设置'}")
        return make_response("\n".join(lines), 200, content_type='text/plain; charset=utf-8')

    @app.route("/api/list_auth", methods=["GET", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def list_auth(request):
        devices = neighbor.get_auth_devices()
        if not devices:
            return make_response("暂无已注册设备", 200, content_type='text/plain; charset=utf-8')
        lines = []
        for dev in devices:
            lines.append(f"{dev['mac']}  IP:{dev['ip']}  （TTL = {dev['ttl']}） 昵称:{dev['nickname'] or '未设置'}")
        return make_response("\n".join(lines), 200, content_type='text/plain; charset=utf-8')

    @app.route("/api/memory", methods=["GET", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def get_memory(request):
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
        return make_response(data, 200, content_type='application/json; charset=utf-8')

    # ========================================================================
    # API：邻居表操作
    # ========================================================================

    @app.route("/api/clear_neighbors", methods=["POST", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def clear_neighbors(request):
        nb = neighbor.load_neighbors()
        if not nb:
            return make_response("邻居表已为空", 200, content_type='text/plain; charset=utf-8')
        neighbor.save_neighbors({})
        return make_response("邻居表已清空", 200, content_type='text/plain; charset=utf-8')

    # @app.route("/api/clear_unauth", methods=["POST", "OPTIONS"])
    # @gc_wrapper
    # @with_cors
    # def clear_unauth_api(request):
    #     count = neighbor.clear_unauth()
    #     return make_response(f"已清除 {count} 个未注册设备", 200, content_type='text/plain; charset=utf-8')

    @app.route("/api/delete_device", methods=["POST", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def delete_device_api(request):
        mac = get_request_param(request, "mac")
        if not mac:
            return make_response("缺少 mac 参数", 400, content_type='text/plain; charset=utf-8')
        mac = mac_to_str(mac)
        if neighbor.delete_device(mac):
            return make_response(f"设备 {mac} 已删除", 200, content_type='text/plain; charset=utf-8')
        else:
            return make_response("设备不存在", 404, content_type='text/plain; charset=utf-8')

    @app.route("/api/set_nickname", methods=["POST", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def set_nickname_api(request):
        mac = get_request_param(request, "mac")
        nickname = get_request_param(request, "nickname")
        if not mac or not nickname:
            return make_response("缺少 mac 或 nickname 参数", 400, content_type='text/plain; charset=utf-8')
        mac = mac_to_str(mac)
        if neighbor.set_nickname(mac, nickname):
            return make_response(f"昵称设置成功: {mac} -> {nickname}", 200, content_type='text/plain; charset=utf-8')
        else:
            return make_response("设备未认证或不存在", 404, content_type='text/plain; charset=utf-8')

    # ========================================================================
    # 邻居间隔配置
    # ========================================================================

    @app.route("/api/set_neighbor_interval", methods=["POST", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def set_neighbor_interval(request):
        interval = get_request_param(request, "interval")
        if not interval:
            return make_response("缺少 interval 参数", 400, content_type='text/plain; charset=utf-8')
        try:
            val = int(interval)
            if val < 5:
                return make_response("间隔必须 >= 5 秒", 400, content_type='text/plain; charset=utf-8')
        except:
            return make_response("interval 必须是整数", 400, content_type='text/plain; charset=utf-8')
        config.update_neighbor_advertise_interval(val)
        return make_response(f"邻居广播间隔已设为 {val} 秒", 200, content_type='text/plain; charset=utf-8')

    @app.route("/api/get_neighbor_interval", methods=["GET", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def get_neighbor_interval(request):
        return make_response({"interval": config.g_neighbor_advertise_interval}, 200, content_type='application/json; charset=utf-8')

    # ========================================================================
    # API：路由表操作
    # ========================================================================

    @app.route("/api/route_table", methods=["GET", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def get_route_table(request):
        return make_response(route.load_route_table(), 200, content_type='application/json; charset=utf-8')

    @app.route("/api/route_table_with_nick", methods=["GET", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def route_table_with_nick(request):
        route_table = route.load_route_table()
        nicknames = neighbor.load_nicknames()
        result = {}
        for mac, entry in route_table.items():
            result[mac] = {
                "ip": entry["ip"],
                "ttl": entry["ttl"],
                "distance": entry["step"],
                "nickname": nicknames.get(mac, "")
            }
        return make_response(result, 200, content_type='application/json; charset=utf-8')

    @app.route("/api/route_delete", methods=["POST", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def route_delete_api(request):
        mac = get_request_param(request, "mac")
        if not mac:
            return make_response("缺少 mac 参数", 400, content_type='text/plain; charset=utf-8')
        mac = mac_to_str(mac)
        if route.route_delete(mac):
            return make_response(f"路由 {mac} 已删除", 200, content_type='text/plain; charset=utf-8')
        else:
            return make_response("路由不存在", 404, content_type='text/plain; charset=utf-8')

    @app.route("/api/set_route_interval", methods=["POST", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def set_route_interval(request):
        interval = get_request_param(request, "interval")
        if not interval:
            return make_response("缺少 interval 参数", 400, content_type='text/plain; charset=utf-8')
        try:
            val = int(interval)
            if val < 5:
                return make_response("间隔必须 >= 5 秒", 400, content_type='text/plain; charset=utf-8')
        except:
            return make_response("interval 必须是整数", 400, content_type='text/plain; charset=utf-8')
        config.update_route_advertise_interval(val)
        return make_response(f"路由通告间隔已设为 {val} 秒", 200, content_type='text/plain; charset=utf-8')

    @app.route("/api/get_route_interval", methods=["GET", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def get_route_interval(request):
        return make_response({"interval": config.g_route_advertise_interval}, 200, content_type='application/json; charset=utf-8')

    @app.route("/api/route_clear", methods=["POST", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def route_clear_api(request):
        route.save_route_table({})
        return make_response("路由表已清空", 200, content_type='text/plain; charset=utf-8')

    # ========================================================================
    # API：UDP 操作
    # ========================================================================

    @app.route("/api/udp_messages", methods=["GET", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def get_udp_messages(request):
        msgs = udp.get_udp_messages()
        return make_response(msgs, 200, content_type='application/json; charset=utf-8')

    @app.route("/api/clear_udp_messages", methods=["POST", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def clear_udp_messages(request):
        udp.clear_udp_messages()
        return make_response("UDP 消息已清空", 200, content_type='text/plain; charset=utf-8')

    # ========================================================================
    # API：UDP 单播
    # ========================================================================

    @app.route("/api/udp_send_ip", methods=["GET", "POST", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def udp_send_ip(request):
        target_ip = get_request_param(request, "ip")
        content = get_request_param(request, "content")
        if not target_ip or not content:
            return make_response("缺少 ip 或 content 参数", 400, content_type='text/plain; charset=utf-8')
        success = udp.udp_send_to_ip(target_ip, content)
        if success:
            return make_response("发送成功", 200, content_type='text/plain; charset=utf-8')
        else:
            return make_response("发送失败", 500, content_type='text/plain; charset=utf-8')

    @app.route("/api/udp_send_ap", methods=["GET", "POST", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def udp_send_ap(request):
        ip_tail = get_request_param(request, "ip_tail")
        content = get_request_param(request, "content")
        if not ip_tail or not content:
            return make_response("缺少 ip_tail 或 content 参数", 400, content_type='text/plain; charset=utf-8')
        prefix = '.'.join(config.g_ap_ip.split('.')[:-1])
        target_ip = f"{prefix}.{ip_tail}"
        success = udp.udp_send_to_ip(target_ip, content)
        if success:
            return make_response("发送成功", 200, content_type='text/plain; charset=utf-8')
        else:
            return make_response("发送失败", 500, content_type='text/plain; charset=utf-8')

    @app.route("/api/udp_send_sta", methods=["GET", "POST", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def udp_send_sta(request):
        ip_tail = get_request_param(request, "ip_tail")
        content = get_request_param(request, "content")
        if not ip_tail or not content:
            return make_response("缺少 ip_tail 或 content 参数", 400, content_type='text/plain; charset=utf-8')
        prefix = wifi.get_sta_prefix()
        if prefix is None:
            return make_response("STA 未连接，无法获取网段", 400, content_type='text/plain; charset=utf-8')
        target_ip = f"{prefix}.{ip_tail}"
        success = udp.udp_send_to_ip(target_ip, content)
        if success:
            return make_response("发送成功", 200, content_type='text/plain; charset=utf-8')
        else:
            return make_response("发送失败", 500, content_type='text/plain; charset=utf-8')

    @app.route("/api/send_to_nick", methods=["GET", "POST", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def send_to_nick(request):
        nickname = get_request_param(request, "nickname")
        content = get_request_param(request, "content")
        if not nickname or not content:
            return make_response("缺少 nickname 或 content 参数", 400, content_type='text/plain; charset=utf-8')
        nicknames = neighbor.load_nicknames()
        mac = None
        for m, n in nicknames.items():
            if n == nickname:
                mac = m
                break
        if not mac:
            return make_response("昵称不存在", 404, content_type='text/plain; charset=utf-8')
        neighbors = neighbor.load_neighbors()
        entry = neighbors.get(mac)
        if not entry:
            route_table = route.load_route_table()
            entry = route_table.get(mac)
            if not entry:
                return make_response("设备未在邻居表注册或路由表注册", 404, content_type='text/plain; charset=utf-8')
        target_ip = entry.get("ip")
        if not target_ip:
            return make_response("设备未在邻居表注册或路由表注册", 404, content_type='text/plain; charset=utf-8')
        success = udp.udp_send_to_ip(target_ip, content)
        if success:
            return make_response(f"消息已发送给昵称 '{nickname}'", 200, content_type='text/plain; charset=utf-8')
        else:
            return make_response("发送失败", 500, content_type='text/plain; charset=utf-8')

    # ========================================================================
    # API：UDP 路由单播
    # ========================================================================

    @app.route("/api/send_route_message", methods=["GET", "POST", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def send_route_message(request):
        dst_mac = get_request_param(request, "dst_mac")
        cmd_msg = get_request_param(request, "cmd_msg")
        if not dst_mac or not cmd_msg:
            return make_response("缺少 dst_mac 或 cmd_msg 参数", 400, content_type='text/plain; charset=utf-8')
        dst_mac = mac_to_str(dst_mac)
        ap_if = network.WLAN(network.AP_IF)
        src_mac = mac_to_str(ap_if.config('mac'))
        if dst_mac == src_mac:
            return make_response("不能发送给自己", 400, content_type='text/plain; charset=utf-8')
        success = udp.send_route_message(dst_mac, cmd_msg)
        if success:
            return make_response("路由消息已发送", 200, content_type='text/plain; charset=utf-8')
        else:
            return make_response("发送失败，目标不可达", 404, content_type='text/plain; charset=utf-8')

    # ========================================================================
    # API：UDP 广播
    # ========================================================================

    @app.route("/api/udp_broadcast", methods=["GET", "POST", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def udp_broadcast(request):
        content = get_request_param(request, "content")
        if not content:
            return make_response("缺少 content 参数", 400, content_type='text/plain; charset=utf-8')
        success = udp.send_broadcast_once(content)
        if success:
            return make_response("发送成功", 200, content_type='text/plain; charset=utf-8')
        else:
            return make_response("发送失败", 500, content_type='text/plain; charset=utf-8')

    @app.route("/api/udp_broadcast_sta", methods=["GET", "POST", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def udp_broadcast_sta(request):
        content = get_request_param(request, "content")
        if not content:
            return make_response("缺少 content 参数", 400, content_type='text/plain; charset=utf-8')
        prefix = wifi.get_sta_prefix()
        if prefix is None:
            return make_response("STA 未连接，无法获取网段", 400, content_type='text/plain; charset=utf-8')
        success = udp.send_sta_broadcast_once(content)
        if success:
            return make_response("发送成功", 200, content_type='text/plain; charset=utf-8')
        else:
            return make_response("发送失败", 500, content_type='text/plain; charset=utf-8')

    @app.route("/api/udp_broadcast_apsta", methods=["GET", "POST", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def udp_broadcast_apsta(request):
        content = get_request_param(request, "content")
        if not content:
            return make_response("缺少 content 参数", 400, content_type='text/plain; charset=utf-8')
        success = udp.send_both_broadcast_once(content)
        if success:
            return make_response("发送成功", 200, content_type='text/plain; charset=utf-8')
        else:
            return make_response("发送失败", 500, content_type='text/plain; charset=utf-8')

    # # ========================================================================
    # # API：UDP 邻居表操作
    # # ========================================================================
    #
    # @app.route("/api/auth_request", methods=["POST", "OPTIONS"])
    # @gc_wrapper
    # @with_cors
    # def auth_request(request):
    #     udp.send_neighbor_register_request("AP")
    #     return make_response("AP 邻居表注册请求已发送", 200, content_type='text/plain; charset=utf-8')
    #
    # @app.route("/api/auth_request_sta", methods=["POST", "OPTIONS"])
    # @gc_wrapper
    # @with_cors
    # def auth_request_sta(request):
    #     prefix = wifi.get_sta_prefix()
    #     if prefix is None:
    #         return make_response("STA 未连接，无法获取网段", 400, content_type='text/plain; charset=utf-8')
    #     udp.send_neighbor_register_request("STA")
    #     return make_response("STA 邻居表注册请求已发送", 200, content_type='text/plain; charset=utf-8')
    #
    # @app.route("/api/auth_request_apsta", methods=["POST", "OPTIONS"])
    # @gc_wrapper
    # @with_cors
    # def auth_request_apsta(request):
    #     neighbor.ttl_decrement_neighbors()
    #     udp.send_neighbor_register_request("STA")
    #     udp.send_neighbor_register_request("AP")
    #     return make_response("AP+STA 邻居表注册请求已发送", 200, content_type='text/plain; charset=utf-8')
    #
    # @app.route("/api/neighbor_sta_update_request", methods=["POST", "OPTIONS"])
    # @gc_wrapper
    # @with_cors
    # def neighbor_sta_update_request(request):
    #     sta = network.WLAN(network.STA_IF)
    #     if not sta.isconnected():
    #         return make_response("STA 未连接", 400, content_type='text/plain; charset=utf-8')
    #     udp.send_neighbor_update_request("STA")
    #     return make_response("邻居表 STA 更新请求已发送", 200, content_type='text/plain; charset=utf-8')
    #
    # @app.route("/api/neighbor_ap_update_request", methods=["POST", "OPTIONS"])
    # @gc_wrapper
    # @with_cors
    # def neighbor_ap_update_request(request):
    #     udp.send_neighbor_update_request("AP")
    #     return make_response("邻居表 AP 更新请求已发送", 200, content_type='text/plain; charset=utf-8')
    #
    # # ========================================================================
    # # API：UDP 路由表操作
    # # ========================================================================
    #
    # @app.route("/api/route_ap_register_request", methods=["POST", "OPTIONS"])
    # @gc_wrapper
    # @with_cors
    # def route_ap_register_request(request):
    #     route.route_ttl_decrement()
    #     udp.send_route_register_request()
    #     return make_response("AP 路由表注册请求已发送", 200, content_type='text/plain; charset=utf-8')
    #
    # @app.route("/api/route_sta_update_request", methods=["POST", "OPTIONS"])
    # @gc_wrapper
    # @with_cors
    # def route_sta_update_request(request):
    #     sta = network.WLAN(network.STA_IF)
    #     if not sta.isconnected():
    #         return make_response("STA 未连接", 400, content_type='text/plain; charset=utf-8')
    #     udp.send_route_update_request()
    #     return make_response("STA 路由表更新请求已发送", 200, content_type='text/plain; charset=utf-8')
    #
    # @app.route("/api/route_sta_learn_request", methods=["POST", "OPTIONS"])
    # @gc_wrapper
    # @with_cors
    # def route_sta_learn_request(request):
    #     sta = network.WLAN(network.STA_IF)
    #     if not sta.isconnected():
    #         return make_response("STA 未连接", 400, content_type='text/plain; charset=utf-8')
    #     udp.send_route_learn_request()
    #     return make_response("STA 路由表学习请求已发送", 200, content_type='text/plain; charset=utf-8')
    #
    # @app.route("/api/route_sta_advertise_request", methods=["POST", "OPTIONS"])
    # @gc_wrapper
    # @with_cors
    # def route_sta_advertise_request(request):
    #     table = route.load_route_table()
    #     if not table:
    #         return make_response("路由表为空", 200, content_type='text/plain; charset=utf-8')
    #     sta = network.WLAN(network.STA_IF)
    #     if not sta.isconnected():
    #         return make_response("STA 未连接", 400, content_type='text/plain; charset=utf-8')
    #     udp.send_route_advertise()
    #     return make_response("STA 路由表通告已发送", 200, content_type='text/plain; charset=utf-8')
    #
    # @app.route("/api/route_sta_sync_request", methods=["POST", "OPTIONS"])
    # @gc_wrapper
    # @with_cors
    # def route_sta_sync_request(request):
    #     table = route.load_route_table()
    #     if table:
    #         sta = network.WLAN(network.STA_IF)
    #         if sta.isconnected():
    #             udp.send_route_advertise()
    #     sta = network.WLAN(network.STA_IF)
    #     if not sta.isconnected():
    #         return make_response("STA 未连接", 400, content_type='text/plain; charset=utf-8')
    #     udp.send_route_learn_request()
    #     return make_response("STA 路由表同步请求已发送（通告+学习）", 200, content_type='text/plain; charset=utf-8')

    # ========================================================================
    # API：系统操作
    # ========================================================================

    @app.route("/api/reboot", methods=["POST", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def reboot_device(request):
        def _do_reboot():
            time.sleep(0.1)
            machine.reset()
        _thread.start_new_thread(_do_reboot, ())
        return make_response("设备正在重启...", 200, content_type='text/plain; charset=utf-8')

    @app.route("/api/config_reload", methods=["POST", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def config_reload(request):
        config.load_all_configs()
        return make_response("配置已重新加载", 200, content_type='text/plain; charset=utf-8')

    @app.route("/api/config_reset", methods=["POST", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def config_reset(request):
        def _do_reset():
            import os
            files = ["system-config.json", "wifi-config.json", "nicknames.json",
                     "neighbors.json", "route_table.json", "neighbor-config.json",
                     "route-config.json"]
            for f in files:
                try:
                    os.remove(f)
                except:
                    pass
            time.sleep(0.5)
            machine.reset()
        _thread.start_new_thread(_do_reset, ())
        return make_response("正在重置配置并重启...", 200, content_type='text/plain; charset=utf-8')

    # ========================================================================
    # API：重置引脚配置
    # ========================================================================

    @app.route("/api/set_reset_pin", methods=["POST", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def set_reset_pin(request):
        pin_str = get_request_param(request, "pin")
        if not pin_str:
            return make_response("缺少 pin 参数", 400, content_type='text/plain; charset=utf-8')
        try:
            pin = int(pin_str)
            if pin < 0 or pin > 21 or pin in range(12, 18):
                return make_response("引脚无效或为 Flash 专用引脚", 400, content_type='text/plain; charset=utf-8')
        except:
            return make_response("引脚必须是整数", 400, content_type='text/plain; charset=utf-8')
        config.update_reset_pin(pin)
        return make_response(f"重置引脚已设为 GPIO{pin}，请重启设备生效。", 200, content_type='text/plain; charset=utf-8')

    @app.route("/api/set_reset_hold_time", methods=["POST", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def set_reset_hold_time(request):
        time_str = get_request_param(request, "seconds")
        if not time_str:
            return make_response("缺少 seconds 参数", 400, content_type='text/plain; charset=utf-8')
        try:
            seconds = int(time_str)
            if seconds < 2:
                return make_response("保持时间至少为 2 秒", 400, content_type='text/plain; charset=utf-8')
        except:
            return make_response("seconds 必须是整数", 400, content_type='text/plain; charset=utf-8')
        config.update_reset_hold_time(seconds)
        return make_response(f"重置保持时间已设为 {seconds} 秒，请重启设备生效。", 200, content_type='text/plain; charset=utf-8')

    @app.route("/api/get_reset_status", methods=["GET", "OPTIONS"])
    @gc_wrapper
    @with_cors
    def get_reset_status(request):
        return make_response({
            "pin": config.g_reset_pin,
            "hold_time": config.g_reset_hold_time
        }, 200, content_type='application/json; charset=utf-8')