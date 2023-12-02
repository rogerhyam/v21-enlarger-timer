# https://electrocredible.com/raspberry-pi-pico-external-interrupts-button-micropython/


from machine import Pin
import time

debounce_time=0


set_btn = Pin(1, Pin.IN, Pin.PULL_UP)
mode_btn = Pin(10, Pin.IN, Pin.PULL_UP)
focus_btn = Pin(17, Pin.IN, Pin.PULL_UP)
run_btn = Pin(16, Pin.IN, Pin.PULL_UP)

print("starting up")

while True:

    if ((mode_btn.value() is 0) and (time.ticks_ms()-debounce_time) > 300):
        debounce_time=time.ticks_ms()
        print("Mode Pressed")
    
    if ((set_btn.value() is 0) and (time.ticks_ms()-debounce_time) > 300):
        debounce_time=time.ticks_ms()
        print("Set Pressed")

    if ((focus_btn.value() is 0) and (time.ticks_ms()-debounce_time) > 300):
        debounce_time=time.ticks_ms()
        print("Focus Pressed")

    if ((run_btn.value() is 0) and (time.ticks_ms()-debounce_time) > 300):
        debounce_time=time.ticks_ms()
        print("Exposed Pressed")