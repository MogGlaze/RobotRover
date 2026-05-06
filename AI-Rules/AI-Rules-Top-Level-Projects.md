# AI Vibe Coding Over Arching Rules For The Project<BR>(Over Arching Rules)
🤖 Rover AI Vibe Coding Rules (Python)

Jim The STEAM Clown Edition — Updated and expanded from the original draft
to align with the Raspberry Pi Rover Architecture Guide.
Changes from the original are marked: ✏️ updated · ➕ added · ✅ unchanged


🧭 1. Core Design Philosophy ✅

Prioritize readability over cleverness
Code must be teachable to high school / early college students
Favor modular, testable components over monolithic scripts
Every file should have a clear single responsibility
Every abstract concept should be grounded in a real-world analogy when explained


🧱 2. Library & Hardware Rules ✏️
Primary GPIO library: gpiozero
Use gpiozero for all GPIO interactions. It provides clean, high-level classes
(PWMOutputDevice, DigitalOutputDevice, DistanceSensor, LED) that map
naturally to the abstract interfaces this architecture teaches.
Backend: pigpio (always, not optional)
Always configure gpiozero to use pigpio as its pin factory backend:
pythonfrom gpiozero.pins.pigpio import PiGPIOFactory
from gpiozero import Device
Device.pin_factory = PiGPIOFactory(pin_numbering='BOARD')

Why pigpio, not lgpio?
pigpio uses DMA (Direct Memory Access) to generate hardware-quality PWM on
all GPIO pins — not just the two hardware PWM pins. Without this, motor
speed control produces audible stutter under CPU load. lgpio's software PWM
stutters on a loaded Pi 5. For any project driving motors, pigpio is required.
Always document this choice with a comment in the driver file.

pigpio daemon requirement
pigpio requires its background daemon to be running before any script starts:
bashsudo pigpiod
# or at boot: sudo systemctl enable pigpiod
Pin numbering: BOARD always
Always use BOARD numbering (physical header pin positions 1–40), never BCM
chip numbers. BOARD numbers are printed on every Pi pinout diagram next to the
header edge. BCM numbers are the Broadcom internal chip identifiers — they do
not match physical positions and vary between Pi models.
Set BOARD mode once per driver file via PiGPIOFactory(pin_numbering='BOARD').
All constants in hal/pin_config.py are BOARD numbers.
Standard library preference
Use standard Python libraries whenever possible:
time, math, threading, dataclasses, logging, signal, pathlib
No other libraries without justification
If a library outside gpiozero, pigpio, and the standard library is used,
the driver file must include a comment explaining:

What the library does
Why gpiozero alone is insufficient for this use case
What the install command is

Document all hardware assumptions
Every driver file must include a header comment stating:

Pin numbers (BOARD convention)
Voltage levels (3.3 V vs 5 V) and any required level shifting
Sensor model and operating range


📁 3. Project Structure Rules ✏️
Follow this structure. Every directory is a layer. Every layer has one job.
textrover_<name>/                       ← project root (descriptive name, not generic)
│
├── <rover_name>.py                 ← entry point only (descriptive name, e.g.
│                                     pi_rover_ultrasonic.py — not main.py)
├── config.py                       ← tunable behavior parameters only
│
├── hal/                            ← Hardware Abstraction Layer
│   ├── __init__.py
│   └── pin_config.py               ← ALL BOARD pin numbers live here. Only here.
│
├── drivers/                        ← hardware interface only
│   ├── __init__.py
│   ├── motors.py
│   └── sensors.py                  ← one file per device type
│
├── control/                        ← decision-making logic only
│   ├── __init__.py
│   ├── navigation.py
│   └── behaviors.py
│
├── utils/                          ← reusable, hardware-free utilities
│   ├── __init__.py
│   └── logger.py
│
├── tests/                          ← hardware-free unit tests
│   ├── __init__.py
│   └── test_<behavior>.py
│
├── .env.example                    ← template for runtime overrides
├── .gitignore                      ← venv/, __pycache__/, .env, logs/
├── requirements.txt                ← pinned runtime dependencies
├── requirements-dev.txt            ← adds pytest, python-dotenv
└── README.md
Layer rules (absolute — no exceptions):
LayerMay import fromMust NOT import fromhal/pin_config.pynothingeverythingdrivers/hal/, gpiozero, pigpiocontrol/, config.pycontrol/utils/, standard librarygpiozero, pigpio, hal/, config.pyutils/standard library onlyeverything else in the projecttests/control/, utils/ via mocksgpiozero, pigpio, drivers/ directlyEntry pointeverything(injects all dependencies)
__init__.py is required in every subdirectory ➕
Every directory that contains Python modules (hal/, drivers/, control/,
utils/, tests/) must contain an __init__.py file. Without it, Python
cannot find the package and every import fails with ModuleNotFoundError.
An empty file is fine — it just has to exist.
Entry point filename ✏️
Name the entry point file descriptively: pi_rover_ultrasonic.py,
pi_rover_line_follow.py, etc. Avoid the generic main.py — in a curriculum
with multiple rover designs, descriptive names make the purpose immediately
clear without opening the file.
config.py vs hal/pin_config.py ➕
These are two different files with two different jobs — never mix them:

hal/pin_config.py — answers "what BOARD pin is connected to what device?"
Edit this when you rewire the robot.
config.py — answers "how should the robot behave?" (speeds, distances,
PID gains, loop timing). Edit this when you tune the robot.

A student tuning PID should never open pin_config.py.
A student rewiring motors should never open config.py.

🧠 4. Code Style Rules ✏️
Naming

✅ left_motor_speed, MOTOR_LEFT_ENA, read_distance_cm()
❌ lms, pin17, getData()

Constants

ALL_CAPS names for all constants: STOP_THRESHOLD_CM = 15.0
All hardware constants in hal/pin_config.py
All behavior constants in config.py
Use @dataclass(frozen=True) in config.py to make constants truly
immutable at runtime — Python has no const keyword

Type hints — required on all functions
pythondef set_speed(self, left: float, right: float) -> None:
def read_distance_cm(self) -> float:
Docstrings — required on every class and public method
Every public method must document: what it does, its arguments, and its return
value. Private methods (underscore prefix) should have a brief comment.
No global variables
All state lives on class instances (self._speed). Global mutable state is the
hardest category of bug to trace and the first thing students should unlearn.
__repr__ required on all driver classes ➕
Every driver class must implement __repr__ returning a meaningful string:
pythondef __repr__(self) -> str:
    return f"MotorDriver(left={self._left:+.2f}, right={self._right:+.2f})"
This means print(motor_driver) gives useful debugging information instead of
a memory address. On Arduino you scatter Serial.println() calls everywhere.
In Python, implement __repr__ once and the debugger does the rest.
Context managers required on hardware driver classes ➕
Every driver class that holds GPIO resources must support the with statement:
pythondef __enter__(self): return self
def __exit__(self, *args): self.cleanup(); return False
This guarantees cleanup() is called even if the script crashes — Python has
no destructor guarantee, and leaving GPIO pins active after a crash can keep
motors running or damage hardware.

🔁 5. Behavior & Control Rules ✅

Use state-based logic (finite state machines) for multi-step behaviours
Avoid deeply nested if statements — prefer small functions and early returns
Strictly separate:

sensing — driver reads hardware, returns abstract value
decision-making — control layer interprets value, decides action
actuation — driver applies the decision to hardware



Dependency injection — required in all control classes ➕
Control classes must receive their driver objects as constructor arguments —
never instantiate hardware inside a control class:
python# ✅ Correct — drivers injected, class is testable
class ObstacleAvoider:
    def __init__(self, motor_driver, sensor_driver, led_driver):
        self._motors = motor_driver
        self._sensor = sensor_driver

# ❌ Wrong — hardcoded dependency, cannot test without hardware
class ObstacleAvoider:
    def __init__(self):
        self._motors = MotorDriver()   # now you can never inject a mock
The chef does not grow vegetables. The chef receives vegetables. The control
class receives its tools — it does not build them.

🧪 6. Testing & Debugging Rules ✏️
Testing framework: pytest
Use pytest for all unit tests. It is not a heavy framework — it is one
pip install pytest and one command: python -m pytest tests/ -v. It is the
professional Python testing standard and appropriate for high school students.
Tests must run without hardware — this is a design requirement ➕
If a test can only run on a Raspberry Pi with hardware connected, the
architecture is broken. Tests in tests/ must run on any laptop with Python
3.10+, no GPIO library, no pigpio daemon, no hardware of any kind.
This is achieved through mock drivers — fake driver classes that implement
the same interface as real drivers but record commands instead of activating
hardware:
pythonclass MockMotorDriver:
    def set_speed(self, left: float, right: float) -> None:
        self.last_left  = left   # record it — don't touch hardware
        self.last_right = right
    def stop(self) -> None:
        self.set_speed(0.0, 0.0)
    def cleanup(self) -> None:
        pass
The sim test: if python -m pytest tests/ -v passes on your laptop, the
control logic is verified. You only have to debug hardware behaviour on the Pi —
not logic bugs.
logging not print() ✏️
Use logging for all runtime diagnostics — never print().
Featureprint()loggingLog levels❌ none✅ DEBUG / INFO / WARNING / ERRORTimestamp❌ none✅ configurableSource module❌ none✅ automaticFile output❌ redirect only✅ rotating file handlerTurn off❌ edit every line✅ change level in one place
Configure logging once in the entry point via utils/logger.py.
Every other module gets its logger with one line:
pythonlogger = logging.getLogger(__name__)
Never call logging.basicConfig() in a module file — only in utils/logger.py.
Reading error messages ➕
Read Python tracebacks bottom-up — the bottom line is the actual error.
The lines above show the call stack (how execution got there).
The five errors students will hit most often in this project structure:
ErrorMost Common CauseFixModuleNotFoundError: No module named 'drivers'Missing __init__.pytouch drivers/__init__.pyImportError: cannot import name 'X'Typo in class nameCheck exact name in the moduleModuleNotFoundError: No module named 'pigpio'venv not activesource venv/bin/activateAttributeError: object has no attribute 'set_speed'Mock incompleteAdd missing method to mockCircular import errorLayer rule violatedTrace imports — remove the cycle

⚡ 7. Safety Rules ✅ + ➕

Always define a safe stop behaviour — motors default to OFF on any error
Handle sensor failure gracefully: return last valid reading, log a warning,
do not crash the loop
Never assume hardware is connected correctly — validate readings and clamp outputs
try/finally or context managers required in the entry point ➕

pythontry:
    while running:
        avoider.update()
finally:
    # This block runs even if the loop crashes
    motors.cleanup()
    sensor.cleanup()
Without finally, a crash leaves GPIO pins active. Motors may keep running.

Signal handling required ➕

The entry point must handle SIGINT (Ctrl+C) and SIGTERM (systemd stop):
pythonsignal.signal(signal.SIGINT,  handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)
Without a signal handler, Ctrl+C terminates the process instantly with no
GPIO cleanup. On Arduino, the board resets on power cycle. On Linux, nothing
resets — GPIO pins stay in whatever state they were in.

📚 8. Documentation Rules ✏️
Every module must include a header comment block stating:

Purpose — one sentence describing the single responsibility of this file
Layer — which architectural layer this file belongs to
May import from / Must NOT import from — explicit layer rules for this file
Inputs / outputs — what values go in and come out of the public interface
Wiring notes — for driver files: BOARD pin numbers, voltage levels,
hardware model, any required protection circuits (e.g. voltage dividers)

Add comments explaining why, not just what:
python# ✅ Why comment — teaches the student something
# pigpio is used instead of lgpio because DMA PWM prevents motor stutter
# on the Pi 5 under CPU load. lgpio's software PWM stutters audibly.

# ❌ What comment — adds no value, restates the code
# set the pin factory to pigpio
Device.pin_factory = PiGPIOFactory(pin_numbering='BOARD')

🧠 AI Vibe Coding Skills
These define what the AI should be good at doing, not just what it should avoid.
🧩 1. Modular Decomposition ✅
Break large problems into layers: HAL → drivers → control → utils.
Suggest and show the full file structure before writing any code.
Never write a file without first establishing which layer it belongs to.
🔌 2. Hardware Abstraction ✏️
Wrap all hardware in classes. Every driver class must:

Accept abstract normalized values (-1.0 to +1.0 for speed, cm for distance)
Translate internally to hardware terms (PWM duty cycle, direction bits)
Apply hardware constraints (minimum duty threshold, voltage clamping)
Implement __repr__, cleanup(), and context manager support

pythonclass MotorDriver:
    def set_speed(self, left: float, right: float) -> None: ...
    def stop(self)    -> None: ...
    def cleanup(self) -> None: ...
    def __repr__(self) -> str: ...
    def __enter__(self): return self
    def __exit__(self, *a): self.cleanup(); return False
🔄 3. Sensor Interpretation ✅
Convert raw sensor data into meaningful abstract values before returning:

Raw ADC 0.0–1.0 → position −1.0 to +1.0
Echo pulse time → distance in centimetres
Apply exception handling — never crash the control loop on a sensor glitch

🧭 4. Behaviour Design ✅
Implement behaviours as state machines with named states (use enum.Enum).
States should be named in plain language: FORWARD, CAUTION, STOP,
REVERSE, TURN. Transitions should be logged at INFO level so the
student can watch the state machine run in the terminal.
🧪 5. Simulation Thinking ✏️
Do not use SIMULATION_MODE = True flags scattered through code. This
approach creates if SIMULATION_MODE: branches everywhere and produces the
same tangled architecture the project structure is designed to prevent.
Instead, use dependency injection with mock drivers. The control layer
cannot tell the difference between a real MotorDriver and a MockMotorDriver
that records commands — and neither should it need to. The separation is
enforced by the architecture, not by a flag.
python# On laptop — pass mocks:
avoider = ObstacleAvoider(MockMotorDriver(), MockSensorDriver(), MockLEDDriver())

# On Pi — pass real drivers:
avoider = ObstacleAvoider(MotorDriver(), UltrasonicDriver(), StatusLEDDriver())
The entry point file is the only place this decision is made.
🛠️ 6. Incremental Development ✅
Build in verified steps — never jump straight to full autonomy:

Wire and test one motor in isolation
Wire and test one sensor in isolation
Write and test the driver for each
Write and test control logic with mock drivers on a laptop
Combine on hardware — only logic bugs remain at this point

🧯 7. Debugging Awareness ✏️
Add logger.debug() calls at key points — sensor readings, state transitions,
motor commands. Use a log format that includes timestamp and module name so
students can trace execution across multiple files:
text2025-04-15 14:32:01 [control.obstacle_avoid ] INFO     FORWARD → STOP (12.3 cm)
2025-04-15 14:32:01 [drivers.motors         ] DEBUG    Motors → L=-0.45  R=-0.45
This is far more useful than print(f"Distance: {distance}") because the
student can see which file each line came from and filter by level.
🎓 8. Teaching Awareness ✅
Every generated code block should be accompanied by:

What it does — one sentence
Why it's structured that way — connect to the architectural principle
Common mistake — what a student would write instead, and why it breaks
Next challenge — one concrete thing the student could add or change


🚫 Anti-Patterns (Explicitly Banned) ✏️
Anti-PatternWhy It's BannedGPIO code directly in the entry pointEntry point is orchestration only — hardware belongs in drivers/Hardcoded pin numbers in driver filesAll pins live in hal/pin_config.py — one file, one edit to rewireScripts longer than 200 lines without structureSplit into layers — single responsibility per fileUsing asyncio or ROS unless explicitly requestedAdds complexity before the student understands the synchronous modelMagic numbers with no name or explanationEvery constant needs a name in config.py or pin_config.pyCopy-paste duplication instead of functionsIf it appears twice, it should be a function in utils/SIMULATION_MODE = True flagsUse mock drivers and dependency injection insteadprint() for runtime diagnosticsUse logging — has levels, timestamps, file output, filteringlogging.basicConfig() in module filesConfigure logging once in utils/logger.py, called from entry point onlyInstantiating hardware inside control classesControl classes receive drivers — they do not build themMissing __init__.py in package directoriesPython cannot find the package — ModuleNotFoundError every timeRunning without a virtual environmentPollutes system Python — breaks other tools on the PiCommitting venv/, __pycache__/, or .env to GitUse .gitignore — these are generated or machine-specificMixing pin numbers and PID gains in the same filepin_config.py is for wiring, config.py is for tuning — never mix

✅ The Three Architecture Self-Check Tests ➕
Before submitting or sharing any rover project, apply these three tests.
If any test fails, the architecture has a problem that needs fixing first.
Test 1 — The Sim Test
Can you run python -m pytest tests/ -v on a laptop with no Pi hardware
connected and have all tests pass? If yes, the control logic is hardware-free
and properly separated. If no, hardware imports have leaked into the wrong layer.
Test 2 — The Rewire Test
Can you change every GPIO pin assignment by editing only hal/pin_config.py
and changing nothing else? If yes, the HAL is doing its job. If no, raw pin
numbers have leaked into driver or control files.
Test 3 — The Teammate Test
Can a teammate open any single file in the project, understand its complete
responsibility in under two minutes, and make a change without reading any
other file? If yes, each file has a single clear responsibility. If no, the
responsibilities are bleeding across layer boundaries.

🌱 Environment & Deployment Rules ➕
Virtual environments are required — not optional
bashpython3 -m venv venv
source venv/bin/activate      # always activate before running or installing
pip install -r requirements.txt
Never pip install into system Python on the Pi. System Python tools depend
on specific package versions — a conflicting install can break them silently.
Two requirements files

requirements.txt — pinned direct runtime dependencies only (not transitive)
requirements-dev.txt — adds pytest, python-dotenv; includes base via -r requirements.txt

.gitignore entries — required
textvenv/
__pycache__/
*.pyc
.env
rover_logs/
*.log
.pytest_cache/
Git deployment goal
A teammate should be able to clone the repo onto a fresh Pi and have the
rover running with:
bashgit clone <repo>
cd rover_<name>
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
sudo pigpiod
python3 pi_rover_<name>.py
No manual steps. No "I also installed this other thing." Reproducible.
