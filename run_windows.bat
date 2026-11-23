@echo off
setlocal
cd /d "%~dp0"

echo ==================================================
echo   ParcelPath Billing Interceptor - Local Launcher
echo ==================================================
echo.

echo Checking the Python installation...
where python >nul 2>nul
if errorlevel 1 goto missing_python

python --version
python -c "import sys; assert sys.version_info >= (3,14), 'Python 3.14 or newer is required.'; print('Python runtime OK:', sys.executable)"
if errorlevel 1 goto wrong_python

if not exist .venv (
    echo.
    echo Creating the project virtual environment...
    python -m venv .venv
    if errorlevel 1 goto setup_error
)

call .venv\Scripts\activate.bat
if errorlevel 1 goto setup_error

echo.
echo Updating pip...
python -m pip install --upgrade pip
if errorlevel 1 goto setup_error

echo.
echo Installing project dependencies...
python -m pip install -r requirements.txt
if errorlevel 1 goto setup_error

echo.
echo Starting ParcelPath Billing Interceptor...
echo The browser should open at http://localhost:8501
echo Press Ctrl+C in this window to stop the application.
echo.
python -m streamlit run app.py
if errorlevel 1 goto app_error
goto end

:missing_python
echo ERROR: Windows could not find Python using the command "python".
echo Install Python 3.14 and enable "Add Python to PATH" during installation.
echo Then close and reopen this terminal and run: python --version
pause
goto end

:wrong_python
echo ERROR: Python 3.14 or newer is required.
echo The launcher above shows which Python executable Windows selected.
echo If you have more than one Python installation, correct your PATH and try again.
pause
goto end

:setup_error
echo.
echo ERROR: Environment creation or dependency installation failed.
echo Review the error above. You can retry by running this file again.
pause
goto end

:app_error
echo.
echo ERROR: Streamlit exited with an error. Review the message above.
pause

goto end

:end
endlocal
