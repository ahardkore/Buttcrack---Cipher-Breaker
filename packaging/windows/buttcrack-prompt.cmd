@echo off
rem Opens a command prompt with buttcrack.exe on PATH, for people who did not
rem tick the PATH box during installation (or who did, but have a prompt that
rem was already open when they installed it).
setlocal
set "PATH=%~dp0;%PATH%"
title Buttcrack command line

echo.
echo   buttcrack -- automatic cipher breaker
echo   ------------------------------------
echo.
echo   buttcrack "Wkh txlfn eurzq ira mxpsv ryhu wkh odcb grj."
echo   buttcrack identify --file puzzle.txt
echo   buttcrack encrypt vigenere --key LEMON "meet me at noon"
echo   buttcrack demo
echo   buttcrack --help
echo.
echo   Everything runs on this machine. Nothing is uploaded.
echo.

cmd /K
