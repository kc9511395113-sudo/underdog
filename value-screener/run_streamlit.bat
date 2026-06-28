@echo off
title Value Screener (Streamlit)
cd /d "%~dp0"
python -m pip install -r requirements.txt -q
echo.
echo Starting Streamlit at http://localhost:8501
echo.
python -m streamlit run streamlit_app.py
pause