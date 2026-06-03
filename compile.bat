@echo off
REM =============================================================================
REM Space Colony - C++ engine compiler for Windows
REM Run from project root:  .\compile.bat
REM =============================================================================

echo [compile] Removing old engine.exe if present...
if exist engine\engine.exe del /f engine\engine.exe

echo [compile] Compiling Space Colony C++ engine...
g++ -std=c++17 -O2 -Wall ^
    engine\main.cpp ^
    engine\linked_list.cpp ^
    engine\tree.cpp ^
    -o engine\engine.exe

IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Compilation failed. Make sure g++ is installed and on PATH.
    echo Install MSYS2 from https://www.msys2.org
    echo Then run in MSYS2: pacman -S mingw-w64-ucrt-x86_64-gcc
    echo And add C:\msys64\ucrt64\bin to your Windows PATH.
    pause
    exit /b 1
)

echo [compile] SUCCESS! engine\engine.exe created.
echo [compile] Now run: py game\ui\main.py
pause