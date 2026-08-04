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
# app.py - 入口程序

import time
import gc
from led import LEDController
import config
from neighbor import update_self_nickname
import wifi
import udp
from util import pin_claim, pin_release
import _thread
import machine
from machine import Pin


from lib.easyweb import EasyWeb
import web_routes




print("=== ESP32-C3 启动中 ===")
print("按住 Ctrl+C 或在此3秒内按 RST 后立即按 Ctrl+C 可进入 REPL")
time.sleep(3)
print("继续执行主程序...")

def start_web_server():
    """启动 Web 服务器（独立线程）"""
    app = EasyWeb()
    web_routes.setup_routes(app)
    print("[WEB] Web 服务器启动 (端口 80)")
    app.run(host="0.0.0.0", port=80)

def main():
    # ---------- 1. 加载所有配置 ----------
    config.load_all_configs()

    # ---------- 更新本机昵称到昵称表，并处理冲突 ----------
    update_self_nickname()
    print(f"[INIT] 本机昵称: {config.g_device_nickname}")

    # ---------- LED ----------
    led_pin = config.g_led_pin
    pin_release(led_pin)
    ok, msg = pin_claim(led_pin, "LED")
    if not ok:
        print(f"[INIT] LED 初始化失败: {msg}")
        led = None
    else:
        led = LEDController(pin=led_pin)
        print(f"[INIT] LED 控制器已初始化，引脚 GPIO{led_pin}")
        led.blink_once(3)   # 启动闪烁一次

    # ---------- 重置引脚 ----------
    reset_pin = config.g_reset_pin
    pin_release(reset_pin)  # 先释放，避免冲突
    ok, msg = pin_claim(reset_pin, "重置引脚")
    if not ok:
        print(f"[INIT] 重置引脚冲突: {msg}，重置功能禁用")
        config.g_reset_pin_obj = None
    else:
        try:
            reset_pin_obj = Pin(reset_pin, Pin.IN, Pin.PULL_UP)
            config.g_reset_pin_obj = reset_pin_obj
            print(f"[INIT] 重置引脚已初始化 GPIO{reset_pin}，短接 {config.g_reset_hold_time} 秒触发重置")
        except Exception as e:
            print(f"[INIT] 重置引脚初始化失败: {e}")
            pin_release(reset_pin)
            config.g_reset_pin_obj = None

    # 启动 AP
    ap_ip = wifi.start_ap()

    # 连接 STA（若配置）
    ssid, password = config.load_wifi_config()
    if ssid:
        if wifi.connect_wifi(ssid, password, timeout=config.g_sta_timeout):
            if led:
                led.on()
            print("[MAIN] Wi-Fi 已连接，LED 常亮")
        else:
            print("[MAIN] Wi-Fi 连接失败，保留配置，进入配置模式")
            if led:
                led.off()
    else:
        print("[MAIN] 无有效 STA 配置，进入配置模式")
        if led:
            led.off()

    # ---------- 启动 UDP 邻居路由回复线程 ----------
    try:
        _thread.start_new_thread(udp.udp_neighbor_routing_reply, ())
    except Exception as e:
        print(f"[UDP] 回复线程启动失败: {e}")

    # ---------- 启动 Web 服务器（独立线程） ----------
    try:
        _thread.start_new_thread(start_web_server, ())
    except Exception as e:
        print(f"[WEB] Web 服务器启动失败: {e}")

    # 强制垃圾回收
    gc.collect()

    # 主线程保持运行（可执行一些轻量任务或空闲）
    try:
        udp.udp_receiver()
    except Exception as e:
        import sys
        print(f"[UDP] 接收启动失败: {e}")
        machine.reset()


if __name__ == "__main__":
    main()