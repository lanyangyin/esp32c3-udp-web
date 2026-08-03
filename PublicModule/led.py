# led.py - 适配低电平点亮的 LED（如 ESP32-C3 SuperMini 板载 LED）
from machine import Pin, PWM
import time

class LEDController:
    def __init__(self, pin=8, freq=1000):
        """
        初始化 LED 控制
        :param pin: GPIO 引脚号（ESP32-C3 SuperMini 板载 LED 通常为 8，低电平点亮）
        :param freq: PWM 频率
        """
        self.pin = Pin(pin, Pin.OUT)
        self.pwm = PWM(self.pin, freq=freq)
        self.off()  # 默认关闭（即输出高电平）

    def on(self):
        """常亮（低电平）"""
        self.pwm.duty(0)          # 低电平点亮

    def off(self):
        """常灭（高电平）"""
        self.pwm.duty(1023)       # 高电平熄灭

    def blink_once(self, count=1, on_time=0.2, off_time=0.2):
        """
        单次闪烁（闪 n 次）
        :param count: 闪烁次数
        :param on_time: 亮起时间（秒）
        :param off_time: 熄灭时间（秒）
        """
        for _ in range(count):
            self.on()
            time.sleep(on_time)
            self.off()
            time.sleep(off_time)

    def blink_loop(self, count=-1, interval=0.5, duration=None):
        """
        循环闪烁
        :param count: 闪烁次数，-1 表示无限循环
        :param interval: 每次闪烁的间隔（即亮->灭的周期，亮灭各占一半）
        :param duration: 总持续时间（秒），若指定则覆盖 count
        """
        if duration is not None:
            total_cycles = int(duration / (interval * 2))
            if total_cycles <= 0:
                total_cycles = 1
            count = total_cycles

        if count == -1:
            while True:
                self.on()
                time.sleep(interval)
                self.off()
                time.sleep(interval)
        else:
            for _ in range(count):
                self.on()
                time.sleep(interval)
                self.off()
                time.sleep(interval)

    def breathe(self, duration=3, steps=50):
        """
        呼吸灯效果（渐亮渐灭）
        :param duration: 一个完整呼吸周期的时间（秒）
        :param steps: 渐变步数（越大越平滑）
        """
        half_steps = steps // 2
        step_delay = duration / steps

        # 渐亮：从高电平到低电平（占空比从 1023 到 0）
        for i in range(half_steps):
            duty = int(1023 - 1023 * (i / half_steps))
            self.pwm.duty(duty)
            time.sleep(step_delay)
        # 渐灭：从低电平到高电平（占空比从 0 到 1023）
        for i in range(half_steps, 0, -1):
            duty = int(1023 - 1023 * (i / half_steps))
            self.pwm.duty(duty)
            time.sleep(step_delay)

    def test(self):
        """测试所有功能"""
        print("测试常亮 2 秒...")
        self.on()
        time.sleep(2)
        print("测试常灭 2 秒...")
        self.off()
        time.sleep(2)
        print("测试闪烁 3 次...")
        self.blink_once(3)
        print("测试呼吸灯 1 个周期...")
        self.breathe(duration=2)
        print("测试循环闪烁 3 次，间隔 0.3 秒...")
        self.blink_loop(count=3, interval=0.3)
        print("测试完成，最终关闭 LED。")
        self.off()

# 如果作为独立脚本运行，则执行测试
if __name__ == "__main__":
    led = LEDController()
    led.test()