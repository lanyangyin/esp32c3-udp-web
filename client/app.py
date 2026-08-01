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

from servo_control import ServoController
from servo_commands import set_servo_controllers
from ir05t import IR05T
from ir_commands import set_ir_object

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
        led.blink_once(3)

    # 启动 AP
    ap_ip = wifi.start_ap()

    # LED 闪烁测试
    print("[INIT] 启动测试: LED 闪烁 3 次")
    led.blink_once(3)

    # 连接 STA（若配置）
    ssid, password = config.load_wifi_config()
    if ssid:
        if wifi.connect_wifi(ssid, password, timeout=config.g_sta_timeout):
            led.on()
            print("[MAIN] Wi-Fi 已连接，LED 常亮")
        else:
            print("[MAIN] Wi-Fi 连接失败，保留配置，进入配置模式")
            led.off()
    else:
        print("[MAIN] 无有效 STA 配置，进入配置模式")
        led.off()

    # ---------- IR ----------
    ir_tx = config.g_ir_tx_pin
    ir_rx = config.g_ir_rx_pin
    # 先检查 TX 和 RX 是否都可用
    ok_tx, msg_tx = pin_claim(ir_tx, "IR05T_TX")
    ok_rx, msg_rx = pin_claim(ir_rx, "IR05T_RX")
    if not ok_tx:
        print(f"[INIT] IR TX 引脚冲突: {msg_tx}")
        # 如果 TX 冲突，则释放已申请的 RX（若有）
        if ok_rx:
            pin_release(ir_rx)
        ir = None
    elif not ok_rx:
        print(f"[INIT] IR RX 引脚冲突: {msg_rx}")
        pin_release(ir_tx)   # 释放已申请的 TX
        ir = None
    else:
        ir = IR05T(uart_id=1, tx_pin=ir_tx, rx_pin=ir_rx, baudrate=9600)
        set_ir_object(ir)
        print(f"[INIT] IR05T 初始化成功，TX=GPIO{ir_tx}, RX=GPIO{ir_rx}")

    # ---------- 舵机 ----------
    servo_controllers = {}
    servo_config = config.load_servo_config()
    for name, cfg in servo_config.items():
        pin = cfg.get("pin")
        if pin is None:
            continue
        # 检查引脚是否已被占用（LED、IR、其他舵机）
        ok, msg = pin_claim(pin, f"舵机-{name}")
        if not ok:
            print(f"[舵机] 跳过 '{name}': {msg}")
            continue
        try:
            ctrl = ServoController(pin=pin)
            ctrl.set_angle(cfg.get("init_angle", 90))
            servo_controllers[name] = ctrl
            print(f"[舵机] 初始化 '{name}' (GPIO{pin}) 成功")
        except Exception as e:
            print(f"[舵机] 初始化 '{name}' 失败: {e}")
            pin_release(pin)  # 释放该引脚
    set_servo_controllers(servo_controllers)


    # # 启动 UDP 接收线程
    # try:
    #     _thread.start_new_thread(udp.udp_receiver, ())
    # except Exception as e:
    #     print(f"[UDP] 接收线程启动失败: {e}")

    # 可选：强制垃圾回收，释放碎片
    gc.collect()

    try:
        udp.udp_receiver()
        # udp.neighbor_routing_diffusion()
    except Exception as e:
        import sys
        print(f"[UDP] 接收启动失败: {e}")


if __name__ == "__main__":
    main()