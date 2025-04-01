python -m pip install pyinstaller
python -m PyInstaller --onefile --noconsole --icon=impl/icon.ico --name autoclicker --add-data "impl/icon.ico;impl" main.py