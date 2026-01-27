import pygame
import RPi.GPIO as GPIO
import time

# GPIO pin assignments
LEFT_IN1 = 17
LEFT_IN2 = 18
LEFT_ENA = 12

RIGHT_IN3 = 22
RIGHT_IN4 = 23
RIGHT_ENB = 13

# Setup GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup([LEFT_IN1, LEFT_IN2, RIGHT_IN3, RIGHT_IN4], GPIO.OUT)
GPIO.setup([LEFT_ENA, RIGHT_ENB], GPIO.OUT)

# Create PWM objects (50 Hz is common for motors)
pwm_left = GPIO.PWM(LEFT_ENA, 50)
pwm_right = GPIO.PWM(RIGHT_ENB, 50)
pwm_left.start(0)
pwm_right.start(0)


def set_motor(left_speed, right_speed):
    """
    left_speed, right_speed: -100 to +100
        negative = reverse, positive = forward
    """
    # Left motor
    if left_speed > 0:
        GPIO.output(LEFT_IN1, GPIO.HIGH)
        GPIO.output(LEFT_IN2, GPIO.LOW)
    elif left_speed < 0:
        GPIO.output(LEFT_IN1, GPIO.LOW)
        GPIO.output(LEFT_IN2, GPIO.HIGH)
    else:
        GPIO.output(LEFT_IN1, GPIO.LOW)
        GPIO.output(LEFT_IN2, GPIO.LOW)
    pwm_left.ChangeDutyCycle(abs(left_speed))

    # Right motor
    if right_speed > 0:
        GPIO.output(RIGHT_IN3, GPIO.HIGH)
        GPIO.output(RIGHT_IN4, GPIO.LOW)
    elif right_speed < 0:
        GPIO.output(RIGHT_IN3, GPIO.LOW)
        GPIO.output(RIGHT_IN4, GPIO.HIGH)
    else:
        GPIO.output(RIGHT_IN3, GPIO.LOW)
        GPIO.output(RIGHT_IN4, GPIO.LOW)
    pwm_right.ChangeDutyCycle(abs(right_speed))


def main():
    pygame.init()
    pygame.joystick.init()

    if pygame.joystick.get_count() == 0:
        print("No joystick found!")
        return

    js = pygame.joystick.Joystick(0)
    js.init()

    print(f"Using joystick: {js.get_name()}")

    # Track last states
    num_axes = js.get_numaxes()
    num_buttons = js.get_numbuttons()
    num_hats = js.get_numhats()

    last_axes = [0.0] * num_axes
    last_buttons = [0] * num_buttons
    last_hats = [(0, 0)] * num_hats

    try:
        while True:
            pygame.event.pump()

            # Read left analog stick (usually axes 0 = left/right, 1 = up/down)
            lx = js.get_axis(0)  # -1.0 (left) to +1.0 (right)
            ly = js.get_axis(1)  # -1.0 (up) to +1.0 (down)

            # Dead zone
            if abs(lx) < 0.1:
                lx = 0.0
            if abs(ly) < 0.1:
                ly = 0.0

            # Tank drive mapping:
            # ly = forward/backward speed
            # lx = turn (left/right bias)
            forward_speed = -ly * 100  # flip sign so pushing stick up = forward
            turn_bias = lx * 100

            left_speed = forward_speed - turn_bias
            right_speed = forward_speed + turn_bias

            # Clamp to [-100, 100]
            left_speed = max(-100, min(100, left_speed))
            right_speed = max(-100, min(100, right_speed))

            set_motor(left_speed, right_speed)

            # Optional: print axes for debugging
            if abs(last_axes[0] - lx) > 0.05 or abs(last_axes[1] - ly) > 0.05:
                print(f"Left stick: X={lx:+.2f}, Y={ly:+.2f} → L={left_speed:+.0f}, R={right_speed:+.0f}")
                last_axes[0] = lx
                last_axes[1] = ly

            # Buttons / hats (you can ignore or use for extra features)
            for b in range(num_buttons):
                v = js.get_button(b)
                if last_buttons[b] != v:
                    last_buttons[b] = v
                    state = "DOWN" if v else "UP"
                    print(f"BUTTON {b}: {state}")

            for h in range(num_hats):
                v = js.get_hat(h)
                if last_hats[h] != v:
                    last_hats[h] = v
                    print(f"HAT {h}: {v}")

            time.sleep(0.02)

    except KeyboardInterrupt:
        print("\nStopping motors and exiting...")
    finally:
        set_motor(0, 0)
        pwm_left.stop()
        pwm_right.stop()
        GPIO.cleanup()
        pygame.joystick.quit()
        pygame.quit()


if __name__ == "__main__":
    main()
