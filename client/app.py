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


from servo_control import ServoController
from servo_commands import set_servo_controllers
from ir05t import IR05T
from ir_commands import set_ir_instances   # 改为注入字典


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

    # ---------- IR 多设备初始化 ----------
    ir_instances = {}
    ir_config = config.load_ir_config()   # 加载所有设备配置
    for name, cfg in ir_config.items():
        tx_pin = cfg.get('tx_pin')
        rx_pin = cfg.get('rx_pin')
        if tx_pin is None or rx_pin is None:
            print(f"[IR] 设备 '{name}' 缺少引脚，跳过")
            continue
        # 申请引脚
        ok_tx, msg_tx = pin_claim(tx_pin, f"IR-{name}-TX")
        if not ok_tx:
            print(f"[IR] 设备 '{name}' TX 引脚冲突: {msg_tx}")
            continue
        ok_rx, msg_rx = pin_claim(rx_pin, f"IR-{name}-RX")
        if not ok_rx:
            print(f"[IR] 设备 '{name}' RX 引脚冲突: {msg_rx}")
            pin_release(tx_pin)
            continue
        try:
            baudrate = cfg.get('baudrate', config.DEFAULT_IR_BAUDRATE)
            timeout = cfg.get('timeout', config.DEFAULT_IR_TIMEOUT)
            uart_id = cfg.get('uart_id', 1)
            obj = IR05T(uart_id=uart_id, tx_pin=tx_pin, rx_pin=rx_pin,
                        baudrate=baudrate, timeout=timeout)
            ir_instances[name] = obj
            print(f"[IR] 设备 '{name}' 初始化成功 (TX={tx_pin}, RX={rx_pin})")
        except Exception as e:
            print(f"[IR] 设备 '{name}' 初始化失败: {e}")
            pin_release(tx_pin)
            pin_release(rx_pin)
    # 注入所有 IR 实例
    set_ir_instances(ir_instances)

    # ---------- 舵机 ----------
    servo_controllers = {}
    servo_config = config.load_servo_config()
    for name, cfg in servo_config.items():
        pin = cfg.get("pin")
        if pin is None:
            continue
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
            pin_release(pin)
    set_servo_controllers(servo_controllers)

    # ---------- 启动 UDP 邻居路由回复线程 ----------
    try:
        _thread.start_new_thread(udp.udp_neighbor_routing_reply, ())
    except Exception as e:
        print(f"[UDP] 回复线程启动失败: {e}")

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