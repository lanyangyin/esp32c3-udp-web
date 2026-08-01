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

from lib.easyweb import EasyWeb
import web_routes



print("=== ESP32-C3 启动中 ===")
print("按住 Ctrl+C 或在此3秒内按 RST 后立即按 Ctrl+C 可进入 REPL")
time.sleep(3)
print("继续执行主程序...")


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


    # 启动 UDP 接收线程
    try:
        _thread.start_new_thread(udp.udp_receiver, ())
    except Exception as e:
        print(f"[UDP] 接收线程启动失败: {e}")


    # 创建 Web 应用并注册路由
    app = EasyWeb()
    web_routes.setup_routes(app)

    # 强制垃圾回收
    gc.collect()

    try:
        app.run(host="0.0.0.0", port=80)
    except Exception as e:
        import sys
        print("[HTTP] Web 服务器异常退出:")


if __name__ == "__main__":
    main()