#!/usr/bin/env python3
import RPi.GPIO as GPIO
import time

# GPIO pin definitions (BCM numbering, adjust if needed)
RS = 27   # Register Select
E  = 22   # Enable
D4 = 25   # Data bit 4
D5 = 24   # Data bit 5
D6 = 23   # Data bit 6
D7 = 18   # Data bit 7

# Setup GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup([RS, E, D4, D5, D6, D7], GPIO.OUT)

def delay_ms(tms):
    time.sleep(tms / 1000.0)

def delay_us(tus):
    time.sleep(tus / 1000000.0)

def pulse_enable():
    GPIO.output(E, GPIO.LOW)
    delay_us(1)
    GPIO.output(E, GPIO.HIGH)
    delay_us(1)
    GPIO.output(E, GPIO.LOW)
    delay_us(100)  # Command settle time

def send_nibble(data_high, rs):
    # High nibble only (4-bit mode)
    GPIO.output(RS, rs)
    GPIO.output(D4, (data_high >> 4) & 1)
    GPIO.output(D5, (data_high >> 5) & 1)
    GPIO.output(D6, (data_high >> 6) & 1)
    GPIO.output(D7, (data_high >> 7) & 1)
    pulse_enable()
    delay_us(50)

def send_byte(data, rs):
    send_nibble(data, rs)      # High nibble
    send_nibble(data << 4, rs) # Low nibble
    delay_ms(2)

def lcd_init():
    delay_ms(50)  # Power up delay
    # Init sequence (4-bit mode)
    GPIO.output(RS, GPIO.LOW)
    send_nibble(0x03, GPIO.LOW)
    delay_ms(5)
    send_nibble(0x03, GPIO.LOW)
    delay_us(150)
    send_nibble(0x03, GPIO.LOW)
    delay_us(150)
    send_nibble(0x02, GPIO.LOW)  # Set 4-bit
    delay_us(150)
    send_byte(0x28, GPIO.LOW)  # 4-bit, 2 lines, 5x8 font
    send_byte(0x0C, GPIO.LOW)  # Display on, cursor off
    send_byte(0x06, GPIO.LOW)  # Entry mode: increment, no shift
    send_byte(0x01, GPIO.LOW)  # Clear

def lcd_clear():
    send_byte(0x01, GPIO.LOW)
    delay_ms(2)

def lcd_set_cursor(col, row):
    addr = 0x80 + (0x40 * row) + col
    send_byte(addr, GPIO.LOW)

def lcd_write_text(text):
    for char in text:
        send_byte(ord(char), GPIO.HIGH)

# Example usage
if __name__ == '__main__':
    lcd_init()
    lcd_clear()
    lcd_set_cursor(0, 0)
    lcd_write_text("Hello World!")
    lcd_set_cursor(0, 1)
    lcd_write_text("RPi LCD 1602A")
    time.sleep(5)
    lcd_clear()
    GPIO.cleanup()
