import tkinter as tk
from tkinter import ttk
import threading
import time
import yaml
import os

from pynput import mouse, keyboard
from pynput.mouse import Controller as MouseController, Button as MouseButton
from pynput.keyboard import Key, Listener as KeyboardListener, KeyCode

# -- Store config.yaml
APPDATA_DIR = os.path.join(os.environ['APPDATA'], 'AutoClickerByTheNano')
os.makedirs(APPDATA_DIR, exist_ok=True)
CONFIG_FILE = os.path.join(APPDATA_DIR, 'config.yaml')

# -- Default config
default_config = {
    'left_click': {
        'mode': 'cps',          # 'cps' or 'delay'
        'cps': 10,              # clicks per second
        'delay': 100,           # ms
        'bind': None,           # e.g. "f6", "mouse4", "middle", ...
        'click_type': 'single', # 'single', 'double', 'triple'
        'activation': 'toggle'  # 'toggle' or 'hold'
    },
    'right_click': {
        'mode': 'delay',        # 'cps' or 'delay'
        'cps': 5,               # clicks per second
        'delay': 200,           # ms
        'bind': None,           # e.g. "mouse5", "r", "left", ...
        'click_type': 'single', # 'single', 'double', 'triple'
        'activation': 'toggle'  # 'toggle' or 'hold'
    },
    'safety_key': 'alt',        # hold this to pause clicking
}

# -- Load / Save config
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    else:
        return default_config

def save_config(cfg):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        yaml.safe_dump(cfg, f)

config = load_config()
mouse_controller = MouseController()

left_click_active = False
right_click_active = False

listening_for_bind = None
listening_popup = None

pressed_keys = set()

def in_tk_window(x, y, window):
    """Return True if (x,y) is inside 'window'."""
    if not window or not window.winfo_exists():
        return False
    l = window.winfo_rootx()
    t = window.winfo_rooty()
    r = l + window.winfo_width()
    b = t + window.winfo_height()
    return (l <= x <= r) and (t <= y <= b)

def left_click_thread():
    global left_click_active
    while left_click_active:
        if is_safety_held():
            time.sleep(0.01)
            continue
        
        if config['left_click']['mode'] == 'cps':
            cps = config['left_click'].get('cps', 10)
            if cps <= 0:
                cps = 1
            interval = 1.0 / cps
        else:
            delay_ms = config['left_click'].get('delay', 100)
            interval = max(0.001, delay_ms / 1000.0)

        ctype = config['left_click'].get('click_type', 'single').lower()
        click_count = 1
        if ctype == 'double':
            click_count = 2
        elif ctype == 'triple':
            click_count = 3

        mouse_controller.click(MouseButton.left, click_count)
        time.sleep(interval)

def right_click_thread():
    global right_click_active
    while right_click_active:
        if is_safety_held():
            time.sleep(0.01)
            continue
        
        if config['right_click']['mode'] == 'cps':
            cps = config['right_click'].get('cps', 5)
            if cps <= 0:
                cps = 1
            interval = 1.0 / cps
        else:  
            delay_ms = config['right_click'].get('delay', 200)
            interval = max(0.001, delay_ms / 1000.0)

        ctype = config['right_click'].get('click_type', 'single').lower()
        click_count = 1
        if ctype == 'double':
            click_count = 2
        elif ctype == 'triple':
            click_count = 3

        mouse_controller.click(MouseButton.right, click_count)
        time.sleep(interval)

def is_safety_held():
    """Return True if the safety key is being held."""
    safety_str = config.get('safety_key', 'alt').lower()
    special_keys_map = {
        'alt': Key.alt_l, 'alt_l': Key.alt_l, 'alt_r': Key.alt_r,
        'ctrl': Key.ctrl_l, 'ctrl_l': Key.ctrl_l, 'ctrl_r': Key.ctrl_r,
        'shift': Key.shift_l, 'shift_l': Key.shift_l, 'shift_r': Key.shift_r,
        'esc': Key.esc, 'tab': Key.tab, 'caps_lock': Key.caps_lock,
    }
    if safety_str in special_keys_map:
        return (special_keys_map[safety_str] in pressed_keys)
    else:
        # single character
        for pk in pressed_keys:
            if isinstance(pk, KeyCode) and pk.char:
                if pk.char.lower() == safety_str:
                    return True
    return False

def start_left_clicker():
    global left_click_active
    if not left_click_active:
        left_click_active = True
        threading.Thread(target=left_click_thread, daemon=True).start()
    refresh_ui()

def stop_left_clicker():
    global left_click_active
    left_click_active = False
    refresh_ui()

def start_right_clicker():
    global right_click_active
    if not right_click_active:
        right_click_active = True
        threading.Thread(target=right_click_thread, daemon=True).start()
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

def parse_key_str(key_str):
    """Examples: 'f6' -> Key.f6, 'mouse4' -> MouseButton.x1, 'a' -> 'a' """
    if not key_str:
        return None
    ks = key_str.lower()
    
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
            return ks
    return None

def matches_bind(section, incoming):
    """Return True if 'incoming' (Key or MouseButton) matches config[section]['bind']. """
    bind_str = config[section]['bind']
    if not bind_str:
        return False
    parsed = parse_key_str(bind_str)

    if isinstance(parsed, mouse.Button):
        return parsed == incoming
    elif isinstance(parsed, Key):
        return parsed == incoming
    elif isinstance(parsed, str):
        if isinstance(incoming, KeyCode) and incoming.char:
            return (incoming.char.lower() == parsed.lower())
    return False

def set_bind(section, bind_str):
    config[section]['bind'] = bind_str
    save_config(config)       # immediate save
    refresh_ui()

def clear_bind(section):
    config[section]['bind'] = None
    save_config(config)
    refresh_ui()

def start_listening(section):
    global listening_for_bind, listening_popup
    listening_for_bind = section

    listening_popup = tk.Toplevel(root)
    listening_popup.title("Listening...")
    listening_popup.geometry("300x100")
    lbl = tk.Label(listening_popup, text="Press a key or mouse button...\n(Press ESC to cancel)")
    lbl.pack(pady=10)

    btn_cancel = tk.Button(listening_popup, text="Cancel", command=cancel_listening)
    btn_cancel.pack()

def cancel_listening():
    global listening_for_bind, listening_popup
    listening_for_bind = None
    if listening_popup and listening_popup.winfo_exists():
        listening_popup.destroy()
        listening_popup = None

def on_press(key):
    if listening_for_bind:
        if key == Key.esc:
            # Cancel
            cancel_listening()
        else:
            k_str = None
            if isinstance(key, Key):
                txt = str(key).replace('Key.', '')
                if txt:
                    k_str = txt
            elif isinstance(key, KeyCode) and key.char:
                k_str = key.char
            
            if k_str:
                set_bind(listening_for_bind, k_str)
                cancel_listening()
        return

    pressed_keys.add(key)
    
    if matches_bind('left_click', key):
        if config['left_click']['activation'] == 'toggle':
            toggle_left_clicker()
        else:
            start_left_clicker()

    elif matches_bind('right_click', key):
        if config['right_click']['activation'] == 'toggle':
            toggle_right_clicker()
        else:
            start_right_clicker()

def on_release(key):
    if key in pressed_keys:
        pressed_keys.remove(key)

    if listening_for_bind:
        return 

    if matches_bind('left_click', key):
        if config['left_click']['activation'] == 'hold':
            stop_left_clicker()
    elif matches_bind('right_click', key):
        if config['right_click']['activation'] == 'hold':
            stop_right_clicker()

def on_click(x, y, button, pressed):
    if listening_for_bind:
        if pressed:  
            if button == mouse.Button.x1:
                set_bind(listening_for_bind, 'mouse4')
            elif button == mouse.Button.x2:
                set_bind(listening_for_bind, 'mouse5')
            elif button == mouse.Button.middle:
                set_bind(listening_for_bind, 'middle')
            elif button == mouse.Button.left:
                set_bind(listening_for_bind, 'left')
            elif button == mouse.Button.right:
                set_bind(listening_for_bind, 'right')
            cancel_listening()
        return

    if not pressed:
        if matches_bind('left_click', button):
            if config['left_click']['activation'] == 'hold':
                stop_left_clicker()
        elif matches_bind('right_click', button):
            if config['right_click']['activation'] == 'hold':
                stop_right_clicker()
    else:
        if matches_bind('left_click', button):
            if config['left_click']['activation'] == 'toggle':
                toggle_left_clicker()
            else:
                start_left_clicker()
        elif matches_bind('right_click', button):
            if config['right_click']['activation'] == 'toggle':
                toggle_right_clicker()
            else:
                start_right_clicker()

root = tk.Tk()
root.title("Auto Clicker")

try:
    root.iconbitmap("impl/icon.ico")
except:
    pass

root.resizable(False, False)

def apply_changes(*_):
    """
    Immediately read all UI widgets into 'config' and save. 
    `_` parameter is for event-handlers that pass extra args (ignored).
    """
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

    config['safety_key'] = safety_var.get()

    save_config(config)
    refresh_ui()

# -- LEFT CLICK
left_frame = ttk.LabelFrame(root, text="Left Click")
left_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

left_mode_var = tk.StringVar(value=config['left_click']['mode'])
left_cps_var = tk.StringVar(value=str(config['left_click']['cps']))
left_delay_var = tk.StringVar(value=str(config['left_click']['delay']))
left_bind_var = tk.StringVar(value=str(config['left_click']['bind'] or ''))
left_click_type_var = tk.StringVar(value=config['left_click']['click_type'])
left_activation_var = tk.StringVar(value=config['left_click']['activation'])

tk.Label(left_frame, text="Mode:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
r_left_cps = ttk.Radiobutton(left_frame, text="CPS", variable=left_mode_var, value='cps', command=apply_changes)
r_left_cps.grid(row=0, column=1, padx=5, pady=5, sticky="w")
r_left_delay = ttk.Radiobutton(left_frame, text="Delay(ms)", variable=left_mode_var, value='delay', command=apply_changes)
r_left_delay.grid(row=0, column=2, padx=5, pady=5, sticky="w")

tk.Label(left_frame, text="CPS:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
e_left_cps = tk.Entry(left_frame, textvariable=left_cps_var, width=6)
e_left_cps.grid(row=1, column=1, padx=5, pady=5, sticky="w")
# When user finishes editing or leaves the field, apply changes
e_left_cps.bind("<FocusOut>", apply_changes)
e_left_cps.bind("<Return>", apply_changes)

tk.Label(left_frame, text="Delay(ms):").grid(row=2, column=0, padx=5, pady=5, sticky="e")
e_left_delay = tk.Entry(left_frame, textvariable=left_delay_var, width=6)
e_left_delay.grid(row=2, column=1, padx=5, pady=5, sticky="w")
e_left_delay.bind("<FocusOut>", apply_changes)
e_left_delay.bind("<Return>", apply_changes)

tk.Label(left_frame, text="Bind:").grid(row=3, column=0, padx=5, pady=5, sticky="e")
lbl_left_bind = tk.Label(left_frame, textvariable=left_bind_var, width=10, relief='sunken')
lbl_left_bind.grid(row=3, column=1, padx=5, pady=5, sticky="w")

# Set Bind & Clear
bind_buttons_left = tk.Frame(left_frame)
bind_buttons_left.grid(row=3, column=2, padx=5, pady=5, sticky="w")

ttk.Button(bind_buttons_left, text="Set Bind", command=lambda: start_listening('left_click')).grid(row=0, column=0, padx=2)
ttk.Button(bind_buttons_left, text="Clear", command=lambda: clear_bind('left_click')).grid(row=0, column=1, padx=2)

tk.Label(left_frame, text="Click Type:").grid(row=4, column=0, padx=5, pady=5, sticky="e")
cb_left_type = ttk.Combobox(left_frame, textvariable=left_click_type_var, values=["single","double","triple"], state="readonly", width=7)
cb_left_type.grid(row=4, column=1, padx=5, pady=5, sticky="w")
cb_left_type.bind("<<ComboboxSelected>>", apply_changes)

tk.Label(left_frame, text="Activation:").grid(row=5, column=0, padx=5, pady=5, sticky="e")
cb_left_activation = ttk.Combobox(left_frame, textvariable=left_activation_var, values=["toggle","hold"], state="readonly", width=7)
cb_left_activation.grid(row=5, column=1, padx=5, pady=5, sticky="w")
cb_left_activation.bind("<<ComboboxSelected>>", apply_changes)

btn_left_toggle = ttk.Button(left_frame, text="Start Left", command=toggle_left_clicker)
btn_left_toggle.grid(row=6, column=0, columnspan=3, pady=5)

# -- RIGHT CLICK
right_frame = ttk.LabelFrame(root, text="Right Click")
right_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

right_mode_var = tk.StringVar(value=config['right_click']['mode'])
right_cps_var = tk.StringVar(value=str(config['right_click']['cps']))
right_delay_var = tk.StringVar(value=str(config['right_click']['delay']))
right_bind_var = tk.StringVar(value=str(config['right_click']['bind'] or ''))
right_click_type_var = tk.StringVar(value=config['right_click']['click_type'])
right_activation_var = tk.StringVar(value=config['right_click']['activation'])

tk.Label(right_frame, text="Mode:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
r_right_cps = ttk.Radiobutton(right_frame, text="CPS", variable=right_mode_var, value='cps', command=apply_changes)
r_right_cps.grid(row=0, column=1, padx=5, pady=5, sticky="w")
r_right_delay = ttk.Radiobutton(right_frame, text="Delay(ms)", variable=right_mode_var, value='delay', command=apply_changes)
r_right_delay.grid(row=0, column=2, padx=5, pady=5, sticky="w")

tk.Label(right_frame, text="CPS:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
e_right_cps = tk.Entry(right_frame, textvariable=right_cps_var, width=6)
e_right_cps.grid(row=1, column=1, padx=5, pady=5, sticky="w")
e_right_cps.bind("<FocusOut>", apply_changes)
e_right_cps.bind("<Return>", apply_changes)

tk.Label(right_frame, text="Delay(ms):").grid(row=2, column=0, padx=5, pady=5, sticky="e")
e_right_delay = tk.Entry(right_frame, textvariable=right_delay_var, width=6)
e_right_delay.grid(row=2, column=1, padx=5, pady=5, sticky="w")
e_right_delay.bind("<FocusOut>", apply_changes)
e_right_delay.bind("<Return>", apply_changes)

tk.Label(right_frame, text="Bind:").grid(row=3, column=0, padx=5, pady=5, sticky="e")
lbl_right_bind = tk.Label(right_frame, textvariable=right_bind_var, width=10, relief='sunken')
lbl_right_bind.grid(row=3, column=1, padx=5, pady=5, sticky="w")

bind_buttons_right = tk.Frame(right_frame)
bind_buttons_right.grid(row=3, column=2, padx=5, pady=5, sticky="w")
ttk.Button(bind_buttons_right, text="Set Bind", command=lambda: start_listening('right_click')).grid(row=0, column=0, padx=2)
ttk.Button(bind_buttons_right, text="Clear", command=lambda: clear_bind('right_click')).grid(row=0, column=1, padx=2)

tk.Label(right_frame, text="Click Type:").grid(row=4, column=0, padx=5, pady=5, sticky="e")
cb_right_type = ttk.Combobox(right_frame, textvariable=right_click_type_var, values=["single","double","triple"], state="readonly", width=7)
cb_right_type.grid(row=4, column=1, padx=5, pady=5, sticky="w")
cb_right_type.bind("<<ComboboxSelected>>", apply_changes)

tk.Label(right_frame, text="Activation:").grid(row=5, column=0, padx=5, pady=5, sticky="e")
cb_right_activation = ttk.Combobox(right_frame, textvariable=right_activation_var, values=["toggle","hold"], state="readonly", width=7)
cb_right_activation.grid(row=5, column=1, padx=5, pady=5, sticky="w")
cb_right_activation.bind("<<ComboboxSelected>>", apply_changes)

btn_right_toggle = ttk.Button(right_frame, text="Start Right", command=toggle_right_clicker)
btn_right_toggle.grid(row=6, column=0, columnspan=3, pady=5)

# -- SAFETY KEY
safety_frame = ttk.LabelFrame(root, text="Safety Key (Hold to Pause Clicking)")
safety_frame.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")

safety_var = tk.StringVar(value=config['safety_key'])
tk.Label(safety_frame, text="Safety Key:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
e_safety = tk.Entry(safety_frame, textvariable=safety_var, width=10)
e_safety.grid(row=0, column=1, padx=5, pady=5, sticky="w")
e_safety.bind("<FocusOut>", apply_changes)
e_safety.bind("<Return>", apply_changes)

# -- Refresh UI: updates label text & toggle button text
def refresh_ui():
    left_bind_var.set(str(config['left_click']['bind'] or ''))
    right_bind_var.set(str(config['right_click']['bind'] or ''))

    if left_click_active:
        btn_left_toggle.config(text="Stop Left")
    else:
        btn_left_toggle.config(text="Start Left")

    if right_click_active:
        btn_right_toggle.config(text="Stop Right")
    else:
        btn_right_toggle.config(text="Start Right")

# Initial refresh
refresh_ui()

# -- Global listenear thread
def global_listener_thread():
    with KeyboardListener(on_press=on_press, on_release=on_release) as kl, \
         mouse.Listener(on_click=on_click) as ml:
        kl.join()
        ml.join()

t_listener = threading.Thread(target=global_listener_thread, daemon=True)
t_listener.start()

root.mainloop()