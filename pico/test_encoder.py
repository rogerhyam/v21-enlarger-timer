
# https://www.upesy.com/blogs/tutorials/rotary-encoder-raspberry-pi-pico-on-micro-python
# https://github.com/miketeachman/micropython-rotary

import RGB1602
import time
from rotary_irq_rp2 import RotaryIRQ
from machine import Pin

lcd=RGB1602.RGB1602(16,2)
lcd.clear()

lcd.setRGB(0,255,0);
lcd.setCursor(0, 0)
lcd.printout("  Encoder Test  ")

lcd.setCursor(0,1)
lcd.printout("numbers..d.")

r = RotaryIRQ(
    pin_num_clk=8,
    pin_num_dt=9,
    reverse=True,
    incr=1,
    range_mode=RotaryIRQ.RANGE_BOUNDED,
    pull_up=True,
    half_step=False,
    min_val=-99,
    max_val=99
)

# set the value to start at 0
r.reset()

val_old = r.value()
while True:
    val_new = r.value()

    if val_old != val_new:
        val_old = val_new
        print("step =", val_new)
        lcd.clear()
        lcd.setCursor(0,0)
        lcd.printout(f'Encoder: {val_new}   ')
        lcd.setCursor(0,1)
        stop = val_new * 0.1
        lcd.printout(f'Stop: {stop}   ')
    time.sleep_ms(10)
