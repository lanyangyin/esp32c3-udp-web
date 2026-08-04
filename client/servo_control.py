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
# servo_control.py
from machine import Pin, PWM
import time

class ServoController:
    def __init__(self, pin, freq=50, min_duty=1638, max_duty=8192,
                 open_angle=80, close_angle=100, reset_angle=90):
        self.pin = pin
        self.freq = freq
        self.min_duty = min_duty
        self.max_duty = max_duty
        self.open_angle = open_angle
        self.close_angle = close_angle
        self.reset_angle = reset_angle

        self.pwm = PWM(Pin(pin))
        self.pwm.freq(freq)
        self.set_angle(reset_angle)

    def _angle_to_duty(self, angle):
        duty = int(self.min_duty + (angle / 180.0) * (self.max_duty - self.min_duty))
        duty = max(self.min_duty, min(self.max_duty, duty))
        return duty

    def set_angle(self, angle):
        if not (0 <= angle <= 180):
            raise ValueError("角度必须在 0~180 之间")
        duty = self._angle_to_duty(angle)
        self.pwm.duty_u16(duty)
        print(f"[舵机] 设置角度: {angle}°, 占空比: {duty}")
        return angle

    def open(self):
        self.set_angle(self.open_angle)
        time.sleep(1)
        self.set_angle(self.reset_angle)
        return f"灯光已开启，角度: {self.open_angle}°"

    def close(self):
        self.set_angle(self.close_angle)
        time.sleep(1)
        self.set_angle(self.reset_angle)
        return f"灯光已关闭，角度: {self.close_angle}°"

    def reset(self):
        self.set_angle(self.reset_angle)
        return f"舵机已复位，角度: {self.reset_angle}°"

    def light_control(self, action):
        if action == "on":
            return self.open()
        elif action == "off":
            return self.close()
        elif action == "reset":
            return self.reset()
        else:
            return f"无效动作: {action}"