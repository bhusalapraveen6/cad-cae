@echo off
set PYTHONPATH=%PYTHONPATH%;%~dp0backend
echo Starting CAD-CAE Streamlit Dashboard...
streamlit run streamlit_app.py
pause
