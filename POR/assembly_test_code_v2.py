#!/usr/bin/env python3
# COMPLETE ROBOT ASSEMBLY - Motors + Sensors + LCD Boot + Switch Control
# Integrates: motor_flash_v2.ino serial, range_sensor_test.py, IMU_test.py, control_motor.py
# LCD: POWER ON → READY (after checks) → Batt % (2,1) → OPERATING (Switch active)
# Flash Arduino with motor_flash_v2.ino first!

import time
import serial
import serial.tools.list_ports
import pygame
import sys
import subprocess  # For potential Arduino monitor
from gpiozero import OutputDevice, DistanceSensor
from gpiozero import exc as gpiozero_exc

try:
    import mpu6050
    IMU_AVAILABLE = True
except ImportError:
    IMU_AVAILABLE = False
    print("mpu6050 missing - IMU disabled (pip3 install mpu6050-raspberrypi)")

# LCD PINS (BCM) - R/W→GND, VO→1kΩ→GND required
RS = OutputDevice(27)
E  = OutputDevice(22)
D4 = OutputDevice(25)
D5 = OutputDevice(24)
D6 = OutputDevice(23)
D7 = OutputDevice(18)  # D6=23 conflicts w/ TRIG? Move sensor if needed

# Sensors
TRIG = 26  
ECHO = 16
sensor = DistanceSensor(trigger=TRIG, echo=ECHO, max_distance=4)


# Serial/Motor config from control_motor.py
BAUD = 115200
DEADZONE = 0.12
MAXPWM = 255
RAMPPERSEC = 900
FAILSAFETIMEOUT = 1000 # Emergency stop timer if PI loses connection
ZRBUTTON = 7  # Switch Pro ZR
STOPBUTTON = 1
M3SPEED = 255
M3DEADZONESTICK = 0.15 # Conveyor runs on ZR stick push
LEFTYAXIS = 1
RIGHTYAXIS = 3

# IMU Flat Thresholds (|Ax/Ay|<0.15g, Az~1g ±0.1)
TILT_THRESH = 0.15; Z_FLAT_MIN = 0.9; Z_FLAT_MAX = 1.1

def delay_ms(t): time.sleep(t/1000)
def delay_us(t): time.sleep(t/1e6)

def pulse_enable():
    E.off(); delay_us(1)
    E.on();  delay_us(1)
    E.off(); delay_us(1)

def lcd_write_nib(data, rs_bit):
    RS.value = rs_bit
    D4.value = bool(data & 0x01)
    D5.value = bool(data & 0x02)
    D6.value = bool(data & 0x04)
    D7.value = bool(data & 0x08)
    pulse_enable()

def lcd_write_byte(data, rs_bit):
    lcd_write_nib(data >> 4, rs_bit)
    lcd_write_nib(data & 0x0F, rs_bit)

def lcd_cmd(cmd): lcd_write_byte(cmd, 0)
def lcd_data(char): lcd_write_byte(ord(char), 1)

def lcd_clear(): lcd_cmd(0x01); delay_ms(2)
def lcd_home(): lcd_cmd(0x02); delay_ms(2)
def lcd_print(text, row=0, col=0):
    lcd_cmd(0x80 + (0x40 * row) + col)
    for char in text[:16]:  # Max 16 chars/line
        lcd_data(char)

# Find Arduino serial port
def find_arduino_port():
    for port in serial.tools.list_ports.comports():
        if 'Arduino' in port.description or 'ACM' in port.device:
            return port.device
    raise RuntimeError("No Arduino serial port found! Check USB connection.")

# LCD Init
def init_lcd():
    time.sleep(0.05)
    lcd_cmd(0x02); time.sleep(0x005)  # 4-bit
    for cmd in [0x28, 0x0C, 0x06, 0x01]:
        lcd_cmd(cmd); time.sleep(0x005)

# Main ramp/send from control_motor.py
def clamp(x, lo, hi): return max(lo, min(hi, x))
def apply_deadzone(x, dz): return 0 if abs(x) < dz else x
def axis_to_pwm(axis_val):
    v = apply_deadzone(axis_val, DEADZONE)
    return int(clamp(v, -1.0, 1.0) * MAXPWM)

def ramp(current, target, dt, rate):
    step = rate * dt
    if target > current: return min(target, current + step)
    return max(target, current - step)

# Boot sequence
init_lcd()
lcd_print(" POWER ON", 0, 1)
print("System powering on...")
time.sleep(2)

# Component checks
ser = None
controller_ok = False
controller_enabled = False

try:
    port = find_arduino_port()
    ser = serial.Serial(port, BAUD, timeout=0.05)
    time.sleep(2)  # Arduino reset
    ser.reset_input_buffer()
    print(f"Arduino on {port}")
    lcd_print(" Motors OK", 1, 1)
    time.sleep(1)
except:
    print("Arduino/Motors FAIL - Check USB")
    lcd_print(" Motors FAIL", 1, 1)

# Sensors
try:
    dist = sensor.distance * 100
    print(f"Range OK: {dist:.1f}cm")
    lcd_print(" Sensors OK", 1, 1)
    time.sleep(1)
except:
    print("Range FAIL")
    lcd_print(" Sensors FAIL", 1, 1)

if IMU_AVAILABLE:
    try:
        mpu6050 = mpu6050.mpu6050(0x68)
        print("IMU OK")
        lcd_print(" IMU OK    ", 1, 1)
        time.sleep(1)
    except:
        print("IMU FAIL")
        lcd_print(" IMU FAIL  ", 1, 1)

# Switch init
pygame.init()
pygame.joystick.init()
if pygame.joystick.get_count() == 0:
    print("No Switch controller - plug in USB")
else:
    print("Controller OK")
    lcd_print(" CONTROLLER OK ", 1, 1)
    time.sleep(1)
joy = None

lcd_clear()
print("System ready!")
lcd_print(" DEVICE READY", 0, 1)

# Main loop
cur1 = cur2 = cur3 = 0.0
last_sent1 = last_sent2 = last_sent3 = None
operating = False
tprev = time.time()
last_input = time.time()

try:
    while True:
        now = time.time()
        dt = now - tprev
        tprev = now

        # Controller
        pygame.event.pump()
        if pygame.joystick.get_count() > 0:
            if joy is None:
                joy = pygame.joystick.Joystick(0)
                joy.init()
            ly = joy.get_axis(LEFTYAXIS)
            ry = joy.get_axis(RIGHTYAXIS)
            zr = joy.get_button(ZRBUTTON)

            tgt1 = axis_to_pwm(ly)
            tgt2 = axis_to_pwm(ry)
            tgt3 = 0
            if zr:
                if ly > M3DEADZONESTICK and ry > M3DEADZONESTICK:
                    tgt3 = -M3SPEED  # Forward
                elif ly < -M3DEADZONESTICK and ry < -M3DEADZONESTICK:
                    tgt3 = M3SPEED  # Reverse

            if abs(ly) > 0.01 or abs(ry) > 0.01 or tgt3 != 0:
                last_input = now
                lcd_print(" OPERATING", 1, 1)

            if joy.get_button(STOPBUTTON):
                tgt1 = tgt2 = tgt3 = 0
        
            cur1 = ramp(cur1, float(tgt1), dt, RAMPPERSEC)
            cur2 = ramp(cur2, float(tgt2), dt, RAMPPERSEC)
            cur3 = ramp(cur3, float(tgt3), dt, RAMPPERSEC)

            # Send serial if changed (50Hz)
            if now % 0.02 < dt:
                m1 = int(round(cur1))
                m2 = int(round(cur2))
                m3 = int(round(cur3))
                if ser and m1 != last_sent1:
                    ser.write(f"M1 {m1}\n".encode())
                    last_sent1 = m1
                if ser and m2 != last_sent2:
                    ser.write(f"M2 {m2}\n".encode())
                    last_sent2 = m2
                if ser and m3 != last_sent3:
                    ser.write(f"M3 {m3}\n".encode())
                    last_sent3 = m3
         
        #    if not operating:
        #        lcd_print("OPERATING", 0, 0)
        #        operating = True
        #else
        #    if operating:
        #       lcd_print("SYSTEM READY", 0, 0)
        #       operating = False

        # Failsafe
        if now - last_input > FAILSAFETIMEOUT:
            cur1 = cur2 = cur3 = 0
            lcd_print(" SHUT DOWN ", 0, 0)

        # Live sensor print (optional LCD update)
        if IMU_AVAILABLE and mpu6050:
            accel = mpu6050.get_accel_data()
            print(f"IMU: {accel}, Dist: {sensor.distance*100:.1f}cm")
        time.sleep(0.5)

except KeyboardInterrupt:
    print("Shutting down...")
finally:
    # Safe LCD shutdown (ignore if closed)
    try:
        lcd_print(" POWER OFF ", 0, 0)
        lcd_clear()
    except gpiozero_exc.GPIODeviceClosed:
        print("LCD already closed - OK")
    
    # Serial safe
    if 'ser' in locals() and ser and ser.is_open:
        ser.write(b"STOP\n")
        ser.close()
    
    pygame.quit()
    
    # Pin closes (idempotent)
    for pin in [RS, E, D4, D5, D6, D7]:
        try:
            pin.close()
        except gpiozero_exc.GPIODeviceClosed:
            pass  # Harmless
    
    print("System stopped safely.")

''''
except KeyboardInterrupt:
    print("Shutting down...")
    lcd_print(" POWER OFF" , 0, 0)
finally:
    lcd_clear()
    if ser:
        ser.write(b"STOP\n")
        ser.close()
    pygame.quit()
    RS.close(); E.close(); D4.close(); D5.close(); D6.close(); D7.close()
    print("System - all stopped.")
    lcd_print(" POWER OFF", 0, 0)
'''''