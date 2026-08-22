@echo off
python "%~dp0tools\harness_cli.py" %*
exit /b %ERRORLEVEL%
