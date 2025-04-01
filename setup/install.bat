@echo off
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Python is not installed. Installing Python...
    start /wait msiexec /i https://www.python.org/ftp/python/3.13.2/python-3.13.2-amd64.exe /quiet InstallAllUsers=1 PrependPath=1
)

where pip >nul 2>nul
if %errorlevel% neq 0 (
    echo pip is not installed. Installing pip...
    curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
    python get-pip.py
)

pip3 install -r requirements.txt