@echo off
title D.C.P.S. PSP - Build ISO Indonesia
cd /d "%~dp0"

echo ============================================================
echo   D.C.P.S. PSP - BUILD ISO BAHASA INDONESIA
echo ============================================================
echo.
echo [1/2] Mengompilasi naskah terjemahan dari folder sheets/...
python tools/dc1_translate_tool.py import-sheets id
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Gagal mengompilasi naskah sheets!
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [2/2] Membangun file ISO Bahasa Indonesia...
python build_iso.py --lang id

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Build ISO Bahasa Indonesia gagal!
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [SUKSES] ISO Bahasa Indonesia berhasil dibuat di folder output/!
echo Tekan tombol apa saja untuk menutup jendela ini...
pause >nul
