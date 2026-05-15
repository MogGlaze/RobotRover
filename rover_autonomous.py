from gpiozero import Motor, DistanceSensor
from time import sleep

# --- MOTORS ---
drive_motor    = Motor(forward=17, backward=27)
steering_motor = Motor(forward=22, backward=23)

# --- ULTRASONIC SENSOR (TRIG=GPIO5, ECHO=GPIO6) ---
sensor = DistanceSensor(echo=6, trigger=5, max_distance=2)

# --- SETTINGS ---
DRIVE_SPEED    = 0.7
OBSTACLE_DIST  = 0.305  # 1 foot  — hard stop
WARN_DIST      = 0.914  # 3 feet  — back up if stationary object ahead
BAIL_DIST      = 0.914  # 3 feet  — abort escape maneuver if path is clear
CLICK_DURATION = 0.12   # seconds per steering click — tune per your hardware

# ─────────────────────────────────────────────────────
#  WHEEL POSITION TRACKING
#  0 = straight, -3 = full left, +3 = full right
#  Tracked so we can always recenter from anywhere.
# ─────────────────────────────────────────────────────
wheel_pos = 0

def stop():
    drive_motor.stop()
    steering_motor.stop()

def is_blocked():
    return sensor.distance < OBSTACLE_DIST

def is_clear():
    """Nothing within 6 feet — safe to abandon escape and go straight."""
    return sensor.distance >= BAIL_DIST

def click(direction, count):
    """
    Send N steering clicks. Wheels must be rolling.
    Tracks wheel_pos so recenter always knows where it is.
    """
    global wheel_pos
    for _ in range(count):
        if direction == 'left':
            steering_motor.forward()
            wheel_pos = max(wheel_pos - 1, -3)
        else:
            steering_motor.backward()
            wheel_pos = min(wheel_pos + 1, 3)
        sleep(CLICK_DURATION)
        steering_motor.stop()
        sleep(0.05)

def recenter_and_go():
    """
    Stop whatever we're doing, re-centre the wheels, drive forward.
    Called whenever the path clears during an escape maneuver.
    """
    global wheel_pos
    print(f"Path clear! Recentering (pos={wheel_pos}) and going forward")
    stop()
    sleep(0.1)
    drive_motor.forward(DRIVE_SPEED * 0.5)  # slow roll while recentering
    if wheel_pos < 0:
        click('right', abs(wheel_pos))       # wheels were left, click right to center
    elif wheel_pos > 0:
        click('left', wheel_pos)             # wheels were right, click left to center
    stop()
    sleep(0.1)

def drive_with_bail(drive_dir, duration):
    """
    Drive forward or backward for up to `duration` seconds.
    Checks sensor every 0.05s — bails immediately if path goes clear (6ft).
    Returns True if bailed early, False if full duration completed.
    """
    if drive_dir == 'forward':
        drive_motor.forward(DRIVE_SPEED)
    else:
        drive_motor.backward(DRIVE_SPEED * 0.6)

    elapsed = 0.0
    interval = 0.05
    while elapsed < duration:
        sleep(interval)
        elapsed += interval
        if is_clear():
            return True   # bailed — path is clear

    stop()
    sleep(0.2)
    return False          # completed full duration

def turn_and_drive(steer_dir, clicks, drive_dir, duration):
    """
    Start driving, apply steering clicks, then drive remaining time.
    Bails mid-drive if path clears within 6 feet.
    Returns True if bailed, False if completed.
    """
    if drive_dir == 'forward':
        drive_motor.forward(DRIVE_SPEED)
    else:
        drive_motor.backward(DRIVE_SPEED * 0.6)

    click(steer_dir, clicks)

    # Drive remaining time, checking sensor every 0.05s
    elapsed = 0.0
    interval = 0.05
    while elapsed < duration:
        sleep(interval)
        elapsed += interval
        if is_clear():
            return True   # bail out

    stop()
    sleep(0.2)
    return False

def try_left():
    """Full left turn, drive 1.5s, recenter. Returns True if bailed."""
    print("Trying left")
    bailed = turn_and_drive('left', 3, 'forward', 1.5)
    if bailed:
        recenter_and_go()
        return True
    # Completed — recenter wheels
    drive_motor.forward(DRIVE_SPEED * 0.4)
    click('right', 3)
    stop()
    sleep(0.2)
    return False

def escape_right():
    """3-point escape to the right. Bails at any step if path clears."""
    print("Escaping right")

    # Step 1: reverse full left
    bailed = turn_and_drive('left', 3, 'backward', 2.5)
    if bailed:
        recenter_and_go()
        return True

    # Step 2: forward full right (6 clicks: full-left -> centre -> full-right)
    bailed = turn_and_drive('right', 6, 'forward', 2.5)
    if bailed:
        recenter_and_go()
        return True

    # Step 3: recenter (full-right -> centre = 3 left clicks)
    drive_motor.forward(DRIVE_SPEED * 0.4)
    click('left', 3)
    stop()
    sleep(0.2)
    return False

def escape_left():
    """3-point escape to the left. Bails at any step if path clears."""
    print("Escaping left")

    # Step 1: reverse full right
    bailed = turn_and_drive('right', 3, 'backward', 2.5)
    if bailed:
        recenter_and_go()
        return True

    # Step 2: forward full left
    bailed = turn_and_drive('left', 6, 'forward', 2.5)
    if bailed:
        recenter_and_go()
        return True

    # Step 3: recenter
    drive_motor.forward(DRIVE_SPEED * 0.4)
    click('right', 3)
    stop()
    sleep(0.2)
    return False

# ─────────────────────────────────────────────────────
#  MAIN LOOP
# ─────────────────────────────────────────────────────
print("Rover starting... CTRL+C to stop.")
stop()
sleep(1)

going_forward = False
escape_right_first = True   # alternates each escape attempt — True = try right first
try:    
    while True:
        dist = sensor.distance

        # ── Early warning: stationary object within 3ft while going forward ──
        if going_forward and dist < WARN_DIST:
            sleep(0.15)
            dist2 = sensor.distance
            getting_closer = dist2 < dist - 0.02  # closing > ~0.8 inches

            if not getting_closer:
                print(f"Stationary object at {dist:.2f}m — backing up 3s then escaping")
                going_forward = False
                stop()
                # Straight reverse 3 seconds, bail if clear
                bailed = drive_with_bail('backward', 3.0)
                if not bailed:
                    # Jump to escape
                    print("Starting escape after backup")
                    bailed = try_left()
                    if not bailed and not is_blocked():
                        going_forward = True
                        continue
                    if not bailed:
                        first  = escape_right if escape_right_first else escape_left
                        second = escape_left  if escape_right_first else escape_right
                        escape_right_first = not escape_right_first
                        bailed = first()
                    if not bailed and not is_blocked():
                        going_forward = True
                        continue
                    if not bailed:
                        second()
                going_forward = True
                continue

        # ── Hard stop at 1 foot ────────────────────────────────────────────────
        if not is_blocked():
            drive_motor.forward(DRIVE_SPEED)
            going_forward = True
            sleep(0.05)

        else:
            stop()
            going_forward = False
            print(f"Blocked at {dist:.2f}m")

            bailed = try_left()
            if not bailed and not is_blocked():
                going_forward = True
                continue

            if not bailed:
                first  = escape_right if escape_right_first else escape_left
                second = escape_left  if escape_right_first else escape_right
                escape_right_first = not escape_right_first
                bailed = first()
            if not bailed and not is_blocked():
                going_forward = True
                continue

            if not bailed:
                second()

            going_forward = True

except KeyboardInterrupt:
    print("\nStopped.")
finally:
    stop()
