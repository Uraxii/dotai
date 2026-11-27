@echo off
REM Runs guidelines.py with the first Python found, on Windows.
REM Usage: guidelines.cmd HARNESS [start]
REM guidelines.py finds a Python 3.11 or later itself. Every path prints a
REM notice when no check ran, and exits 0, so a failure never blocks work.

REM Only a Python that starts is given the payload, so stdin is read once.
setlocal
py -3 -I -c "import sys; sys.exit(sys.version_info < (3, 6))" <nul >nul 2>&1 && (set "PYTHON=py -3" & goto run)
python -I -c "import sys; sys.exit(sys.version_info < (3, 6))" <nul >nul 2>&1 && (set "PYTHON=python" & goto run)
python3 -I -c "import sys; sys.exit(sys.version_info < (3, 6))" <nul >nul 2>&1 && (set "PYTHON=python3" & goto run)
if "%~2"=="start" (echo {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "Notice: code-quality guideline hooks need Python 3.11 or later; none was found, so no guideline checks run in this session."}, "systemMessage": "Notice: code-quality guideline hooks need Python 3.11 or later; none was found, so no guideline checks run in this session."}) else (echo {"systemMessage": "Notice: code-quality guideline hooks need Python 3.11 or later; none was found, so this call was not checked."})
exit /b 0

:run
%PYTHON% -I "%~dp0guidelines.py" %1 2>nul || echo {"systemMessage": "pstack guideline hook failed; code-quality guidelines were not checked for this call."}
exit /b 0
