# Launch file for the application

from rotary_irq_rp2 import RotaryIRQ
from machine import Pin
import RGB1602
import time

print("Starting up")


class V21:
    
    
    def __init__(self):
        # We work like a state machine.
        # actions changes the state
        # changes in state are reflected in the display and lamp
        self.state = {
            "mode"  : "Burn", # the mode we are in: Expose | Burn | Test | Focus | Run
            "base"  : 0.0,     # the basic exposure in seconds - defaults to a useful number
            "stops" : 1.0,      # number of stops over or under the base we are set for a main exposure
            "burn"  : 0.1,      # the number of stops over the base exposure that is set for the next burn
            "steps" : 7,        # the number of steps in a test strip 
            "interval" : 0.5,   # the size of a step in a test strip
            "steps_mod": False, # whether we are changing the steps or interval
            "step"  : 0,        # the step that we are currently on
            "ref"   : 0.0,       # illumination value stored for comparison
            "sample": 0.0       # current illumination value
        }
        
        # we only update the display when the state has changed.
        self.display_state = self.state.copy()
        self.state["base"] = 16.0 # setting initial base here will trigger display update
        self.state["mode"] = "Expose"
        self.state["stops"] = 0.0
        
        # we need the LCD screen and it needs to be red
        self.lcd=RGB1602.RGB1602(16,2)
        self.lcd.setRGB(255,0,0);
        
        # put up a welcome message for a couple of seconds
        self.lcd.clear()
        self.lcd.setCursor(0, 0)
        self.lcd.printout("  V21 Enlarger  ")
        self.lcd.setCursor(0,1)
        self.lcd.printout("     Timer     ")
        time.sleep(1)
        
        # we need a rotary encode to turn
        self.encoder = RotaryIRQ(
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
        self.encoder.reset() # set the value to start at 0
        self.encoder_old_value = self.encoder.value() # so we can see if it changes
        
        # we need some buttons
        self.debounce_time=0
        self.mode_btn = Pin(10, Pin.IN, Pin.PULL_UP)
        self.set_btn = Pin(1, Pin.IN, Pin.PULL_UP)
        self.focus_btn = Pin(17, Pin.IN, Pin.PULL_UP)
        self.run_btn = Pin(16, Pin.IN, Pin.PULL_UP)
        

    # called in the main loop
    def poll_encoder(self):
        val_new = self.encoder.value()
        if self.encoder_old_value != val_new:
            if self.state["mode"] == "Burn":
                self.state["burn"] = self.state["burn"] + ( (val_new - self.encoder_old_value)* 0.1 )
                if self.state["burn"] < 0.1: self.state["burn"] = 0.1 # never below 0.1 
                self.state["burn"] = round(self.state["burn"], 1)
            elif self.state["mode"] == "Test":
                if self.state["steps_mod"]:
                    # we are changing the number of steps
                    if val_new > self.encoder_old_value:
                        # increasing number of steps
                        self.state["steps"] = self.state["steps"] + 2
                        if self.state["steps"] > 15: self.state["steps"] = 21
                    else:
                        # decreasing number of steps
                        self.state["steps"] = self.state["steps"] - 2
                        if self.state["steps"] < 3: self.state["steps"] = 3
                else:
                    # we are changing the interval
                    self.state["interval"] = self.state["interval"] + ( (val_new - self.encoder_old_value)* 0.1 )
                    if self.state["interval"] < 0.1: self.state["interval"] = 0.1 # never below 0.1
                    self.state["interval"] = round(self.state["interval"], 1)
            else:
                # just update the stops
                self.state["stops"] = val_new * 0.1
                
            # save so we can check again
            self.encoder_old_value = val_new

    # all important function to calculate the EXPOSE value from
    # the base and stops variables
    def get_exposure_duration(self):
        return self.state["base"] * pow(2, self.state["stops"])

    # all important function to calculate the BURN value from
    # the base and stops variables
    def get_burn_duration(self):
        return (self.state["base"] * pow(2, self.state["burn"])) - self.state["base"]
    
    def get_step_duration(self):
        
        # this is worked out heuristically
        # a better mathmetician would do it differently
        
        target_exposures = list();
        steps_either_side = (self.state['steps']-1) / 2
        
        # work from the right
        for i in range(steps_either_side):            
            stripe = (steps_either_side - i) * -1
            stops_off = stripe  * self.state["interval"]
            duration = self.state["base"] * pow(2, stops_off)
            target_exposures.append(duration)
            
        # add the base exposure in the middle
        target_exposures.append(self.state["base"])
        
        for i in range(steps_either_side):
            stripe = i+1
            stops_off = stripe * self.state["interval"]
            duration = self.state["base"] * pow(2, stops_off)
            target_exposures.append(duration)
        
        # now take them away so they are additive.
        additional_exposures = list();
        for i in range(len(target_exposures)):
            duration = target_exposures[i]
            duration = duration - sum(additional_exposures)    
            additional_exposures.append(duration)
            
        return additional_exposures[self.state['step']]


    def mode_btn_pressed(self):
        if self.state["mode"] == "Expose":
            self.state["mode"] = "Burn"
        elif self.state["mode"] == "Burn":
            self.state["mode"] = "Test"
        elif self.state["mode"] == "Test":
            self.state["mode"] = "Expose"
        else:
            pass # do nothing if we are in Focus, Run or Pause


    def set_btn_pressed(self):
        if self.state["mode"] == "Expose":
            self.state["base"] = self.get_exposure_duration() # the base becomes the calcuated duration
            self.state["stops"] = 0.0 # and we are now at the base so zero the stops
        elif self.state["mode"] == "Burn":
            self.state["burn"] = 0.1 # convenience reset
        elif self.state["mode"] == "Test":
            # toggle between changing the steps and step
            self.state["steps_mod"] = not self.state["steps_mod"]
        else:
            pass # do nothing if we are in Run or Pause


    def focus_btn_pressed(self):
        if self.state["mode"] == "Expose":
            self.state["mode"] = "Focus" # turn on focus
        elif self.state["mode"] == "Burn":
            self.state["mode"] = "Focus" # turn on focus
        elif self.state["mode"] == "Test":
            self.state["mode"] = "Focus" # turn on focus
            self.state["step"] = 0 # cancel the running test sequence
            pass
        elif self.state["mode"] == "Focus":
            self.state["mode"] = "Expose" # turn off focus
            pass
        elif self.state["mode"] == "Run":
            self.state["mode"] = "Expose" # cancel a running exposure
            self.state["step"] = 0 # and cancel the current test sequence if any
            pass
        elif self.state["mode"] == "Pause":
            self.state["mode"] = "Expose" # cancel a paused exposure
            pass
        else:
            pass # do nothing if we whatever...


    def run_btn_pressed(self):
        # start a run
        # increment test step if we are in test mode or step is already > 0
        # pause a run
        
        pass

    # called in the main loop
    def poll_buttons(self):
        
        if ((self.mode_btn.value() is 0) and (time.ticks_ms()-self.debounce_time) > 300):
            self.debounce_time=time.ticks_ms()
            self.mode_btn_pressed()
        
        if ((self.set_btn.value() is 0) and (time.ticks_ms()-self.debounce_time) > 300):
            self.debounce_time=time.ticks_ms()
            self.set_btn_pressed()

        if ((self.focus_btn.value() is 0) and (time.ticks_ms()-self.debounce_time) > 300):
            self.debounce_time=time.ticks_ms()
            self.focus_button_pressed()

        if ((self.run_btn.value() is 0) and (time.ticks_ms()-self.debounce_time) > 300):
            self.debounce_time=time.ticks_ms()
            self.run_btn_pressed()

    def poll_sensor(self):
        pass


    def update_display(self):
    
            
        #    Only update portion of display that has changed.
        #    |----------|-999.9s|
        #    |-----------|-+9.9 |
        #    Top left (0,0) is max 10 digits
        #    Bottom left (0,1) is max 11 digits

        # do nothing if the state hasn't changed
        if self.display_state == self.state:
            return
        
        # something has changes
        
        if self.state["mode"] == "Expose":
            
            # title
            self.lcd.setCursor(0, 0)
            self.lcd.printout('Expose    ')

            # duration
            duration = self.get_exposure_duration();
            duration = round(duration, 1)
            secs = f"{duration}s";
            self.lcd.setCursor(10, 0)
            self.lcd.printout(f"{secs: >6}")
            
            # base
            base = self.state['base']
            base = round(base, 1)
            secs = f"{base}s";
            self.lcd.setCursor(0, 1)
            self.lcd.printout(f"{secs: <10}")
            
            # stops
            if self.state["stops"] > 0:           
                stops = f"+{self.state["stops"]} " # + added for clarity
            else:
                stops = f"{self.state["stops"]} "
            self.lcd.setCursor(10, 1)
            self.lcd.printout(f"{stops: >6}")

            
        elif self.state["mode"] == "Burn":
            
            # title
            self.lcd.setCursor(0, 0)
            self.lcd.printout('Burn      ')

            # duration
            duration = self.get_burn_duration();
            duration = round(duration, 1)
            secs = f"{duration}s";
            self.lcd.setCursor(10, 0)
            self.lcd.printout(f"{secs: >6}")
            
            # base
            base = self.state['base']
            base = round(base, 1)
            secs = f"{base}s";
            self.lcd.setCursor(0, 1)
            self.lcd.printout(f"{secs: <10}")
            
            # stops to burn - always positive
            burn = f"+{self.state['burn']} "
            self.lcd.setCursor(10, 1)
            self.lcd.printout(f"{burn: >6}")
            
        elif self.state["mode"] == "Test":
            
            # title
            self.lcd.setCursor(0, 0)
            self.lcd.printout('Test      ')
            
            # duration
            duration = self.get_step_duration();
            duration = round(duration, 1)
            secs = f"{duration}s";
            self.lcd.setCursor(10, 0)
            self.lcd.printout(f"{secs: >6}")
            
            # steps (where base would go)
            steps = self.state['steps']
            if self.state["steps_mod"]: steps = f"{steps:} <-" # signify changeable 
            self.lcd.setCursor(0, 1)
            self.lcd.printout(f"{self.state['step']}/{steps: <8}")
            
            interval = self.state["interval"]
            interval = f"+{interval:} "
            if not self.state["steps_mod"]: interval = f"-> {interval:}" # signify changeable
            self.lcd.setCursor(8, 1)
            self.lcd.printout(f"{interval: >8}")
            
        else:
            pass
        
        # keep a copy to see if it changes next tim
        self.display_state = self.state.copy()
         
    def update_lamp(self):
        pass

    
# Do the business
v21_timer = V21()

# The main loop of the programme
while(True):
    v21_timer.poll_encoder()
    v21_timer.poll_buttons()
    v21_timer.poll_sensor()
    v21_timer.update_display()
    v21_timer.update_lamp()
    
    
