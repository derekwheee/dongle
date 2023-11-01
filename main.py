import time
import board
import neopixel
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_hid.keycode import Keycode
from digitalio import DigitalInOut, Pull
import touchio
from lib.env import OPTIONS

options = OPTIONS()

# Sleep to avoid a race condition on some systems
time.sleep(1)

pixel = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness = 0.5)

keyboard = Keyboard(usb_hid.devices)
keyboard_layout = KeyboardLayoutUS(keyboard)

button = DigitalInOut(board.SWITCH)
button.switch_to_input(pull=Pull.DOWN)

touch = touchio.TouchIn(board.TOUCH)

def make_keystrokes(keys, delay):
    if isinstance(keys, str):  # If it's a string...
        keyboard_layout.write(keys)  # ...Print the string
    elif isinstance(keys, int):  # If its a single key
        keyboard.press(keys)  # 'Press'...
        keyboard.release_all()  # ...'Release'!
    elif isinstance(keys, (list, tuple)):  # If its multiple keys
        keyboard.press(*keys)  # 'Press'...
        keyboard.release_all()  # ...'Release'!
    time.sleep(delay)

modes = [
    {
        'macro': options.LAPTOP_PASSWORD,
        'color': (0, 255, 255)
    },
    {
        'macro': options.MASTER_PASSWORD,
        'color': (255, 0, 255)
    },
    {
        'macro': (Keycode.COMMAND, Keycode.E),
        'color': (255, 64, 0)
    },
    {
        'macro': (Keycode.ESCAPE),
        'color': (255, 0, 0)
    }
]

state = {
    'mode': 0,
    'currentColor': modes[0]['color'],
    'isButtonPressed': False,
    'isTouched': False,
    'isMenuMode': False,
    'lastKeypress': time.monotonic(),
    'lastBlink': time.monotonic()
}

shouldToggleMenuMode = True
shouldSkipRelease = False

def scaleColors(now, colors, duration = 1000):

    half = duration / 2

    timeElapsedMs = int((now - state['lastKeypress']) * 1000) % duration

    if timeElapsedMs < half:
        scalar = timeElapsedMs / half
    else:
        scalar = (half - (timeElapsedMs - half)) / half

    return (
        colors[0] * scalar,
        colors[1] * scalar,
        colors[2] * scalar
    )

while True:

    now = time.monotonic()

    if shouldToggleMenuMode and state['isButtonPressed'] and now - state['lastKeypress'] > 1:
        state['isMenuMode'] = not state['isMenuMode']
        state['currentColor'] = modes[state['mode']]['color']
        shouldToggleMenuMode = False
        shouldSkipRelease = True

    if state['isMenuMode'] or (shouldToggleMenuMode and state['isButtonPressed'] and now - state['lastKeypress'] > 1):
        state['currentColor'] = scaleColors(now, modes[state['mode']]['color'])

    if button.value and not state['isButtonPressed']:
        state['isButtonPressed'] = True
        state['lastKeypress'] = now

    if not button.value and state['isButtonPressed']:

        state['isButtonPressed'] = False

        if not shouldSkipRelease:
            if not state['isMenuMode']:
                state['currentColor'] = (255, 0, 0)
            
                if isinstance(modes[state['mode']]['macro'], (list, tuple)) and isinstance(modes[state['mode']]['macro'][0], dict):
                    for k in modes[state['mode']]['macro']:
                        make_keystrokes(k['keys'], k['delay'])
                else:
                    make_keystrokes(modes[state['mode']]['macro'], delay=0)

                state['currentColor'] = modes[state['mode']]['color']

            if state['isMenuMode']:
                state['mode'] = 0 if state['mode'] == len(modes) - 1 else state['mode'] + 1

        shouldToggleMenuMode = True
        shouldSkipRelease = False

    if touch.value and not state['isTouched']:
        state['currentColor'] = (64, 0, 255)
        state['isTouched'] = True
    if not touch.value and state['isTouched']:
        state['currentColor'] = modes[state['mode']]['color']
        state['isTouched'] = False

    pixel.fill(state['currentColor'])
