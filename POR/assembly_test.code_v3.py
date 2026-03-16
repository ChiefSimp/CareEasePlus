#!/usr/bin/env python3
# COMPLETE ROBOT ASSEMBLY - Motors + Sensors + LCD Boot + Switch Control

import time
import serial
import serial.tools.list_ports
import pygame
import sys
import subprocess
from gpiozero import OutputDevice, DistanceSensor
from gpiozero import exc as gpiozero_exc

try:
    import mpu6050 as mpu6050_lib
    IMU_AVAILABLE = True
except ImportError:
    IMU_AVAILABLE = False
    mpu6050_lib = None
    print("mpu6050 missing - IMU disabled (pip3 install mpu6050-raspberrypi)")

mpu = None  # IMU instance (set later)

# LCD PINS (BCM)
RS = OutputDevice(27)
E  = OutputDevice(22)
D4 = OutputDevice(25)
D5 = OutputDevice(24)
D6 = OutputDevice(23)
D7 = OutputDevice(18)

# Sensors
TRIG = 26
ECHO = 16
sensor = DistanceSensor(trigger=TRIG, echo=ECHO, max_distance=4)

# Serial/Motor config
BAUD = 115200
DEADZONE = 0.08
MAXPWM = 255
RAMPPERSEC = 900
FAILSAFETIMEOUT = 0.8

# NOTE: These indexes may differ for DualSense vs Switch Pro.
ZRBUTTON = 7
STOPBUTTON = 1
M3SPEED = 255
M3DEADZONESTICK = 0.15
LEFTYAXIS = 1
RIGHTYAXIS = 4
dist_offset_cm = 0.0

# IMU Flat Thresholds
TILT_THRESH = 2
Z_FLAT_MIN = -15
Z_FLAT_MAX = -8


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
    for char in text[:16]:
        lcd_data(char)

def find_arduino_port():
    for port in serial.tools.list_ports.comports():
        if 'Arduino' in port.description or 'ACM' in port.device:
            return port.device
    raise RuntimeError("No Arduino serial port found! Check USB connection.")

def init_lcd():
    time.sleep(0.05)
    lcd_cmd(0x02); time.sleep(0.005)
    for cmd in [0x28, 0x0C, 0x06, 0x01]:
        lcd_cmd(cmd); time.sleep(0.005)

def clamp(x, lo, hi): return max(lo, min(hi, x))
def apply_deadzone(x, dz): return 0 if abs(x) < dz else x

def axis_to_pwm(axis_val):
    v = apply_deadzone(axis_val, DEADZONE)
    return int(clamp(v, -1.0, 1.0) * MAXPWM)

def ramp(current, target, dt, rate):
    step = rate * dt
    if target > current: return min(target, current + step)
    return max(target, current - step)

def is_device_flat():
    if not IMU_AVAILABLE or mpu is None:
        return True
    accel = mpu.get_accel_data()
    ax, ay, az = accel['x'], accel['y'], accel['z']
    return (abs(ax) < TILT_THRESH and abs(ay) < TILT_THRESH and Z_FLAT_MIN <= az <= Z_FLAT_MAX)

def init_ps5_controller():
    """
    Finds a connected DualSense over OS Bluetooth (pairing must be done in the OS).
    """
    pygame.joystick.quit()
    pygame.joystick.init()
    pygame.event.pump()

    if pygame.joystick.get_count() == 0:
        return None

    for i in range(pygame.joystick.get_count()):
        j = pygame.joystick.Joystick(i)
        j.init()
        name = (j.get_name() or "").lower()
        if "wireless controller" in name or "dualsense" in name:
            print(f"PS5 Controller connected: {j.get_name()}")
            return j

    return None


# ---------------- Boot sequence ----------------
init_lcd()
lcd_print(" POWER ON", 0, 1)
print("System powering on...")
time.sleep(2)

ser = None
controller_ok = False
controller_enabled = False

# Motors / Arduino
try:
    port = find_arduino_port()
    ser = serial.Serial(port, BAUD, timeout=0.05)
    time.sleep(2)
    ser.reset_input_buffer()
    print(f"Arduino on {port}")
    lcd_print(" MOTORS OK", 1, 1)
    time.sleep(1)
except Exception as e:
    print(f"Arduino/Motors FAIL - Check USB ({e})")
    lcd_print(" MOTORS FAIL", 1, 1)
    time.sleep(1)

# Sensor + calibration
try:
    dist = sensor.distance * 100
    print(f"Range OK: {dist:.1f}cm")
    time.sleep(1)

    print("HC-SR04 calibrating (keep clear 2s)...")
    lcd_print(" SENSOR CALIB...", 1, 0)
    time.sleep(2)

    samples = 100
    dist_sum = 0.0
    for _ in range(samples):
        dist_sum += sensor.distance * 100
        time.sleep(0.02)

    dist_offset_cm = dist_sum / samples
    print(f"HC-SR04 offset: {dist_offset_cm:.1f}cm (corrected dist = raw - offset)")
    lcd_print(" SENSOR OK      ", 1, 0)
    time.sleep(1)
except Exception as e:
    print(f"Range FAIL ({e})")
    lcd_print(" SENSOR FAIL    ", 1, 0)
    time.sleep(1)

# IMU
if IMU_AVAILABLE:
    try:
        mpu = mpu6050_lib.mpu6050(0x68)
        print("IMU OK")
        flat_status = "FLAT" if is_device_flat() else "TILTED"
        lcd_print(f" IMU {flat_status:<10}", 1, 0)
        time.sleep(1)
    except Exception as e:
        print(f"IMU FAIL ({e})")
        lcd_print(" IMU FAIL       ", 1, 0)
        time.sleep(1)
        mpu = None

# Controller init
pygame.init()
print("Searching for PS5 controller over Bluetooth...")
lcd_print(" SEARCH CTRL     ", 1, 0)

joy = None
timeout = time.time() + 10
while joy is None and time.time() < timeout:
    joy = init_ps5_controller()
    time.sleep(0.5)

if joy:
    controller_ok = True
    lcd_print(" PS5 READY       ", 1, 0)
    print("DualSense READY")
else:
    controller_ok = False
    lcd_print(" NO PS5 FOUND    ", 1, 0)
    print("No PS5 controller detected")
time.sleep(1)

lcd_clear()
print("System ready!")
lcd_print(" DEVICE READY", 0, 1)

# ---------------- Main loop ----------------
cur1 = cur2 = cur3 = 0.0
last_sent1 = last_sent2 = last_sent3 = None
tprev = time.time()
last_input = time.time()

try:
    while True:
        now = time.time()
        dt = now - tprev
        tprev = now

        # Reconnect if controller drops
        if joy is not None and not joy.get_init():
            print("Controller lost — attempting reconnect...")
            joy = None

        if joy is None:
            joy = init_ps5_controller()
            if joy:
                controller_ok = True
                print("Reconnected PS5 controller")

        # IMU safety gate
        if not is_device_flat():
            controller_enabled = False
            lcd_print(" TILTED          ", 1, 0)
            cur1 = cur2 = cur3 = 0.0
            if ser:
                ser.write(b"M1 0\nM2 0\nM3 0\n")
            time.sleep(0.5)
            continue
        else:
            controller_enabled = controller_ok
            lcd_print("                ", 1, 0)

        # Controller read (only if connected)
        if controller_enabled and joy is not None:
            pygame.event.pump()
            ly = joy.get_axis(LEFTYAXIS)
            ry = joy.get_axis(RIGHTYAXIS)
            zr = joy.get_button(ZRBUTTON)

            tgt1 = axis_to_pwm(ly)
            tgt2 = axis_to_pwm(ry)
            tgt3 = 0

            if zr:
                if ly > M3DEADZONESTICK and ry > M3DEADZONESTICK:
                    tgt3 = -M3SPEED
                elif ly < -M3DEADZONESTICK and ry < -M3DEADZONESTICK:
                    tgt3 = M3SPEED

            if abs(ly) > 0.01 or abs(ry) > 0.01 or tgt3 != 0:
                last_input = now
                lcd_print(" OPERATING       ", 0, 0)

            if joy.get_button(STOPBUTTON):
                tgt1 = tgt2 = tgt3 = 0

            cur1 = ramp(cur1, float(tgt1), dt, RAMPPERSEC)
            cur2 = ramp(cur2, float(tgt2), dt, RAMPPERSEC)
            cur3 = ramp(cur3, float(tgt3), dt, RAMPPERSEC)

            # Serial ~50Hz
            if (now % 0.02) < dt and ser:
                m1 = int(round(cur1))
                m2 = int(round(cur2))
                m3 = int(round(cur3))

                if m1 != last_sent1:
                    ser.write(f"M1 {m1}\n".encode("utf-8"))
                    last_sent1 = m1
                if m2 != last_sent2:
                    ser.write(f"M2 {m2}\n".encode("utf-8"))
                    last_sent2 = m2
                if m3 != last_sent3:
                    ser.write(f"M3 {m3}\n".encode("utf-8"))
                    last_sent3 = m3

        # Failsafe
        if now - last_input > FAILSAFETIMEOUT:
            cur1 = cur2 = cur3 = 0

        # Live sensor print
        if IMU_AVAILABLE and mpu is not None:
            accel = mpu.get_accel_data()
            print(f"IMU: {accel}, Dist: {sensor.distance*100:.1f}cm")

        time.sleep(0.5)

except KeyboardInterrupt:
    print("Shutting down...")

finally:
    try:
        lcd_print(" POWER OFF ", 0, 0)
        lcd_clear()
    except gpiozero_exc.GPIODeviceClosed:
        print("LCD already closed - OK")

    if ser and ser.is_open:
        try:
            ser.write(b"STOP\n")
        except Exception:
            pass
        ser.close()

    pygame.quit()

    for pin in [RS, E, D4, D5, D6, D7]:
        try:
            pin.close()
        except gpiozero_exc.GPIODeviceClosed:
            pass

    print("System stopped safely.")