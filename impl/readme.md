# Auto Clicker

An advanced, **global hotkey**-based auto-clicker that offers multiple customization options, saves its config in `AppData`, and bundles into a single EXE. This auto-clicker:

1. **Globally Hooks** Keyboard & Mouse
2. **Supports** Left & Right click
3. **Single**, **Double**, or **Triple** clicks
4. **CPS** (Clicks Per Second) or **Delay** (ms) mode
5. **Toggle** or **Hold** activation
6. **Safety Key** – hold to temporarily pause auto-clicking

## Key Features

1. **Global Hotkeys**  
   - Bind any keyboard key (`F1`..`F12`, letters, etc.) or mouse button (`mouse4`, `mouse5`, `middle`, etc.) to toggle or hold.  
   - Works even if the auto-clicker’s window is minimized or unfocused.

2. **Left & Right Click**  
   - Separate configurations for left-click and right-click auto-clicking.  
   - Each can be toggled independently.

3. **Click Type**  
   - **Single**: 1 click per interval  
   - **Double**: 2 clicks per interval  
   - **Triple**: 3 clicks per interval  

4. **CPS or Delay**  
   - **CPS**: for example, 10 means 10 clicks per second (0.1 seconds between clicks).  
   - **Delay (ms)**: set an exact number of milliseconds between clicks (e.g., `100 ms`).

5. **Toggle vs. Hold**  
   - **Toggle**: Press/click your bind once to enable; press/click again to disable.  
   - **Hold**: Auto-click runs only while the bind is held down.

6. **Safety Key**  
   - If you hold down the chosen safety key (e.g., `Alt`), auto-clicking pauses until you release it.  

7. **Config Saved to AppData**  
   - No clutter in the executable’s folder.  
   - Stored in `%APPDATA%\MyAutoClicker\config.yaml` on Windows (or the equivalent `~/.config/` location if you adapt it to other platforms).

8. **Instantly Saves Changes**  
   - Changing any option in the GUI – or setting/clearing a bind – immediately updates `config.yaml`.

---

## Installation & Dependencies

1. **Python 3.7+** (if you run from source).
2. **pip install** the following:
   ```bash
   pip install pynput pyyaml
   ```
3. (Optional) **PyInstaller** if you want to build a single EXE:
   ```bash
   pip install pyinstaller
   ```

> **Note**: If you’re just using the provided `.exe` (pre-built), you don’t need to install Python or these packages on your system. Everything is bundled.

---

## Usage (From Source)

1. **Clone** or **download** this repository.  
2. **Install** the Python dependencies:
   ```bash
   pip install pynput pyyaml
   ```
3. **Run**:
   ```bash
   python main.py
   ```
4. On first run, the script creates `config.yaml` in:
   ```
   C:\Users\%USERNAME%\AppData\Roaming\MyAutoClicker\config.yaml
   ```
   (assuming Windows).

---

## Usage (Pre-built EXE)

1. **Double-click** the `main.exe` (or whichever name you gave it).  
2. (Optional) **Run as Administrator** if you want to capture certain mouse buttons or do advanced hooking.  
3. The app loads/saves config in:
   ```
   %APPDATA%\MyAutoClicker\config.yaml
   ```
4. **No console** window appears. Just the main GUI.

---

## Building Your Own EXE

If you want to build your own executable (instead of using a pre-compiled version), follow these steps:

1. **Install PyInstaller**:
   ```bash
   pip install pyinstaller
   ```
2. **In the project folder**, run:
   ```bash
   pyinstaller --onefile --noconsole --icon=impl/icon.ico main.py
   ```
3. **Check** the `dist/` folder for your new `main.exe`.
4. Distribute `main.exe` to others.

---

## Configuration Details

- **`config.yaml`** is automatically created/updated. Sample structure:

  ```yaml
  left_click:
    mode: cps             # or "delay"
    cps: 10
    delay: 100
    bind: mouse4          # or something like "f6", "a", "left"...
    click_type: single    # or "double", "triple"
    activation: toggle    # or "hold"

  right_click:
    mode: delay
    cps: 5
    delay: 200
    bind: mouse5
    click_type: single
    activation: toggle

  safety_key: alt
  ```

- **No manual editing** is typically necessary. Changes from the GUI instantly write to this YAML file.

---

## Tips & Notes

- **Administrator Privileges**:  
  - Capturing global left/right mouse buttons sometimes requires running as Administrator on Windows or granting Accessibility on macOS. 
- **Ignore GUI Clicks**:  
  - Clicks inside the GUI window (for pressing buttons, etc.) are ignored for toggling the auto-clicker.  
- **Set/Change/Remove Binds**:  
  - Click **“Set Bind”** and press the desired key (e.g., `F6`) or mouse button (`mouse4`).  
  - Click **“Clear”** to remove the current bind.

---

## Troubleshooting

- **Bind Doesn’t Work**:  
  - Try using a side mouse button (`mouse4`/`mouse5`) or a keyboard key if left/right capture fails (OS restrictions).  
  - Run as Administrator for advanced hooking.  
- **No `config.yaml`**:  
  - The app should auto-generate `config.yaml` in `%APPDATA%\MyAutoClicker`. If it doesn’t, ensure the path is valid and your environment variables are standard.  
- **Icon Not Displayed**:  
  - Make sure `icon.ico` is valid and placed in `impl/icon.ico` if you’re building from source with PyInstaller.  

---

## Credits

- Built with [**Python**](https://www.python.org/)  
- Uses [**pynput**](https://pypi.org/project/pynput/) for global hooking  
- Uses [**PyYAML**](https://pypi.org/project/PyYAML/) for configuration  

*(Feel free to add any additional acknowledgments, special thanks, etc.)*