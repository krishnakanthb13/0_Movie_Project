:START
@echo off
title Movie Library Manager
color 0A
chcp 65001 >nul

:: Virtual Environment Activation
if exist ".venv\Scripts\activate.bat" (
    echo [Environment] Activating virtual environment...
    call .venv\Scripts\activate.bat
) else (
    echo [Environment] No virtual environment found. Running globally.
    echo [Hint] Run Option [V] to set up an isolated environment.
)

:MENU
cls
echo.
echo  ╔══════════════════════════════════════════════════════════════╗
echo  ║              MOVIE LIBRARY MANAGER                           ║
echo  ╠══════════════════════════════════════════════════════════════╣
echo  ║                                                              ║
echo  ║   SCANNING                                                   ║
echo  ║   [1] Full Scan (Index all videos)                           ║
echo  ║   [2] Quick Scan (First 50 files)                            ║
echo  ║   [3] Custom Scan (Enter limit)                              ║
echo  ║                                                              ║
echo  ║   VIEWING                                                    ║
echo  ║   [4] Show Statistics                                        ║
echo  ║   [5] Show Sample Records (10)                               ║
echo  ║   [6] Show Sample Records (Custom)                           ║
echo  ║                                                              ║
echo  ║   DATABASE                                                   ║
echo  ║   [7] Sync CSV to SQLite                                     ║
echo  ║   [8] Open CSV File                                          ║
echo  ║   [9] Open Data Folder                                       ║
echo  ║   [D] Cleanup (Remove deleted movies)                        ║
echo  ║                                                              ║
echo  ║   ENRICHMENT (Requires API Keys)                             ║
echo  ║   [A] AI Enrichment (Gemini)                                 ║
echo  ║   [B] OMDb Enrichment                                        ║
echo  ║   [C] Full Enrichment (AI + OMDb)                            ║
echo  ║                                                              ║
echo  ║   SERVER                                                     ║
echo  ║   [S] Start Web Server                                       ║
echo  ║                                                              ║
echo  ║   OTHER                                                      ║
echo  ║   [V] Set Up Virtual Environment (UV)                        ║
echo  ║   [T] Test Parser                                            ║
echo  ║   [E] Edit .env File (API Keys)                              ║
echo  ║   [0] Exit                                                   ║
echo  ║                                                              ║
echo  ╚══════════════════════════════════════════════════════════════╝
echo.

set /p choice="  Select an option: "

if "%choice%"=="1" goto FULL_SCAN
if "%choice%"=="2" goto QUICK_SCAN
if "%choice%"=="3" goto CUSTOM_SCAN
if "%choice%"=="4" goto STATS
if "%choice%"=="5" goto SAMPLE_10
if "%choice%"=="6" goto SAMPLE_CUSTOM
if "%choice%"=="7" goto SYNC
if "%choice%"=="8" goto OPEN_CSV
if "%choice%"=="9" goto OPEN_DATA
if /i "%choice%"=="A" goto AI_ENRICH
if /i "%choice%"=="B" goto OMDB_ENRICH
if /i "%choice%"=="C" goto FULL_ENRICH
if /i "%choice%"=="D" goto CLEANUP
if /i "%choice%"=="S" goto START_SERVER
if /i "%choice%"=="V" goto SETUP_ENV
if /i "%choice%"=="T" goto TEST_PARSER
if /i "%choice%"=="E" goto EDIT_ENV
if "%choice%"=="0" goto EXIT

echo  Invalid option. Press any key to try again...
pause >nul
goto MENU

:FULL_SCAN
cls
echo.
echo  ========================================
echo   FULL SCAN - Indexing all videos...
echo  ========================================
echo.
python main.py --scan
echo.
echo  Scan complete!
pause
goto MENU

:QUICK_SCAN
cls
echo.
echo  ========================================
echo   QUICK SCAN - First 50 files...
echo  ========================================
echo.
python main.py --scan --limit 50
echo.
pause
goto MENU

:CUSTOM_SCAN
cls
echo.
set /p limit="  Enter number of files to scan: "
echo.
echo  Scanning %limit% files...
echo.
python main.py --scan --limit %limit%
echo.
pause
goto MENU

:STATS
cls
echo.
python main.py --stats
echo.
pause
goto MENU

:SAMPLE_10
cls
echo.
python main.py --sample 10
echo.
pause
goto MENU

:SAMPLE_CUSTOM
cls
echo.
set /p count="  Enter number of samples to show: "
echo.
python main.py --sample %count%
echo.
pause
goto MENU

:SYNC
cls
echo.
echo  Syncing CSV to SQLite...
echo.
python main.py --sync
echo.
echo  Sync complete!
pause
goto MENU

:OPEN_CSV
cls
echo  Opening CSV file...
start "" "data\movies.csv"
goto MENU

:OPEN_DATA
cls
echo  Opening data folder...
start "" "data"
goto MENU

:AI_ENRICH
cls
echo.
echo  ========================================
echo   AI ENRICHMENT (Gemini)
echo  ========================================
echo.
echo  This requires GEMINI_API_KEY in .env
echo.
set /p confirm="  Continue? (Y/N): "
if /i "%confirm%"=="Y" (
    python main.py --enrich --limit 10
) else (
    echo  Cancelled.
)
echo.
pause
goto MENU

:OMDB_ENRICH
cls
echo.
echo  ========================================
echo   OMDb ENRICHMENT
echo  ========================================
echo.
echo  This requires OMDB_API_KEY in .env
echo.
set /p confirm="  Continue? (Y/N): "
if /i "%confirm%"=="Y" (
    python main.py --fetch-omdb --limit 10
) else (
    echo  Cancelled.
)
echo.
pause
goto MENU

:FULL_ENRICH
cls
echo.
echo  ========================================
echo   FULL ENRICHMENT (AI + OMDb)
echo  ========================================
echo.
echo  This requires both API keys in .env
echo.
set /p limit="  Enter number of movies to enrich (or 'all'): "
echo.
if /i "%limit%"=="all" (
    python main.py --enrich
    python main.py --fetch-omdb
) else (
    python main.py --enrich --limit %limit%
    python main.py --fetch-omdb --limit %limit%
)
echo.
pause
goto MENU

:START_SERVER
cls
echo.
echo  ========================================
echo   STARTING WEB SERVER
echo  ========================================
echo.
echo  Server will start at http://localhost:8010
echo  Press Ctrl+C to stop the server.
echo.
python server.py
pause
goto MENU

:TEST_PARSER
cls
echo.
echo  ========================================
echo   PARSER TEST
echo  ========================================
echo.
python parser.py
echo.
pause
goto MENU

:EDIT_ENV
cls
echo  Opening .env file...
start "" notepad ".env"
goto MENU

:CLEANUP
cls
echo.
echo  ========================================
echo   DATABASE CLEANUP
echo  ========================================
echo.
echo  This will check for movies in the database
echo  whose files no longer exist on disk.
echo.
echo  Step 1: Checking for missing files...
echo.
python main.py --check-missing
echo.
set /p confirm="  Remove these movies from database? (Y/N): "
if /i "%confirm%"=="Y" (
    python main.py --cleanup
) else (
    echo  Cancelled.
)
echo.
pause
goto MENU

:SETUP_ENV
cls
call setup_env.bat
goto START

:EXIT
cls
echo.
echo  Goodbye!
echo.
timeout /t 2 >nul
exit
