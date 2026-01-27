from gpiozero import DistanceSensor
import time

TRIG = 23 # (GPIO Pin 23)
ECHO = 24 # (GPIO Pin 24)

sensor = DistanceSensor (trigger=TRIG, echo=ECHO)

print("Distance Measurement in Progress")
print("Waiting For Sensor to Settle")
time.sleep(2)

try:
    while True:
        distance_cm = sensor.distance * 100;
        distance = round(distance_cm, 2)

        print ("Distance", distance, "cm")

        time.sleep(0.5)
except KeyboardInterrupt:
    print("\nMeasurement stopped by user.")
