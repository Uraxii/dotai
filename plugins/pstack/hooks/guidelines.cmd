@echo off
REM Runs guidelines.py with the first Python found, on Windows.
REM Usage: guidelines.cmd HARNESS [start]
REM guidelines.py finds a Python 3.11 or later itself. With no Python at all,
REM a session start ("start") prints the notice; other calls do nothing.
REM Every path exits 0, so a failure never blocks the user's work.

REM A candidate that is missing or cannot start fails, and the next one runs.
REM guidelines.py itself always exits 0, so it runs at most once.
py -3 -I "%~dp0guidelines.py" %1 2>nul && exit /b 0
python -I "%~dp0guidelines.py" %1 2>nul && exit /b 0
python3 -I "%~dp0guidelines.py" %1 2>nul && exit /b 0
if "%~2"=="start" echo {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "Notice: code-quality guideline hooks need Python 3.11 or later; none was found, so no guideline checks run in this session."}, "systemMessage": "Notice: code-quality guideline hooks need Python 3.11 or later; none was found, so no guideline checks run in this session."}
exit /b 0
