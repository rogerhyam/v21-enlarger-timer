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
            "mode_prev": None, # used to hold a previous state when we slip into Focus or Run
            "run_duration" : 0, # total milliseconds for this exposure
            "run_remaining" : 0, # time  milliseconds left of this exposure
            "run_remaining_sec" : 0, # the time in seconds (used for triggering display update)
            "run_start" : 0, # start milliseconds (ticks) time of this segment of exposure - resets if we pause
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
            elif self.state["mode"] == "Test" and self.state["step"] == 0:
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
        elif self.state["mode"] == "Test" and self.state["step"] == 0:
            # toggle between changing the steps and step
            self.state["steps_mod"] = not self.state["steps_mod"]
        elif self.state["mode"] == "Test" and self.state["step"] > 0:
            # once we are running a sequence then this button cancels 
            self.state["step"] = 0
        else:
            pass # do nothing if we are in Run or Pause


    def focus_btn_pressed(self):
        
        if self.state["mode"] == "Focus":
            # we are already focussing so turn it off
            self.state["mode"] = self.state["mode_prev"]
        elif self.state["mode"] == "Run" or self.state["mode"] == "Paused":
            # we are running and this is the cancel button
            self.state["mode"] = self.state["mode_prev"]
            self.state["step"] = 0 # and cancel the current test sequence if any
        elif self.state["mode"] == "Test" and self.state["step"] > 0:
            self.state["step"] = 0
        else:
            # we are in some other mode and so switching over to focus
            self.state["mode_prev"] = self.state["mode"]
            self.state["mode"] = "Focus"


    def run_btn_pressed(self):
        
        if self.state["mode"] == "Run":
            # we are already running so pause
            self.state["mode"] = "Paused"
        elif self.state["mode"] == "Paused":
            self.state["mode"] = "Run"
            self.state["run_start"] = time.ticks_ms()
        elif self.state["mode"] == "Expose":
            # making a regular exposure
            print(self.state)
            self.state["mode"] = "Run"
            self.state["mode_prev"] = "Expose" # so we can go back afterwards
            self.state["run_start"] = time.ticks_ms()
            self.state["run_duration"] = self.get_exposure_duration() * 1000
            self.state["run_remaining"] = self.state["run_duration"]
            self.state['run_remaining_sec'] = round(self.get_exposure_duration(), 1)
            print(self.state)
            
        elif self.state["mode"] == "Burn":
            # burning stops
            self.state["mode"] = "Run"
            self.state["mode_prev"] = "Burn" # so we can go back afterwards
            self.state["run_start"] = time.ticks_ms()
            self.state["run_duration"] = self.get_burn_duration() * 1000
            self.state["run_remaining"] = self.state["run_duration"]
            self.state['run_remaining_sec'] = round(self.get_burn_duration(), 1)
            
        elif self.state["mode"] == "Test":
            # run one of the test steps
            self.state["mode"] = "Run"
            self.state["mode_prev"] = "Test" # so we can go back afterwards
            self.state["run_start"] = time.ticks_ms()
            self.state["run_duration"] = self.get_step_duration() * 1000
            self.state["run_remaining"] = self.state["run_duration"]
            self.state['run_remaining_sec'] = round(self.get_step_duration(), 1)
            self.state["step"] = self.state["step"] + 1

        else:
            pass # do nothing when in focus mode
        
            
            

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
            self.focus_btn_pressed()

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
            if self.state["steps_mod"] and self.state["step"] == 0: steps = f"{steps:} <-" # signify changeable 
            self.lcd.setCursor(0, 1)
            self.lcd.printout(f"{self.state['step']}/{steps: <8}")
            
            interval = self.state["interval"]
            interval = f"+{interval:} "
            if not self.state["steps_mod"] and self.state["step"] == 0 : interval = f"-> {interval:}" # signify changeable
            self.lcd.setCursor(8, 1)
            self.lcd.printout(f"{interval: >8}")
        
        elif self.state["mode"] == "Focus":
            self.lcd.clear()
            self.lcd.setCursor(0, 0)
            self.lcd.printout('   - FOCUS -   ')

        elif self.state["mode"] == "Run":
            
            # we only update the display if there has
            # been a significant change in the time remaining
            if self.display_state['run_remaining_sec'] != self.state['run_remaining_sec'] or self.display_state["mode"] != "Run":    
                self.lcd.clear()
                self.lcd.setCursor(5, 0)
                self.lcd.printout(f"{self.state['run_remaining_sec']}s")

                bars = round(16 * self.state['run_remaining'] / self.state['run_duration'])
                bars = '=' * bars;
                self.lcd.setCursor(0, 1)
                self.lcd.printout(bars)

        elif self.state["mode"] == "Paused":
            self.lcd.clear()
            self.lcd.setCursor(5, 0)
            self.lcd.printout(f"{self.state['run_remaining_sec']}s")
            self.lcd.setCursor(4,1)
            self.lcd.printout("Paused")

        else:
            pass
        
        # keep a copy to see if it changes next tim
        self.display_state = self.state.copy()
         
    def update_lamp(self):
        pass
    
    def update_timer(self):
        if self.state["mode"] == "Run":
            
            now = time.ticks_ms()
            remaining = self.state['run_remaining'] - time.ticks_diff(now, self.state["run_start"])
            
            if remaining <= 0:
                self.state["mode"] = self.state["mode_prev"]
                if self.state["mode"] == "Test" and self.state["step"] == self.state["steps"]:
                    self.state["step"] = 0
                    
            else:
                self.state['run_remaining'] = remaining
                self.state['run_remaining_sec'] = round(remaining / 1000, 1)
                self.state["run_start"] = now
                
                

    
# Do the business
v21_timer = V21()

# The main loop of the programme
while(True):
    v21_timer.poll_encoder()
    v21_timer.poll_buttons()
    v21_timer.poll_sensor()
    v21_timer.update_display()
    v21_timer.update_lamp()
    v21_timer.update_timer()
    
    
