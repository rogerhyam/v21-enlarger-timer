#
# Run this file to test the LCD is working
#

import RGB1602
import time

lcd=RGB1602.RGB1602(16,2)

lcd.setRGB(255,0,0);
lcd.setCursor(0, 0)
lcd.printout("  V21 Enlarger  ")
lcd.setCursor(0,1)
lcd.printout("     Timer     ")

time.sleep(1)

lcd.clear()

lcd.setCursor(0, 0)
lcd.printout("Mode")