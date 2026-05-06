# rover.py
# Simple rover entry point.
#
# Imports pin assignments from the hal/ package and uses them
# to set up gpiozero devices. All pin numbers come from
# hal/pin_config.py — none are hardcoded here.
#
# Run:  python3 rover.py
#
# Requirements:
#   pip install gpiozero pigpio
#   sudo pigpiod          (start the pigpio daemon)

import time

from gpiozero import Device, LED, PWMOutputDevice, DigitalOutputDevice
from gpiozero import DistanceSensor
from gpiozero.pins.pigpio import PiGPIOFactory

# ── Import pin numbers from the HAL package ───────────────────
# This is the only place pin numbers enter the program.
# If you rewire the robot, edit hal/pin_config.py — not this file.
from hal.pin_config import (
    STATUS_LED,
    MOTOR_LEFT_ENA,
    MOTOR_LEFT_IN1,
    MOTOR_LEFT_IN2,
    MOTOR_RIGHT_ENB,
    MOTOR_RIGHT_IN3,
    MOTOR_RIGHT_IN4,
    # ULTRASONIC_TRIG,
    # ULTRASONIC_ECHO,
)

# ── Configure gpiozero to use pigpio with BOARD numbering ─────
# This must happen before any Device is created.
Device.pin_factory = PiGPIOFactory(pin_numbering='BOARD')

# ── Set up hardware devices using BOARD pin numbers ───────────
led    = LED(STATUS_LED)

left_ena  = PWMOutputDevice(MOTOR_LEFT_ENA,  initial_value=0)
left_in1  = DigitalOutputDevice(MOTOR_LEFT_IN1,  initial_value=False)
left_in2  = DigitalOutputDevice(MOTOR_LEFT_IN2,  initial_value=False)

right_enb = PWMOutputDevice(MOTOR_RIGHT_ENB, initial_value=0)
right_in3 = DigitalOutputDevice(MOTOR_RIGHT_IN3, initial_value=False)
right_in4 = DigitalOutputDevice(MOTOR_RIGHT_IN4, initial_value=False)

# sensor = DistanceSensor(echo=ULTRASONIC_ECHO, trigger=ULTRASONIC_TRIG)


def set_motors(left: float, right: float) -> None:
    """
    Drive both motors.
    left / right: -1.0 (full reverse) to +1.0 (full forward), 0.0 = stop.
    """
    # Left motor
    left_in1.value = left > 0
    left_in2.value = left < 0
    left_ena.value = abs(left)

    # Right motor
    right_in3.value = right > 0
    right_in4.value = right < 0
    right_enb.value = abs(right)


def stop() -> None:
    """Stop both motors."""
    set_motors(0.0, 0.0)


def cleanup() -> None:
    """Release all GPIO resources."""
    stop()
    for device in (
        left_ena, left_in1, left_in2,
        right_enb, right_in3, right_in4,
        led, sensor,
    ):
        device.close()


# ── Main program ──────────────────────────────────────────────
if __name__ == "__main__":
    print("Rover starting — press Ctrl+C to stop")
    print(f"Using BOARD pin {STATUS_LED} for status LED")
    print(f"Using BOARD pins {MOTOR_LEFT_ENA}/{MOTOR_LEFT_IN1}/{MOTOR_LEFT_IN2} for left motor")
    print(f"Using BOARD pins {MOTOR_RIGHT_ENB}/{MOTOR_RIGHT_IN3}/{MOTOR_RIGHT_IN4} for right motor")
    # print(f"Using BOARD pins {ULTRASONIC_TRIG}/{ULTRASONIC_ECHO} for ultrasonic sensor")

    try:
        # Startup blink — 3 flashes to show the program is alive
        for _ in range(3):
            led.on();  time.sleep(0.2)
            led.off(); time.sleep(0.2)

        # Simple Motor Test - Drive forward, backward
        # drive forward
        led.off()
        set_motors(0.5, 0.5)
        time.sleep(2)
        stop()
        time.sleep(0.5)
        # drive backward
        set_motors(-0.5, -0.5)
        time.sleep(2)
        stop()
        time.sleep(0.5)

        """
        # Simple obstacle avoidance loop
        while True:
            distance_cm = sensor.distance * 100   # gpiozero returns metres

            print(f"Distance: {distance_cm:.1f} cm")

            if distance_cm < 20:
                # Obstacle close — stop and blink LED
                print("Obstacle! Stopping.")
                stop()
                led.on()
            else:
                # Path clear — drive forward
                led.off()
                set_motors(0.5, 0.5)

            time.sleep(0.1)
        """

    except KeyboardInterrupt:
        print("\nCtrl+C received — stopping")

    finally:
        cleanup()
        print("Rover stopped. GPIO released.")
