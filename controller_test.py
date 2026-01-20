#!/usr/bin/env python3
"""
Read Nintendo Switch controller input on macOS using pygame (SDL).
Works when the controller is connected via Bluetooth or USB and shows up as a game controller.

Usage:
  python3 read_switch_controller_pygame.py
"""

import sys
import time

import pygame


def main():
    pygame.init()
    pygame.joystick.init()

    count = pygame.joystick.get_count()
    if count == 0:
        print("No controllers detected.")
        print("Tips:")
        print(" - Connect the controller via Bluetooth (System Settings > Bluetooth) or USB")
        print(" - Make sure it appears in macOS as a game controller")
        sys.exit(1)

    print(f"Detected {count} controller(s):")
    joysticks = []
    for i in range(count):
        js = pygame.joystick.Joystick(i)
        js.init()
        joysticks.append(js)
        print(f"  [{i}] {js.get_name()} | axes={js.get_numaxes()} buttons={js.get_numbuttons()} hats={js.get_numhats()}")

    # Pick the first controller by default
    js = joysticks[0]
    print("\nReading inputs from:", js.get_name())
    print("Press Ctrl+C to quit.\n")

    # Simple state trackers to avoid spamming unchanged values (optional)
    last_axes = [None] * js.get_numaxes()
    last_buttons = [None] * js.get_numbuttons()
    last_hats = [None] * js.get_numhats()

    try:
        while True:
            # Pump events so pygame updates joystick state
            pygame.event.pump()

            # Axes (analog sticks, triggers depending on mapping)
            for a in range(js.get_numaxes()):
                v = js.get_axis(a)
                # deadzone for sticks
                if abs(v) < 0.05:
                    v = 0.0
                if last_axes[a] != v:
                    last_axes[a] = v
                    print(f"AXIS {a}: {v:+.3f}")

            # Buttons
            for b in range(js.get_numbuttons()):
                v = js.get_button(b)  # 0 or 1
                if last_buttons[b] != v:
                    last_buttons[b] = v
                    state = "DOWN" if v else "UP"
                    print(f"BUTTON {b}: {state}")

            # Hats (D-pad) returns (x,y) each in {-1,0,1}
            for h in range(js.get_numhats()):
                v = js.get_hat(h)
                if last_hats[h] != v:
                    last_hats[h] = v
                    print(f"HAT {h}: {v}")

            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        pygame.joystick.quit()
        pygame.quit()


if __name__ == "__main__":
    main()
