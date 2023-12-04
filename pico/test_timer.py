import time

before = time.ticks_ms()

count = 0;
while True:
    now = time.ticks_ms()
    if now - before > 1000:
        print(count)
        count = count + 1
        before = now
        
        
