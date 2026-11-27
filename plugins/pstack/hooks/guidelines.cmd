@echo off
REM Runs guidelines.py with the first Python found, on Windows.
REM Usage: guidelines.cmd HARNESS [start]
REM guidelines.py finds a Python 3.11 or later itself. With no Python at all,
REM a session start ("start") prints the notice; other calls do nothing.
REM Every path exits 0, so a failure never blocks the user's work.

where py >nul 2>nul && (py -3 -I "%~dp0guidelines.py" %1 & exit /b 0)
where python >nul 2>nul && (python -I "%~dp0guidelines.py" %1 & exit /b 0)
where python3 >nul 2>nul && (python3 -I "%~dp0guidelines.py" %1 & exit /b 0)
if "%~2"=="start" echo {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "Notice: code-quality guideline hooks need Python 3.11 or later; none was found, so no guideline checks run in this session."}, "systemMessage": "Notice: code-quality guideline hooks need Python 3.11 or later; none was found, so no guideline checks run in this session."}
exit /b 0
