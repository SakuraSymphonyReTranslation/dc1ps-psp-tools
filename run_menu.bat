@echo off
title D.C.P.S. PSP Translation & Modding Toolkit
cd /d "%~dp0"
setlocal enabledelayedexpansion

:MENU
cls
echo ======================================================================
echo       D.C.P.S. PSP TRANSLATION & ASSET TOOLKIT (NPJH50731)
echo ======================================================================
echo.
echo   [BUILD ISO GAME]
echo     1. Build ISO Bahasa Indonesia (Prioritas ID + Fallback EN)
echo     2. Build ISO Bahasa Inggris (Hybrid FanTL + MangaGamer Complete)
echo.
echo   [MANAJEMEN TERJEMAHAN BAHASA INDONESIA]
echo     3. Ekspor Ulang 721 Scene ke Sheet JSON (translations/id/sheets/)
echo     4. Impor Naskah Sheet JSON ke Naskah Game (transfer_id.json)
echo.
echo   [MODIFIKASI VIDEO & GRAFIS UI]
echo     5. Ekstrak Video Opening/Ending PMF ke folder custom/video/
echo     6. Ekstrak Grafis UI PNG & catfile.bin ke folder custom/ui/
echo     7. Repack catfile.bin (Setelah tekstur UI selesai diedit)
echo.
echo   [EMULASI & PENGUJIAN]
echo     8. Jalankan Game di Emulator PPSSPP
echo.
echo     9. Keluar
echo.
echo ======================================================================
set /p opt="Pilih menu [1-9]: "

if "%opt%"=="1" goto BUILD_ID
if "%opt%"=="2" goto BUILD_EN
if "%opt%"=="3" goto EXPORT_SHEETS
if "%opt%"=="4" goto IMPORT_SHEETS
if "%opt%"=="5" goto EXTRACT_VIDEO
if "%opt%"=="6" goto EXTRACT_UI
if "%opt%"=="7" goto REPACK_UI
if "%opt%"=="8" goto RUN_PPSSPP
if "%opt%"=="9" goto EXIT
goto MENU

:BUILD_ID
cls
echo [BUILD] Membangun ISO Bahasa Indonesia...
python tools/dc1_translate_tool.py import-sheets id
python build_iso.py --lang id
echo.
pause
goto MENU

:BUILD_EN
cls
echo [BUILD] Membangun ISO Bahasa Inggris...
python build_iso.py --lang en
echo.
pause
goto MENU

:EXPORT_SHEETS
cls
echo [SHEETS] Mengekspor 721 scene bilingual ke folder translations/id/sheets/...
python tools/dc1_translate_tool.py export-sheets id
echo.
pause
goto MENU

:IMPORT_SHEETS
cls
echo [SHEETS] Mengompilasi sheet terjemahan ke transfer_id.json...
python tools/dc1_translate_tool.py import-sheets id
echo.
pause
goto MENU

:EXTRACT_VIDEO
cls
echo [ASSET] Mengekstrak video PMF dari Base ISO...
python tools/dc1_assets.py extract-video
echo.
pause
goto MENU

:EXTRACT_UI
cls
echo [ASSET] Mengekstrak file grafis UI dan tekstur...
python tools/dc1_assets.py extract-ui
echo.
pause
goto MENU

:REPACK_UI
cls
echo [ASSET] Menyusun ulang custom/ui/catfile.bin...
python tools/dc1_assets.py repack-catfile
echo.
pause
goto MENU

:RUN_PPSSPP
cls
echo [EMULATOR] Menjalankan PPSSPP...
if exist "output\D.C.P.S. [NPJH50731]_id.iso" (
    start "" "F:\Games\PSP\ppsspp_win\PPSSPPWindows64.exe" "output\D.C.P.S. [NPJH50731]_id.iso"
) else if exist "output\D.C.P.S. [NPJH50731]_en.iso" (
    start "" "F:\Games\PSP\ppsspp_win\PPSSPPWindows64.exe" "output\D.C.P.S. [NPJH50731]_en.iso"
) else (
    echo File ISO belum dibangun di folder output/! Silakan pilih menu 1 atau 2 terlebih dahulu.
    pause
)
goto MENU

:EXIT
exit /b 0
