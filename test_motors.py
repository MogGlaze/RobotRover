from gpiozero import Motor
from time import sleep

drive_motor = Motor(forward=17, backward=27)

print("Testing drive motor forward...")
drive_motor.forward(1.0)
sleep(2)
drive_motor.stop()
print("Done!")
