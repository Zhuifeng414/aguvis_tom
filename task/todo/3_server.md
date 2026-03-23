Nice, it works, now i can access it through my local computer.

Now, please write a code run on my local computer, when i type 'kk', it will have a screenshot save as .png

THen this .png will be uploaded into my server, as the new image in /home/tuq24452/code/GUIAgent/aguvis/streamlit_ui/app.py

Please dont change current code in /home/tuq24452/code/GUIAgent/aguvis/streamlit_ui, you should create a new subfolder and work on it, 
You need to refer current code in /home/tuq24452/code/GUIAgent/aguvis/streamlit_ui. The only change is, when i click kk on my local computer, the .png will appear as new image in /home/tuq24452/code/GUIAgent/aguvis/streamlit_ui/app.py


You can refer following code about how to do screenshot with key input kk:

import pyautogui
from pynput import keyboard
import time
import os

# Store the last key pressed to check for the 'kk' sequence
last_key = None

def on_press(key):
    global last_key
    trigger_keys = ['kk', 'gg']
    try:
        # Check if current key and previous key are both 'k' or 'g'
        if (key.char == 'k' and last_key == 'k')  or (key.char == 'm' and last_key == 'm') or (key.char == 'g' and last_key == 'g'):
            take_screenshot()
            # Reset last_key so 'kkk' doesn't trigger two screenshots
            last_key = None
        else:
            last_key = key.char
    except AttributeError:
        # Handle special keys (Shift, Ctrl, etc.)
        last_key = None

def take_screenshot():
    # Create a filename based on the current timestamp
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    filename = f"./pic/screenshot_{timestamp}.png"
    
    # Take and save the screenshot
    screenshot = pyautogui.screenshot()
    screenshot.save(filename)
    print(f"Saved: {filename}")

# Setup the listener
with keyboard.Listener(on_press=on_press) as listener:
    listener.join()