from gpiozero import Motor
from time import sleep
import readchar
import cv2
import threading

# --- PIN SETUP ---
drive_motor = Motor(forward=17, backward=27)
steering_motor = Motor(forward=22, backward=23)

STEER_DURATION = 0.1
state = "stopped"

# --- CAMERA SETUP ---
cap = cv2.VideoCapture(0)  # 0 = first USB camera

def camera_stream():
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        cv2.imshow("Rover Camera", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

# Start camera in a separate thread so it doesnt block controls
cam_thread = threading.Thread(target=camera_stream, daemon=True)
cam_thread.start()

def steer_left():
    steering_motor.forward()
    sleep(STEER_DURATION)
    steering_motor.stop()

def steer_right():
    steering_motor.backward()
    sleep(STEER_DURATION)
    steering_motor.stop()

def stop_all():
    drive_motor.stop()
    steering_motor.stop()

print("=== ROVER KEYBOARD CONTROL ===")
print("W = Forward/Brake | S = Backward/Brake")
print("A = Left    | D = Right")
print("SPACE = Stop | Q = Quit")
print("==============================\n")

try:
    while True:
        key = readchar.readkey()

        if key == 'w':
            if state == "backward":
                print(">> Brake")
                state = "stopped"
                drive_motor.stop()
            elif state == "stopped":
                print(">> Forward")
                state = "forward"
                drive_motor.forward(0.7)
            elif state == "forward":
                print(">> Forward")
                drive_motor.forward(0.7)

        elif key == 's':
            if state == "forward":
                print(">> Brake")
                state = "stopped"
                drive_motor.stop()
            elif state == "stopped":
                print(">> Backward")
                state = "backward"
                drive_motor.backward(0.7)
            elif state == "backward":
                print(">> Backward")
                drive_motor.backward(0.7)

        elif key == 'a':
            print(">> Steer Left")
            steer_left()

        elif key == 'd':
            print(">> Steer Right")
            steer_right()

        elif key == ' ':
            print(">> Stop")
            state = "stopped"
            stop_all()

        elif key == 'q':
            print(">> Quitting...")
            break

except KeyboardInterrupt:
    pass
finally:
    stop_all()
    cap.release()
    cv2.destroyAllWindows()
    print("Motors stopped. Bye!")
