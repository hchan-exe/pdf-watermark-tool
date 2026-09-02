@echo off
cd /d "%~dp0"
python pdf_watermark_gui.py
if errorlevel 1 (
    echo.
    echo Failed to start. Make sure Python is installed and on PATH.
    echo Then run: pip install pypdf reportlab
    pause
)
