# Launch file for the application

import RGB1602
import time

# we need the LCD screen and it needs to be red
lcd=RGB1602.RGB1602(16,2)
lcd.setRGB(255,0,0);

# We work like a state machine.
# actions changes the state
# changes in state are reflected in the display and lamp
state = {
    "mode"  : "Expose", # the mode we are in: Expose | Burn | Test | Focus | Run
    "base"  : 12.0,     # the basic exposure in seconds - defaults to a useful number
    "stops" : 0.0,      # number of stops over or under the base we are set for a main exposure
    "burn"  : 0.0,      # the number of stops over the base exposure that is set for the next burn
    "steps" : 7,        # the number of steps in a test strip 
    "step"  : 0,        # the step that we are currently on
    "ref"   : 0.0       # illumination value stored for comparison
    "sample": 0.0       # current illumination value
}


def display(mode, duration, base, stops):

    # refresh the whole thing
    lcd.clear()

    # mode is top left
    lcd.setCursor(0, 0)
    lcd.printout(mode)

    # duration is top right aligned
    d_as_string = f'{duration:.1f}s'
    lcd.setCursor(16 - len(d_as_string), 0 )
    lcd.printout(d_as_string)

    # base it bottom left
    b_as_string = f'{base:.1f}s'
    lcd.setCursor(0, 1)
    lcd.printout(b_as_string)
    
    # stops is bottom right aligned
    if stops >= 0:    
        s_as_string = f'+{stops:.1f} '
    else:
        s_as_string = f'{stops:.1f} '
    lcd.setCursor(16 - len(s_as_string), 1 )
    lcd.printout(s_as_string)
    



display("Expose", 33.0, 21, -7);
time.sleep(2)
display("Burn", 2.0, 21, 1);
time.sleep(2)
display("Test", 2.0, 21, 1);
    
    
