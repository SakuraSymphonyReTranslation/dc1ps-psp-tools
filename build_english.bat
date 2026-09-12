@echo off
title D.C.P.S. PSP - Build ISO English
cd /d "%~dp0"

echo ============================================================
echo   D.C.P.S. PSP - BUILD ISO BAHASA INGGRIS (HYBRID COMPLETE)
echo ============================================================
echo.
echo Menjalankan build ISO Bahasa Inggris...
python build_iso.py --lang en

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Build ISO gagal! Silakan cek pesan kesalahan di atas.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [SUKSES] ISO berhasil dibuat di folder output/!
echo Tekan tombol apa saja untuk menutup jendela ini...
pause >nul
