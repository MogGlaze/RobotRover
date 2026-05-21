#!/usr/bin/env python3
# rover_server_wasd.py
# Web-based rover control server — matches rover_wasd.py exactly.
# No distance sensor required. Camera index 0.
# Run: python3 rover_server_wasd.py
# Then open http://<pi-ip>:5000 on any device on the same network.
#
# Dependencies:
#   pip install flask opencv-python --break-system-packages

import os
import threading
import cv2
from flask import Flask, request, jsonify, Response
from gpiozero import Motor
from time import sleep

os.environ["QT_QPA_PLATFORM"] = "xcb"  # fixes wayland/Qt plugin error

# ── PIN SETUP (matches rover_wasd.py exactly) ─────────────────
drive_motor    = Motor(forward=17, backward=27, pwm=False)
steering_motor = Motor(forward=22, backward=23, pwm=False)

STEER_DURATION = 0.1
state          = "stopped"   # "stopped" | "forward" | "backward"

# ── CAMERA SETUP (index 0, matches rover_wasd.py) ─────────────
latest_frame = [None]
camera_ok    = [False]
_camera_lock = threading.Lock()

def camera_capture():
    """Only captures frames — never calls imshow (must stay off main thread)."""
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[Camera] Failed to open — check USB connection")
        return
    camera_ok[0] = True
    while True:
        ret, frame = cap.read()
        if ret:
            with _camera_lock:
                latest_frame[0] = frame
    cap.release()

cam_thread = threading.Thread(target=camera_capture, daemon=True)
cam_thread.start()
sleep(1)  # give camera a moment to init

if not camera_ok[0]:
    print("[Camera] Not detected — running without video feed\n")

def generate_frames():
    """Yield a continuous MJPEG stream from the USB camera."""
    import numpy as np
    blank = np.zeros((480, 640, 3), dtype='uint8')
    blank[:] = 30
    while True:
        with _camera_lock:
            frame = latest_frame[0]
        if frame is None:
            frame = blank
        _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buf.tobytes() + b'\r\n')


# ── STEERING HELPERS (matches rover_wasd.py exactly) ──────────
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


# ── FLASK APP ─────────────────────────────────────────────────
app = Flask(__name__)

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<title>Rover Control</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: #0f1117;
    color: #e2e8f0;
    font-family: 'Segoe UI', system-ui, sans-serif;
    display: flex;
    flex-direction: column;
    align-items: center;
    min-height: 100svh;
    padding: 16px;
    gap: 16px;
  }
  h1 { font-size: 1.3rem; font-weight: 700; letter-spacing: 0.05em; color: #7dd3fc; }

  #camera-wrap {
    width: 100%; max-width: 640px;
    background: #1e2433;
    border-radius: 12px; overflow: hidden;
    position: relative; aspect-ratio: 4/3;
  }
  #camera-feed { width: 100%; height: 100%; object-fit: cover; display: block; }
  #cam-badge {
    position: absolute; top: 8px; left: 8px;
    background: rgba(0,0,0,0.55); color: #86efac;
    font-size: 0.7rem; font-weight: 700;
    padding: 3px 8px; border-radius: 20px; letter-spacing: 0.05em;
  }

  #status-bar {
    width: 100%; max-width: 640px;
    background: #1e2433; border-radius: 12px;
    padding: 12px 16px;
    display: flex; justify-content: space-between; align-items: center;
    font-size: 0.85rem;
  }
  .stat-label { color: #94a3b8; }
  .stat-value { font-weight: 600; color: #86efac; }

  .dpad {
    display: grid;
    grid-template-columns: repeat(3, 80px);
    grid-template-rows: repeat(3, 80px);
    gap: 8px; user-select: none;
  }
  .btn {
    border-radius: 12px; border: none; font-size: 1.6rem; cursor: pointer;
    background: #1e2433; color: #e2e8f0;
    display: flex; align-items: center; justify-content: center;
    transition: background 0.1s, transform 0.08s;
    -webkit-tap-highlight-color: transparent; touch-action: manipulation;
  }
  .btn:active          { background: #2d4a6e; transform: scale(0.93); }
  .btn.stop-btn        { background: #2d1f1f; color: #f87171; font-size: 1.1rem; font-weight: 700; }
  .btn.stop-btn:active { background: #5c2626; }
  .btn.active          { background: #1e4a2d; border: 2px solid #86efac; }
  .btn-up    { grid-column: 2; grid-row: 1; }
  .btn-left  { grid-column: 1; grid-row: 2; }
  .btn-stop  { grid-column: 2; grid-row: 2; }
  .btn-right { grid-column: 3; grid-row: 2; }
  .btn-down  { grid-column: 2; grid-row: 3; }

  #hint { color: #555; font-size: 12px; text-align: center; }
</style>
</head>
<body>

<h1>🤖 Rover Control</h1>

<div id="camera-wrap">
  <img id="camera-feed" src="/video" alt="Camera feed">
  <div id="cam-badge">● LIVE</div>
</div>

<div id="status-bar">
  <span class="stat-label">State</span>
  <span class="stat-value" id="action-value">Idle</span>
</div>

<div class="dpad">
  <button class="btn btn-up"            id="btn-w"   onmousedown="cmd('forward')"  ontouchstart="cmd('forward')">▲</button>
  <button class="btn btn-left"          id="btn-a"   onmousedown="cmd('left')"     ontouchstart="cmd('left')">◀</button>
  <button class="btn btn-stop stop-btn" id="btn-spc" onmousedown="cmd('stop')"     ontouchstart="cmd('stop')">■</button>
  <button class="btn btn-right"         id="btn-d"   onmousedown="cmd('right')"    ontouchstart="cmd('right')">▶</button>
  <button class="btn btn-down"          id="btn-s"   onmousedown="cmd('backward')" ontouchstart="cmd('backward')">▼</button>
</div>

<div id="hint">
  W = Forward &nbsp;|&nbsp; S = Backward &nbsp;|&nbsp; A = Left &nbsp;|&nbsp; D = Right<br>
  W/S again while moving = Brake &nbsp;|&nbsp; Space = Stop
</div>

<script>
  // ── Send command to server ──
  async function cmd(action) {
    try {
      const res = await fetch('/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cmd: action })
      });
      updateUI(await res.json());
    } catch(e) { console.error(e); }
  }

  // ── Update status display ──
  function updateUI(data) {
    const action = data.action;
    document.getElementById('action-value').textContent =
      action === 'stopped' ? 'Idle' : action.charAt(0).toUpperCase() + action.slice(1);

    ['btn-w','btn-a','btn-s','btn-d'].forEach(id =>
      document.getElementById(id).classList.remove('active'));
    if (action === 'forward')  document.getElementById('btn-w').classList.add('active');
    if (action === 'backward') document.getElementById('btn-s').classList.add('active');
  }

  // ── WASD keyboard — exact same logic as rover_wasd.py ──
  // W while going backward = brake
  // S while going forward  = brake
  // W/S while stopped      = move
  // A/D                    = steer (one pulse)
  // Space                  = stop

  const pressed = new Set();

  document.addEventListener('keydown', e => {
    const k = e.key.toLowerCase();
    if (pressed.has(k)) return; // no repeat
    pressed.add(k);

    if      (k === 'w') { e.preventDefault(); cmd('forward'); }
    else if (k === 's') { e.preventDefault(); cmd('backward'); }
    else if (k === 'a') { e.preventDefault(); cmd('left'); }
    else if (k === 'd') { e.preventDefault(); cmd('right'); }
    else if (k === ' ') { e.preventDefault(); cmd('stop'); }
  });

  document.addEventListener('keyup', e => {
    pressed.delete(e.key.toLowerCase());
  });

  // ── Poll state every 300ms ──
  async function poll() {
    try { updateUI(await (await fetch('/status')).json()); } catch(e) {}
    setTimeout(poll, 300);
  }
  poll();
</script>
</body>
</html>
"""


# ── ROUTES ────────────────────────────────────────────────────
@app.route('/')
def index():
    return HTML

@app.route('/video')
def video():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/status')
def status():
    return jsonify(action=state)

@app.route('/command', methods=['POST'])
def command():
    global state
    action = request.get_json().get('cmd', 'stop')

    # ── Exact same logic as rover_wasd.py ──
    if action == 'forward':
        if state == 'backward':
            print(">> Brake")
            stop_all()
            state = 'stopped'
        else:
            print(">> Forward")
            drive_motor.forward()
            state = 'forward'

    elif action == 'backward':
        if state == 'forward':
            print(">> Brake")
            stop_all()
            state = 'stopped'
        else:
            print(">> Backward")
            drive_motor.backward()
            state = 'backward'

    elif action == 'left':
        print(">> Steer Left")
        steer_left()

    elif action == 'right':
        print(">> Steer Right")
        steer_right()

    elif action == 'stop':
        print(">> Stop")
        stop_all()
        state = 'stopped'

    return jsonify(action=state)


if __name__ == '__main__':
    try:
        print("=== ROVER SERVER (WASD) ===")
        print("W = Forward  | S = Backward")
        print("A = Left     | D = Right")
        print("W/S again while moving = Brake")
        print("Space = Stop")
        print("Open http://<your-pi-ip>:5000 in a browser")
        print("===========================\n")
        app.run(host='0.0.0.0', port=5000, threaded=True)
    finally:
        stop_all()
        print("Motors stopped. Bye!")
