: << 'CMDBLOCK'
@echo off
REM Runs a hook script from this directory with bash, on Windows and elsewhere.
REM Usage: run-hook.cmd SCRIPT [ARGUMENT...]   (at most eight arguments)
REM
REM cmd.exe reads the first line as a label and runs this batch half. bash
REM reads it as the no-op ":" with a here-document, and skips to the shell
REM half at the end. Both halves need LF line endings, which .gitattributes
REM keeps. The same file ships in every plugin that runs hooks on Windows; a
REM test keeps the copies identical.
REM
REM Modeled on hooks/run-hook.cmd in obra/superpowers, MIT License,
REM Copyright (c) 2025 Jesse Vincent.

if "%~1"=="" (
    echo run-hook.cmd: name the hook script to run >&2
    exit /b 0
)

setlocal
set "BASH_EXE="

REM Git for Windows, installed for all users.
if defined ProgramFiles if exist "%ProgramFiles%\Git\bin\bash.exe" set "BASH_EXE=%ProgramFiles%\Git\bin\bash.exe"
if not defined BASH_EXE if defined ProgramFiles(x86) if exist "%ProgramFiles(x86)%\Git\bin\bash.exe" set "BASH_EXE=%ProgramFiles(x86)%\Git\bin\bash.exe"

REM Git for Windows, installed for one user. Without the defined check, an
REM unset LOCALAPPDATA would turn this into a path on the current drive.
if not defined BASH_EXE if defined LOCALAPPDATA if exist "%LOCALAPPDATA%\Programs\Git\bin\bash.exe" set "BASH_EXE=%LOCALAPPDATA%\Programs\Git\bin\bash.exe"

REM Any other bash on PATH. where.exe is called by its full path and with
REM $PATH: so that neither it nor bash comes from the current directory. The
REM WSL launchers (System32, Sysnative, the WindowsApps alias) are skipped:
REM they are not Git Bash, and they fail when no Linux distribution exists.
if not defined BASH_EXE if defined SystemRoot for /f "delims=" %%B in ('"%SystemRoot%\System32\where.exe" $PATH:bash 2^>nul') do if not defined BASH_EXE if not "%%~xB"=="" if /i not "%%~dpB"=="%SystemRoot%\System32\" if /i not "%%~dpB"=="%SystemRoot%\Sysnative\" if /i not "%%~dpB"=="%LOCALAPPDATA%\Microsoft\WindowsApps\" set "BASH_EXE=%%B"

REM With no bash, the hook does nothing rather than fail the session.
if not defined BASH_EXE exit /b 0

REM Outside a parenthesized block, so ERRORLEVEL is read after bash exits.
"%BASH_EXE%" "%~dp0%~1" %2 %3 %4 %5 %6 %7 %8 %9
exit /b %ERRORLEVEL%
CMDBLOCK

# bash runs from here. $0 can hold a Windows path, so split on / or \.
hooks_dir=${0%[/\\]*}
[ "$hooks_dir" = "$0" ] && hooks_dir=.
script=$1
shift
exec "${BASH:-bash}" "$hooks_dir/$script" "$@"
