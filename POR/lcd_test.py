from gpiozero import OutputDevice
import time


RS = OutputDevice(27)
E  = OutputDevice(22)
D4 = OutputDevice(25)
D5 = OutputDevice(24)
D6 = OutputDevice(23)
D7 = OutputDevice(18)

print("Toggle test - watch multimeter or LED on GPIO27/22 etc")

for i in range(20):
    RS.on(); time.sleep(0.2); RS.off(); time.sleep(0.2)
    E.on(); time.sleep(0.2); E.off(); time.sleep(0.2)
    print(f"Toggle {i}")
    