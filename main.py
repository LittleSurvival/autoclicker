import tkinter as tk
from tkinter import ttk
import threading
import time
import yaml
import os

from pynput import mouse, keyboard
from pynput.mouse import Controller as MouseController, Button as MouseButton
from pynput.keyboard import Key, Listener as KeyboardListener, KeyCode

CONFIG_FILE = 'config.yaml'

# ------------------------------------------------------------------------
# Load / Save Config
# ------------------------------------------------------------------------
default_config = {
    'left_click': {
        'mode': 'cps',        # 'cps' or 'delay'
        'cps': 10,            # clicks per second
        'delay': 100,         # ms
        'bind': None,         # e.g. "f6", "mouse4"
    },
    'right_click': {
        'mode': 'delay',      # 'cps' or 'delay'
        'cps': 5,             # clicks per second
        'delay': 200,         # ms
        'bind': None,         # e.g. "mouse5", "r"
    },
    'safety_key': 'alt',      # when this is held, no auto-click
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    else:
        return default_config

def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        yaml.safe_dump(config, f)

# ------------------------------------------------------------------------
# Global variables
# ------------------------------------------------------------------------
config = load_config()
mouse_controller = MouseController()

# Whether left/right click auto-clickers are actively running
left_click_active = False
right_click_active = False

# If we're listening for a new bind, store which section we are setting:
# can be 'left_click' or 'right_click'
listening_for_bind = None
listening_popup = None
listening_cancelled = False

# We track pressed keys to detect if safety is being held
pressed_keys = set()

# ------------------------------------------------------------------------
# Utility: check if a point (x, y) is inside a given Tk window
# ------------------------------------------------------------------------
def in_tk_window(x, y, window):
    """
    Returns True if the global screen coords (x,y) fall inside
    the bounding box of the given Tk window.
    """
    if not window or not window.winfo_exists():
        return False
    left = window.winfo_rootx()
    top = window.winfo_rooty()
    right = left + window.winfo_width()
    bottom = top + window.winfo_height()
    return (left <= x <= right) and (top <= y <= bottom)

# ------------------------------------------------------------------------
# Worker threads to handle auto-clicking
# ------------------------------------------------------------------------
def left_click_thread():
    global left_click_active
    while left_click_active:
        # Check safety key
        if is_safety_held():
            time.sleep(0.01)
            continue
        
        if config['left_click']['mode'] == 'cps':
            # clicks per second
            cps = config['left_click']['cps']
            if cps <= 0:
                cps = 1
            interval = 1.0 / cps
        else:
            # delay in ms
            delay_ms = config['left_click']['delay']
            interval = max(0.001, delay_ms / 1000.0)
        
        # Perform a left click
        mouse_controller.click(MouseButton.left)
        time.sleep(interval)

def right_click_thread():
    global right_click_active
    while right_click_active:
        # Check safety key
        if is_safety_held():
            time.sleep(0.01)
            continue
        
        if config['right_click']['mode'] == 'cps':
            # clicks per second
            cps = config['right_click']['cps']
            if cps <= 0:
                cps = 1
            interval = 1.0 / cps
        else:
            # delay in ms
            delay_ms = config['right_click']['delay']
            interval = max(0.001, delay_ms / 1000.0)
        
        # Perform a right click
        mouse_controller.click(MouseButton.right)
        time.sleep(interval)

# ------------------------------------------------------------------------
# Safety key logic
# ------------------------------------------------------------------------
def is_safety_held():
    safety_str = config.get('safety_key', 'alt').lower()

    special_keys_map = {
        'alt': Key.alt_l, 'alt_l': Key.alt_l, 'alt_r': Key.alt_r,
        'ctrl': Key.ctrl_l, 'ctrl_l': Key.ctrl_l, 'ctrl_r': Key.ctrl_r,
        'shift': Key.shift_l, 'shift_l': Key.shift_l, 'shift_r': Key.shift_r,
        'esc': Key.esc, 'tab': Key.tab, 'caps_lock': Key.caps_lock,
    }

    if safety_str in special_keys_map:
        return special_keys_map[safety_str] in pressed_keys
    else:
        # If user typed a single character like 'a'
        for pk in pressed_keys:
            if isinstance(pk, KeyCode) and pk.char is not None:
                if pk.char.lower() == safety_str:
                    return True
    return False

# ------------------------------------------------------------------------
# Global hotkey toggles
# ------------------------------------------------------------------------
def parse_key_str(key_str):
    """
    Convert a string from config to something we can compare with 
    pressed keys or incoming events. Returns either:
      - A pynput.keyboard.Key or
      - A string representing a character (for KeyCode matching)
      - A pynput.mouse.Button if it's a mouse button
    """
    if not key_str:
        return None
    
    ks = key_str.lower()
    # handle mouse
    if ks.startswith('mouse'):
        # e.g. "mouse4" -> Button.x1, "mouse5" -> Button.x2
        # "middle", "left", "right"
        if ks == 'mouse4':
            return MouseButton.x1
        elif ks == 'mouse5':
            return MouseButton.x2
        elif ks == 'middle':
            return MouseButton.middle
        elif ks == 'left':
            return MouseButton.left
        elif ks == 'right':
            return MouseButton.right
    else:
        # handle keyboard special keys
        special_keys_map = {
            'alt': Key.alt_l, 'alt_l': Key.alt_l, 'alt_r': Key.alt_r,
            'ctrl': Key.ctrl_l, 'ctrl_l': Key.ctrl_l, 'ctrl_r': Key.ctrl_r,
            'shift': Key.shift_l, 'shift_l': Key.shift_l, 'shift_r': Key.shift_r,
            'esc': Key.esc, 'tab': Key.tab, 'caps_lock': Key.caps_lock,
            'f1': Key.f1, 'f2': Key.f2, 'f3': Key.f3, 'f4': Key.f4,
            'f5': Key.f5, 'f6': Key.f6, 'f7': Key.f7, 'f8': Key.f8,
            'f9': Key.f9, 'f10': Key.f10, 'f11': Key.f11, 'f12': Key.f12,
        }
        if ks in special_keys_map:
            return special_keys_map[ks]
        else:
            # assume single char
            return ks  # We'll compare with KeyCode(char=ks)
    return None

def key_matches_config(section, key):
    """
    Return True if the pressed keyboard key matches the toggle
    for the given config section.
    """
    bind_str = config[section]['bind']
    if not bind_str:
        return False

    parsed_bind = parse_key_str(bind_str)
    # If the bind is a mouse button, we skip here
    if isinstance(parsed_bind, mouse.Button):
        return False

    # Compare Key -> Key, or KeyCode(char=...) -> 'x'
    if isinstance(key, Key) and isinstance(parsed_bind, Key) and key == parsed_bind:
        return True
    if isinstance(key, KeyCode) and isinstance(parsed_bind, str):
        if key.char and key.char.lower() == parsed_bind.lower():
            return True

    return False

def mouse_matches_config(section, button, x, y):
    """
    Return True if the pressed mouse button matches the toggle
    for the given config section, and the click is outside the GUI.
    """
    # If the click is inside our main window or the "listening" popup, ignore
    if in_tk_window(x, y, root) or in_tk_window(x, y, listening_popup):
        return False
    
    bind_str = config[section]['bind']
    if not bind_str:
        return False

    parsed_bind = parse_key_str(bind_str)
    if isinstance(parsed_bind, mouse.Button) and button == parsed_bind:
        return True
    return False

# ------------------------------------------------------------------------
# Toggle logic
# ------------------------------------------------------------------------
def toggle_left_clicker():
    global left_click_active
    if left_click_active:
        left_click_active = False
    else:
        left_click_active = True
        t = threading.Thread(target=left_click_thread, daemon=True)
        t.start()
    refresh_ui()  # update button text

def toggle_right_clicker():
    global right_click_active
    if right_click_active:
        right_click_active = False
    else:
        right_click_active = True
        t = threading.Thread(target=right_click_thread, daemon=True)
        t.start()
    refresh_ui()  # update button text

# ------------------------------------------------------------------------
# Set a new bind
# ------------------------------------------------------------------------
def set_bind(section, bind_str):
    """
    Update config for 'section' with a new bind
    """
    config[section]['bind'] = bind_str
    save_config(config)
    refresh_ui()

# ------------------------------------------------------------------------
# Listening mode for new binds
# ------------------------------------------------------------------------
def start_listening(section):
    """
    Put the UI in "listening" mode to capture the next key or mouse press.
    """
    global listening_for_bind, listening_popup, listening_cancelled
    listening_for_bind = section
    listening_cancelled = False

    # Show a small top-level popup telling user to press a key/mouse
    listening_popup = tk.Toplevel(root)
    listening_popup.title("Listening...")
    listening_popup.geometry("300x100")
    label = tk.Label(listening_popup, text="Press a key or mouse button...\n(ESC to cancel)")
    label.pack(pady=10)

    cancel_button = tk.Button(listening_popup, text="Cancel", command=cancel_listening)
    cancel_button.pack()

    # Start a separate listener thread
    def listen_thread():
        with KeyboardListener(on_press=on_press, on_release=on_release) as kl, \
             mouse.Listener(on_click=on_click) as ml:
            kl.join()
            ml.stop()  # once keyboard stops, also stop mouse listener

    t = threading.Thread(target=listen_thread, daemon=True)
    t.start()

def cancel_listening():
    global listening_for_bind, listening_popup, listening_cancelled
    listening_cancelled = True
    listening_for_bind = None
    if listening_popup is not None:
        listening_popup.destroy()
        listening_popup = None

# ------------------------------------------------------------------------
# Callbacks for global key/mouse
# ------------------------------------------------------------------------
def on_press(key):
    global left_click_active, right_click_active

    # If user is in "listening" mode to set a new bind
    if listening_for_bind:
        if key == Key.esc:
            cancel_listening()
            return False  # stop the listener
        else:
            # Attempt to get a textual representation
            # E.g. Key.f6 -> 'f6', KeyCode(char='a') -> 'a'
            key_str = None
            if isinstance(key, Key):
                # e.g. Key.f6 => 'f6'
                # str(Key.f6) gives 'Key.f6', so we parse out the last part
                txt = str(key).replace('Key.', '')
                if txt:
                    key_str = txt
            elif isinstance(key, KeyCode):
                if key.char:
                    key_str = key.char
            if key_str:
                set_bind(listening_for_bind, key_str)
                cancel_listening()
            return False  # stop the listener so we don't record more
    else:
        # Normal operation: track pressed keys
        pressed_keys.add(key)
        # Check if this key matches left or right toggle
        if key_matches_config('left_click', key):
            toggle_left_clicker()
        if key_matches_config('right_click', key):
            toggle_right_clicker()

    return True

def on_release(key):
    if key in pressed_keys:
        pressed_keys.remove(key)

def on_click(x, y, button, pressed):
    """
    Global mouse click callback
    """
    global left_click_active, right_click_active

    # If user is listening for a new bind and it is a press, capture that
    # if it is outside the "Cancel" button, etc. 
    if listening_for_bind and pressed:
        # We set the bind to whichever mouse button was pressed
        btn_str = None
        if button == MouseButton.x1:
            btn_str = 'mouse4'
        elif button == MouseButton.x2:
            btn_str = 'mouse5'
        elif button == MouseButton.middle:
            btn_str = 'middle'
        elif button == MouseButton.left:
            btn_str = 'left'
        elif button == MouseButton.right:
            btn_str = 'right'
        if btn_str:
            set_bind(listening_for_bind, btn_str)
            cancel_listening()
        return False  # stop the listener

    # If not listening, check if it's a toggle press (on mouse release or press)
    # We'll only check toggles on "press == True"
    if pressed and not listening_for_bind:
        # If the click matches left/right toggle AND is outside the GUI
        if mouse_matches_config('left_click', button, x, y):
            toggle_left_clicker()
        if mouse_matches_config('right_click', button, x, y):
            toggle_right_clicker()

    return True

# ------------------------------------------------------------------------
# GUI
# ------------------------------------------------------------------------
def refresh_ui():
    # Update the entry fields from config
    left_mode_var.set(config['left_click']['mode'])
    left_cps_var.set(str(config['left_click']['cps']))
    left_delay_var.set(str(config['left_click']['delay']))
    left_bind_var.set(str(config['left_click']['bind'] or ''))

    right_mode_var.set(config['right_click']['mode'])
    right_cps_var.set(str(config['right_click']['cps']))
    right_delay_var.set(str(config['right_click']['delay']))
    right_bind_var.set(str(config['right_click']['bind'] or ''))

    safety_var.set(config['safety_key'])

    # Update toggle button text
    if left_click_active:
        left_toggle_btn.config(text="Stop Left")
    else:
        left_toggle_btn.config(text="Start Left")

    if right_click_active:
        right_toggle_btn.config(text="Stop Right")
    else:
        right_toggle_btn.config(text="Start Right")

def apply_changes():
    # Save changes from UI to config
    # left
    config['left_click']['mode'] = left_mode_var.get()
    try:
        config['left_click']['cps'] = int(left_cps_var.get())
    except:
        config['left_click']['cps'] = 10
    try:
        config['left_click']['delay'] = int(left_delay_var.get())
    except:
        config['left_click']['delay'] = 100

    # right
    config['right_click']['mode'] = right_mode_var.get()
    try:
        config['right_click']['cps'] = int(right_cps_var.get())
    except:
        config['right_click']['cps'] = 5
    try:
        config['right_click']['delay'] = int(right_delay_var.get())
    except:
        config['right_click']['delay'] = 200

    # safety
    config['safety_key'] = safety_var.get()

    save_config(config)
    refresh_ui()

root = tk.Tk()
root.title("Auto Clicker")
root.resizable(False, False)

# Left Click Frame
left_frame = ttk.LabelFrame(root, text="Left Click")
left_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

left_mode_var = tk.StringVar()
left_cps_var = tk.StringVar()
left_delay_var = tk.StringVar()
left_bind_var = tk.StringVar()

mode_label_left = ttk.Label(left_frame, text="Mode:")
mode_label_left.grid(row=0, column=0, padx=5, pady=5, sticky="e")
mode_cps_left = ttk.Radiobutton(left_frame, text="CPS", variable=left_mode_var, value='cps')
mode_cps_left.grid(row=0, column=1, padx=5, pady=5, sticky="w")
mode_delay_left = ttk.Radiobutton(left_frame, text="Delay(ms)", variable=left_mode_var, value='delay')
mode_delay_left.grid(row=0, column=2, padx=5, pady=5, sticky="w")

cps_label_left = ttk.Label(left_frame, text="CPS:")
cps_label_left.grid(row=1, column=0, padx=5, pady=5, sticky="e")
cps_entry_left = ttk.Entry(left_frame, textvariable=left_cps_var, width=6)
cps_entry_left.grid(row=1, column=1, padx=5, pady=5, sticky="w")

delay_label_left = ttk.Label(left_frame, text="Delay(ms):")
delay_label_left.grid(row=2, column=0, padx=5, pady=5, sticky="e")
delay_entry_left = ttk.Entry(left_frame, textvariable=left_delay_var, width=6)
delay_entry_left.grid(row=2, column=1, padx=5, pady=5, sticky="w")

bind_label_left = ttk.Label(left_frame, text="Bind:")
bind_label_left.grid(row=3, column=0, padx=5, pady=5, sticky="e")
bind_value_left = ttk.Label(left_frame, textvariable=left_bind_var, width=10, relief='sunken')
bind_value_left.grid(row=3, column=1, padx=5, pady=5, sticky="w")
bind_button_left = ttk.Button(left_frame, text="Set Bind", command=lambda: start_listening('left_click'))
bind_button_left.grid(row=3, column=2, padx=5, pady=5, sticky="w")

# Toggle Button for Left
left_toggle_btn = ttk.Button(left_frame, text="Start Left", command=toggle_left_clicker)
left_toggle_btn.grid(row=4, column=0, columnspan=3, pady=5)

# Right Click Frame
right_frame = ttk.LabelFrame(root, text="Right Click")
right_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

right_mode_var = tk.StringVar()
right_cps_var = tk.StringVar()
right_delay_var = tk.StringVar()
right_bind_var = tk.StringVar()

mode_label_right = ttk.Label(right_frame, text="Mode:")
mode_label_right.grid(row=0, column=0, padx=5, pady=5, sticky="e")
mode_cps_right = ttk.Radiobutton(right_frame, text="CPS", variable=right_mode_var, value='cps')
mode_cps_right.grid(row=0, column=1, padx=5, pady=5, sticky="w")
mode_delay_right = ttk.Radiobutton(right_frame, text="Delay(ms)", variable=right_mode_var, value='delay')
mode_delay_right.grid(row=0, column=2, padx=5, pady=5, sticky="w")

cps_label_right = ttk.Label(right_frame, text="CPS:")
cps_label_right.grid(row=1, column=0, padx=5, pady=5, sticky="e")
cps_entry_right = ttk.Entry(right_frame, textvariable=right_cps_var, width=6)
cps_entry_right.grid(row=1, column=1, padx=5, pady=5, sticky="w")

delay_label_right = ttk.Label(right_frame, text="Delay(ms):")
delay_label_right.grid(row=2, column=0, padx=5, pady=5, sticky="e")
delay_entry_right = ttk.Entry(right_frame, textvariable=right_delay_var, width=6)
delay_entry_right.grid(row=2, column=1, padx=5, pady=5, sticky="w")

bind_label_right = ttk.Label(right_frame, text="Bind:")
bind_label_right.grid(row=3, column=0, padx=5, pady=5, sticky="e")
bind_value_right = ttk.Label(right_frame, textvariable=right_bind_var, width=10, relief='sunken')
bind_value_right.grid(row=3, column=1, padx=5, pady=5, sticky="w")
bind_button_right = ttk.Button(right_frame, text="Set Bind", command=lambda: start_listening('right_click'))
bind_button_right.grid(row=3, column=2, padx=5, pady=5, sticky="w")

# Toggle Button for Right
right_toggle_btn = ttk.Button(right_frame, text="Start Right", command=toggle_right_clicker)
right_toggle_btn.grid(row=4, column=0, columnspan=3, pady=5)

# Safety Key
safety_frame = ttk.LabelFrame(root, text="Safety Key (Hold to Stop Auto-Click)")
safety_frame.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")

safety_var = tk.StringVar()
safety_label = ttk.Label(safety_frame, text="Safety Key:")
safety_label.grid(row=0, column=0, padx=5, pady=5, sticky="e")
safety_entry = ttk.Entry(safety_frame, textvariable=safety_var, width=10)
safety_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")

# Apply/Save button
apply_button = ttk.Button(root, text="Apply & Save", command=apply_changes)
apply_button.grid(row=3, column=0, padx=10, pady=10, sticky="nsew")

# Initialize UI
refresh_ui()

# ------------------------------------------------------------------------
# Start global listeners in a background thread
# ------------------------------------------------------------------------
def global_listener_thread():
    with KeyboardListener(on_press=on_press, on_release=on_release) as kl, \
         mouse.Listener(on_click=on_click) as ml:
        kl.join()
        ml.join()

t_listener = threading.Thread(target=global_listener_thread, daemon=True)
t_listener.start()

# ------------------------------------------------------------------------
# Main loop
# ------------------------------------------------------------------------
root.mainloop()