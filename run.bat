@echo off
mode con: cols=54 lines=14
title Text Input Helper

cd /d "%~dp0"
".venv\Scripts\python.exe" app.py