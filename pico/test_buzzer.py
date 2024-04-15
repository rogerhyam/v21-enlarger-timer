# check the buzzer works

from machine import Pin
from machine import PWM
import time

buzzer = PWM(Pin(13, Pin.OUT), freq=200, duty_u16=32000)
time.sleep(0.5)
buzzer.freq(130)
time.sleep(0.5)
buzzer.deinit()

