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
        'mode': 'cps',          # 'cps' or 'delay'
        'cps': 10,              # clicks per second
        'delay': 100,           # ms
        'bind': None,           # e.g. "f6", "mouse4", "middle", etc.
        'click_type': 'single', # 'single', 'double', 'triple'
        'activation': 'toggle'  # 'toggle' or 'hold'
    },
    'right_click': {
        'mode': 'delay',        # 'cps' or 'delay'
        'cps': 5,               # clicks per second
        'delay': 200,           # ms
        'bind': None,           # e.g. "mouse5", "r", "left", etc.
        'click_type': 'single', # 'single', 'double', 'triple'
        'activation': 'toggle'  # 'toggle' or 'hold'
    },
    'safety_key': 'alt',        # when this is held, no auto-click
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    else:
        return default_config

def save_config(cfg):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        yaml.safe_dump(cfg, f)

# ------------------------------------------------------------------------
# Global Variables
# ------------------------------------------------------------------------
config = load_config()
mouse_controller = MouseController()

# Left/right clicker states
left_click_active = False
right_click_active = False

# For capturing new binds
listening_for_bind = None
listening_popup = None
listening_cancelled = False

# Track pressed keys and pressed mouse buttons
pressed_keys = set()
pressed_mouse_buttons = set()

# ------------------------------------------------------------------------
# Check if a point (x, y) is inside a given Tk window
# ------------------------------------------------------------------------
def in_tk_window(x, y, window):
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
        # Safety check
        if is_safety_held():
            time.sleep(0.01)
            continue
        
        # Interval
        if config['left_click']['mode'] == 'cps':
            cps = config['left_click'].get('cps', 10)
            if cps <= 0: 
                cps = 1
            interval = 1.0 / cps
        else:  # 'delay'
            delay_ms = config['left_click'].get('delay', 100)
            interval = max(0.001, delay_ms / 1000.0)

        # Single/double/triple
        ctype = config['left_click'].get('click_type', 'single').lower()
        click_count = 1
        if ctype == 'double':
            click_count = 2
        elif ctype == 'triple':
            click_count = 3

        # Perform the click
        mouse_controller.click(MouseButton.left, click_count)
        time.sleep(interval)

def right_click_thread():
    global right_click_active
    while right_click_active:
        # Safety check
        if is_safety_held():
            time.sleep(0.01)
            continue
        
        # Interval
        if config['right_click']['mode'] == 'cps':
            cps = config['right_click'].get('cps', 5)
            if cps <= 0: 
                cps = 1
            interval = 1.0 / cps
        else:  # 'delay'
            delay_ms = config['right_click'].get('delay', 200)
            interval = max(0.001, delay_ms / 1000.0)

        # Single/double/triple
        ctype = config['right_click'].get('click_type', 'single').lower()
        click_count = 1
        if ctype == 'double':
            click_count = 2
        elif ctype == 'triple':
            click_count = 3

        # Perform the click
        mouse_controller.click(MouseButton.right, click_count)
        time.sleep(interval)

# ------------------------------------------------------------------------
# Safety key logic
# ------------------------------------------------------------------------
def is_safety_held():
    """True if the configured safety key is currently held."""
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
        # Single char?
        for pk in pressed_keys:
            if isinstance(pk, KeyCode) and pk.char:
                if pk.char.lower() == safety_str:
                    return True
    return False

# ------------------------------------------------------------------------
# Parsing bind strings into pynput objects
# ------------------------------------------------------------------------
def parse_key_str(key_str):
    """Convert a string like 'f6', 'mouse4', 'middle', 'left', 'a' into a Key or Button object."""
    if not key_str:
        return None
    ks = key_str.lower()
    # Mouse?
    if ks.startswith('mouse'):
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
        # Keyboard
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
            # Single char
            return ks
    return None

# ------------------------------------------------------------------------
# Activation / toggling
# ------------------------------------------------------------------------
def start_left_clicker():
    global left_click_active
    if not left_click_active:
        left_click_active = True
        t = threading.Thread(target=left_click_thread, daemon=True)
        t.start()
    refresh_ui()

def stop_left_clicker():
    global left_click_active
    left_click_active = False
    refresh_ui()

def start_right_clicker():
    global right_click_active
    if not right_click_active:
        right_click_active = True
        t = threading.Thread(target=right_click_thread, daemon=True)
        t.start()
    refresh_ui()

def stop_right_clicker():
    global right_click_active
    right_click_active = False
    refresh_ui()

def toggle_left_clicker():
    if left_click_active:
        stop_left_clicker()
    else:
        start_left_clicker()

def toggle_right_clicker():
    if right_click_active:
        stop_right_clicker()
    else:
        start_right_clicker()

# ------------------------------------------------------------------------
# Checking whether a pressed key/mouse is for left or right, and how to react
# ------------------------------------------------------------------------
def matches_bind(section, incoming):
    """Return True if 'incoming' (Key or Button) matches the config bind for 'section'."""
    bind_str = config[section]['bind']
    if not bind_str:
        return False
    parsed = parse_key_str(bind_str)

    # If it's a mouse button from config
    if isinstance(parsed, mouse.Button):
        return (parsed == incoming)
    # If it's a keyboard key from config
    elif isinstance(parsed, Key):
        return (parsed == incoming)
    # If it's a single-char (like 'a', 'b', etc.)
    elif isinstance(parsed, str):
        # For keyboard, we get KeyCode(char='x') in 'incoming'
        if isinstance(incoming, KeyCode) and incoming.char:
            return (incoming.char.lower() == parsed.lower())
    return False

# ------------------------------------------------------------------------
# Binding logic
# ------------------------------------------------------------------------
def set_bind(section, bind_str):
    config[section]['bind'] = bind_str
    save_config(config)
    refresh_ui()

def start_listening(section):
    global listening_for_bind, listening_popup, listening_cancelled
    listening_for_bind = section
    listening_cancelled = False

    listening_popup = tk.Toplevel(root)
    listening_popup.title("Listening...")
    listening_popup.geometry("300x100")
    label = tk.Label(listening_popup, text="Press a key or mouse button...\n(ESC to cancel)")
    label.pack(pady=10)

    btn_cancel = tk.Button(listening_popup, text="Cancel", command=cancel_listening)
    btn_cancel.pack()

    def listen_thread():
        with KeyboardListener(on_press=on_press, on_release=on_release) as kl, \
             mouse.Listener(on_click=on_click) as ml:
            kl.join()
            ml.stop()

    t = threading.Thread(target=listen_thread, daemon=True)
    t.start()

def cancel_listening():
    global listening_for_bind, listening_popup, listening_cancelled
    listening_cancelled = True
    listening_for_bind = None
    if listening_popup and listening_popup.winfo_exists():
        listening_popup.destroy()
        listening_popup = None

# ------------------------------------------------------------------------
# Global callback: Keyboard
# ------------------------------------------------------------------------
def on_press(key):
    """Called when a key is pressed globally."""
    if listening_for_bind:
        # In "listening" mode
        if key == Key.esc:
            cancel_listening()
            return False
        else:
            # Convert the pressed key to a string
            key_str = None
            if isinstance(key, Key):
                # e.g. Key.f6 => 'f6'
                txt = str(key).replace('Key.', '')
                if txt:
                    key_str = txt
            elif isinstance(key, KeyCode) and key.char:
                key_str = key.char
            
            if key_str:
                set_bind(listening_for_bind, key_str)
                cancel_listening()
            return False
    else:
        pressed_keys.add(key)
        # Check left or right config
        # If "activation" is "toggle" => we do toggle on press
        # If "activation" is "hold" => we start on press, stop on release
        # (but only if it matches the config bind)
        if matches_bind('left_click', key):
            if config['left_click'].get('activation', 'toggle') == 'toggle':
                toggle_left_clicker()
            else:  # hold mode
                start_left_clicker()
        elif matches_bind('right_click', key):
            if config['right_click'].get('activation', 'toggle') == 'toggle':
                toggle_right_clicker()
            else:  # hold mode
                start_right_clicker()
    return True

def on_release(key):
    """Called when a key is released globally."""
    if key in pressed_keys:
        pressed_keys.remove(key)

    # If we are in "hold" mode for left/right, releasing the bind stops it.
    if not listening_for_bind:
        if matches_bind('left_click', key):
            if config['left_click'].get('activation', 'toggle') == 'hold':
                stop_left_clicker()
        elif matches_bind('right_click', key):
            if config['right_click'].get('activation', 'toggle') == 'hold':
                stop_right_clicker()

# ------------------------------------------------------------------------
# Global callback: Mouse
# ------------------------------------------------------------------------
def on_click(x, y, button, pressed):
    """Called on mouse click globally."""
    if listening_for_bind and pressed:
        # If capturing a new bind
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

    if not listening_for_bind:
        # If this click is inside the GUI, ignore
        if in_tk_window(x, y, root) or in_tk_window(x, y, listening_popup):
            return True

        # Normal operation: Check if matches left/right
        # Then see if activation is toggle or hold
        if matches_bind('left_click', button):
            if pressed:
                if config['left_click'].get('activation', 'toggle') == 'toggle':
                    toggle_left_clicker()
                else:  # hold
                    start_left_clicker()
            else:
                # mouse button released
                if config['left_click'].get('activation', 'toggle') == 'hold':
                    stop_left_clicker()

        elif matches_bind('right_click', button):
            if pressed:
                if config['right_click'].get('activation', 'toggle') == 'toggle':
                    toggle_right_clicker()
                else:  # hold
                    start_right_clicker()
            else:
                if config['right_click'].get('activation', 'toggle') == 'hold':
                    stop_right_clicker()

    return True

# ------------------------------------------------------------------------
# GUI
# ------------------------------------------------------------------------
root = tk.Tk()
root.title("Auto Clicker")
root.resizable(False, False)

# -------------
# LEFT CLICK UI
# -------------
left_frame = ttk.LabelFrame(root, text="Left Click")
left_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

left_mode_var = tk.StringVar()
left_cps_var = tk.StringVar()
left_delay_var = tk.StringVar()
left_bind_var = tk.StringVar()
left_click_type_var = tk.StringVar()
left_activation_var = tk.StringVar()

ttk.Label(left_frame, text="Mode:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
ttk.Radiobutton(left_frame, text="CPS", variable=left_mode_var, value='cps').grid(row=0, column=1, padx=5, pady=5, sticky="w")
ttk.Radiobutton(left_frame, text="Delay(ms)", variable=left_mode_var, value='delay').grid(row=0, column=2, padx=5, pady=5, sticky="w")

ttk.Label(left_frame, text="CPS:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
tk.Entry(left_frame, textvariable=left_cps_var, width=6).grid(row=1, column=1, padx=5, pady=5, sticky="w")

ttk.Label(left_frame, text="Delay(ms):").grid(row=2, column=0, padx=5, pady=5, sticky="e")
tk.Entry(left_frame, textvariable=left_delay_var, width=6).grid(row=2, column=1, padx=5, pady=5, sticky="w")

ttk.Label(left_frame, text="Bind:").grid(row=3, column=0, padx=5, pady=5, sticky="e")
ttk.Label(left_frame, textvariable=left_bind_var, width=10, relief='sunken').grid(row=3, column=1, padx=5, pady=5, sticky="w")
ttk.Button(left_frame, text="Set Bind", command=lambda: start_listening('left_click')).grid(row=3, column=2, padx=5, pady=5, sticky="w")

ttk.Label(left_frame, text="Click Type:").grid(row=4, column=0, padx=5, pady=5, sticky="e")
cb_left_type = ttk.Combobox(left_frame, textvariable=left_click_type_var, values=["single", "double", "triple"], state="readonly", width=7)
cb_left_type.grid(row=4, column=1, padx=5, pady=5, sticky="w")

ttk.Label(left_frame, text="Activation:").grid(row=5, column=0, padx=5, pady=5, sticky="e")
cb_left_activation = ttk.Combobox(left_frame, textvariable=left_activation_var, values=["toggle", "hold"], state="readonly", width=7)
cb_left_activation.grid(row=5, column=1, padx=5, pady=5, sticky="w")

left_toggle_btn = ttk.Button(left_frame, text="Start Left", command=toggle_left_clicker)
left_toggle_btn.grid(row=6, column=0, columnspan=3, pady=5)

# --------------
# RIGHT CLICK UI
# --------------
right_frame = ttk.LabelFrame(root, text="Right Click")
right_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

right_mode_var = tk.StringVar()
right_cps_var = tk.StringVar()
right_delay_var = tk.StringVar()
right_bind_var = tk.StringVar()
right_click_type_var = tk.StringVar()
right_activation_var = tk.StringVar()

ttk.Label(right_frame, text="Mode:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
ttk.Radiobutton(right_frame, text="CPS", variable=right_mode_var, value='cps').grid(row=0, column=1, padx=5, pady=5, sticky="w")
ttk.Radiobutton(right_frame, text="Delay(ms)", variable=right_mode_var, value='delay').grid(row=0, column=2, padx=5, pady=5, sticky="w")

ttk.Label(right_frame, text="CPS:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
tk.Entry(right_frame, textvariable=right_cps_var, width=6).grid(row=1, column=1, padx=5, pady=5, sticky="w")

ttk.Label(right_frame, text="Delay(ms):").grid(row=2, column=0, padx=5, pady=5, sticky="e")
tk.Entry(right_frame, textvariable=right_delay_var, width=6).grid(row=2, column=1, padx=5, pady=5, sticky="w")

ttk.Label(right_frame, text="Bind:").grid(row=3, column=0, padx=5, pady=5, sticky="e")
ttk.Label(right_frame, textvariable=right_bind_var, width=10, relief='sunken').grid(row=3, column=1, padx=5, pady=5, sticky="w")
ttk.Button(right_frame, text="Set Bind", command=lambda: start_listening('right_click')).grid(row=3, column=2, padx=5, pady=5, sticky="w")

ttk.Label(right_frame, text="Click Type:").grid(row=4, column=0, padx=5, pady=5, sticky="e")
cb_right_type = ttk.Combobox(right_frame, textvariable=right_click_type_var, values=["single", "double", "triple"], state="readonly", width=7)
cb_right_type.grid(row=4, column=1, padx=5, pady=5, sticky="w")

ttk.Label(right_frame, text="Activation:").grid(row=5, column=0, padx=5, pady=5, sticky="e")
cb_right_activation = ttk.Combobox(right_frame, textvariable=right_activation_var, values=["toggle", "hold"], state="readonly", width=7)
cb_right_activation.grid(row=5, column=1, padx=5, pady=5, sticky="w")

right_toggle_btn = ttk.Button(right_frame, text="Start Right", command=toggle_right_clicker)
right_toggle_btn.grid(row=6, column=0, columnspan=3, pady=5)

# --------------
# SAFETY KEY UI
# --------------
safety_frame = ttk.LabelFrame(root, text="Safety Key (Hold to Pause Clicking)")
safety_frame.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")

safety_var = tk.StringVar()
ttk.Label(safety_frame, text="Safety Key:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
tk.Entry(safety_frame, textvariable=safety_var, width=10).grid(row=0, column=1, padx=5, pady=5, sticky="w")

# --------------
# APPLY & SAVE
# --------------
def apply_changes():
    # Left
    config['left_click']['mode'] = left_mode_var.get()
    try:
        config['left_click']['cps'] = int(left_cps_var.get())
    except ValueError:
        config['left_click']['cps'] = 10

    try:
        config['left_click']['delay'] = int(left_delay_var.get())
    except ValueError:
        config['left_click']['delay'] = 100
    
    config['left_click']['click_type'] = left_click_type_var.get()
    config['left_click']['activation'] = left_activation_var.get()

    # Right
    config['right_click']['mode'] = right_mode_var.get()
    try:
        config['right_click']['cps'] = int(right_cps_var.get())
    except ValueError:
        config['right_click']['cps'] = 5

    try:
        config['right_click']['delay'] = int(right_delay_var.get())
    except ValueError:
        config['right_click']['delay'] = 200
    
    config['right_click']['click_type'] = right_click_type_var.get()
    config['right_click']['activation'] = right_activation_var.get()

    # Safety
    config['safety_key'] = safety_var.get()

    save_config(config)
    refresh_ui()

apply_btn = ttk.Button(root, text="Apply & Save", command=apply_changes)
apply_btn.grid(row=3, column=0, padx=10, pady=10, sticky="nsew")

# --------------
# Refresh UI
# --------------
def refresh_ui():
    # Left
    left_mode_var.set(config['left_click']['mode'])
    left_cps_var.set(str(config['left_click']['cps']))
    left_delay_var.set(str(config['left_click']['delay']))
    left_bind_var.set(str(config['left_click']['bind'] or ''))
    left_click_type_var.set(config['left_click'].get('click_type', 'single'))
    left_activation_var.set(config['left_click'].get('activation', 'toggle'))

    # Right
    right_mode_var.set(config['right_click']['mode'])
    right_cps_var.set(str(config['right_click']['cps']))
    right_delay_var.set(str(config['right_click']['delay']))
    right_bind_var.set(str(config['right_click']['bind'] or ''))
    right_click_type_var.set(config['right_click'].get('click_type', 'single'))
    right_activation_var.set(config['right_click'].get('activation', 'toggle'))

    safety_var.set(config['safety_key'])

    # Button text
    left_toggle_btn.config(text="Stop Left" if left_click_active else "Start Left")
    right_toggle_btn.config(text="Stop Right" if right_click_active else "Start Right")

refresh_ui()

# --------------
# Global listener thread
# --------------
def global_listener_thread():
    with KeyboardListener(on_press=on_press, on_release=on_release) as kl, \
         mouse.Listener(on_click=on_click) as ml:
        kl.join()
        ml.join()

t_listener = threading.Thread(target=global_listener_thread, daemon=True)
t_listener.start()

root.mainloop()