:START
@echo off
title Movie Library Manager
chcp 65001 >nul

:: ANSI color setup. Capture the ESC (0x1B) char, then define color vars.
:: ANSI codes are zero-width, so they don't affect the menu's column alignment.
for /f %%a in ('echo prompt $E ^| cmd') do set "ESC=%%a"
set "CR=%ESC%[0m"
set "CB=%ESC%[36m"
set "CT=%ESC%[1;97m"
set "CS=%ESC%[1;36m"
set "CK=%ESC%[93m"
set "CD=%ESC%[90m"
set "CG=%ESC%[92m"
set "CE=%ESC%[91m"

:: Virtual Environment Activation
if exist ".venv\Scripts\activate.bat" (
    echo  %CG%[Environment]%CR% Activating virtual environment...
    call .venv\Scripts\activate.bat
) else (
    echo  %CE%[Environment]%CR% No virtual environment found. Running globally.
    echo  %CD%[Hint] Run Option [V] to set up an isolated environment.%CR%
)

:MENU
cls
echo.
echo  %CB%╔═══════════════════════════════════╦═══════════════════════════════════╗%CR%
echo  %CB%║%CR%%CT%                          MOVIE LIBRARY MANAGER                        %CR%%CB%║%CR%
echo  %CB%╠═══════════════════════════════════╬═══════════════════════════════════╣%CR%
echo  %CB%║%CR%%CS% SCANNING                          %CR%%CB%║%CR%%CS% ENRICHMENT (needs keys)           %CR%%CB%║%CR%
echo  %CB%║%CR%  %CK%[1]%CR% Full Scan                    %CB%║%CR%  %CK%[A]%CR% AI Enrich (Gemini)           %CB%║%CR%
echo  %CB%║%CR%  %CK%[2]%CR% Quick Scan (50)              %CB%║%CR%  %CK%[B]%CR% OMDb Enrich                  %CB%║%CR%
echo  %CB%║%CR%  %CK%[3]%CR% Custom Scan                  %CB%║%CR%  %CK%[C]%CR% Full Enrich (AI+OMDb)        %CB%║%CR%
echo  %CB%║%CR%%CS% VIEWING                           %CR%%CB%║%CR%  %CK%[K]%CR% Bulk AI Enrich               %CB%║%CR%
echo  %CB%║%CR%  %CK%[4]%CR% Statistics                   %CB%║%CR%  %CK%[L]%CR% Full Bulk (AI+OMDb)          %CB%║%CR%
echo  %CB%║%CR%  %CK%[5]%CR% Sample (10)                  %CB%║%CR%  %CK%[F]%CR% Retry Failed OMDb            %CB%║%CR%
echo  %CB%║%CR%  %CK%[6]%CR% Sample (Custom)              %CB%║%CR%%CS% SERVER                            %CR%%CB%║%CR%
echo  %CB%║%CR%%CS% DATABASE                          %CR%%CB%║%CR%  %CK%[S]%CR% Start Web Server             %CB%║%CR%
echo  %CB%║%CR%  %CK%[7]%CR% Sync CSV to SQLite           %CB%║%CR%%CS% OTHER                             %CR%%CB%║%CR%
echo  %CB%║%CR%  %CK%[8]%CR% Open CSV File                %CB%║%CR%  %CK%[V]%CR% Setup venv (UV)              %CB%║%CR%
echo  %CB%║%CR%  %CK%[9]%CR% Open Data Folder             %CB%║%CR%  %CK%[T]%CR% Test Parser                  %CB%║%CR%
echo  %CB%║%CR%  %CK%[D]%CR% Cleanup (deleted)            %CB%║%CR%  %CK%[E]%CR% Edit .env                    %CB%║%CR%
echo  %CB%║%CR%  %CK%[M]%CR% Clean Titles                 %CB%║%CR%  %CK%[H]%CR% Help                         %CB%║%CR%
echo  %CB%║%CR%                                   %CB%║%CR%  %CK%[R]%CR% Reset Data                   %CB%║%CR%
echo  %CB%╠═══════════════════════════════════╩═══════════════════════════════════╣%CR%
echo  %CB%║%CR%  %CK%[0]%CR% Exit                                                             %CB%║%CR%
echo  %CB%╚═══════════════════════════════════════════════════════════════════════╝%CR%
echo.

set /p choice="  %CK%Select an option:%CR% "

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
if /i "%choice%"=="K" goto BULK_AI_ENRICH
if /i "%choice%"=="L" goto FULL_BULK_ENRICH
if /i "%choice%"=="F" goto RETRY_FAILED
if /i "%choice%"=="D" goto CLEANUP
if /i "%choice%"=="M" goto CLEAN_NAMES
if /i "%choice%"=="S" goto START_SERVER
if /i "%choice%"=="V" goto SETUP_ENV
if /i "%choice%"=="T" goto TEST_PARSER
if /i "%choice%"=="E" goto EDIT_ENV
if /i "%choice%"=="H" goto HELP
if /i "%choice%"=="R" goto RESET
if "%choice%"=="0" goto EXIT

echo  %CE%Invalid option.%CR% Press any key to try again...
pause >nul
goto MENU

:FULL_SCAN
cls
echo.
echo  ========================================
echo   FULL SCAN - Indexing all videos...
echo  ========================================
echo.
python src\main.py --scan
set "rc=%errorlevel%"
echo.
call :STATUS %rc% "Full scan"
pause
goto MENU

:QUICK_SCAN
cls
echo.
echo  ========================================
echo   QUICK SCAN - First 50 files...
echo  ========================================
echo.
python src\main.py --scan --limit 50
set "rc=%errorlevel%"
echo.
call :STATUS %rc% "Quick scan"
pause
goto MENU

:CUSTOM_SCAN
cls
echo.
set /p limit="  Enter number of files to scan: "
echo.
echo  Scanning %limit% files...
echo.
python src\main.py --scan --limit %limit%
set "rc=%errorlevel%"
echo.
call :STATUS %rc% "Custom scan"
pause
goto MENU

:STATS
cls
echo.
echo  Fetching Database Statistics...
echo.
python src\main.py --stats
set "rc=%errorlevel%"
echo.
call :STATUS %rc% "Statistics"
pause
goto MENU

:SAMPLE_10
cls
echo.
python src\main.py --sample 10
set "rc=%errorlevel%"
echo.
call :STATUS %rc% "Sample"
pause
goto MENU

:SAMPLE_CUSTOM
cls
echo.
set /p count="  Enter number of samples to show: "
echo.
python src\main.py --sample %count%
set "rc=%errorlevel%"
echo.
call :STATUS %rc% "Sample"
pause
goto MENU

:SYNC
cls
echo.
echo  Syncing CSV to SQLite...
echo.
python src\main.py --sync
set "rc=%errorlevel%"
echo.
call :STATUS %rc% "CSV to SQLite sync"
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
echo  %CD%Requires GEMINI_API_KEY in .env%CR%
echo.
set /p limit="  Enter limit (default 10, 'all' for all): "
if "%limit%"=="" set limit=10

call :CHOOSE_MODEL

if /i "%limit%"=="all" (
    python src\main.py --enrich %AIFLAGS%
) else (
    python src\main.py --enrich %AIFLAGS% --limit %limit%
)
set "rc=%errorlevel%"
echo.
call :STATUS %rc% "AI enrichment"
pause
goto MENU

:BULK_AI_ENRICH
cls
echo.
echo  ========================================
echo   BULK AI ENRICHMENT (Configured Model)
echo  ========================================
echo.
echo  This uses the configured AI model (Configured Model)
echo  It processes movies in chunks of 50 for speed.
echo.
set /p limit="  Enter limit (default 50, 'all' for all): "
if "%limit%"=="" set limit=50

call :CHOOSE_MODEL

if /i "%limit%"=="all" (
    python src\main.py --enrich --bulk %AIFLAGS%
) else (
    python src\main.py --enrich --bulk %AIFLAGS% --limit %limit%
)
set "rc=%errorlevel%"
echo.
call :STATUS %rc% "Bulk AI enrichment"
pause
goto MENU

:FULL_BULK_ENRICH
cls
echo.
echo  ========================================
echo   FULL BULK ENRICHMENT (Gemini + OMDb)
echo  ========================================
echo.
echo  1. Bulk AI Identification (Configured Model)
echo  2. OMDb Metadata Fetch (Detailed Info)
echo.
set /p limit="  Enter limit (default 50, 'all' for all): "
if "%limit%"=="" set limit=50

call :CHOOSE_MODEL

if /i "%limit%"=="all" (
    python src\main.py --enrich --bulk %AIFLAGS%
    echo.
    echo  [Step 1 Complete] Starting OMDb fetch...
    python src\main.py --fetch-omdb
) else (
    python src\main.py --enrich --bulk %AIFLAGS% --limit %limit%
    echo.
    echo  [Step 1 Complete] Starting OMDb fetch...
    python src\main.py --fetch-omdb --limit %limit%
)
set "rc=%errorlevel%"
echo.
call :STATUS %rc% "Full bulk enrichment"
pause
goto MENU

:OMDB_ENRICH
cls
echo.
echo  ========================================
echo   OMDb ENRICHMENT
echo  ========================================
echo.
echo  %CD%Requires OMDB_API_KEY in .env%CR%
echo.
set /p limit="  Enter limit (default 10, 'all' for all): "
if "%limit%"=="" set limit=10

if /i "%limit%"=="all" (
    python src\main.py --fetch-omdb
) else (
    python src\main.py --fetch-omdb --limit %limit%
)
set "rc=%errorlevel%"
echo.
call :STATUS %rc% "OMDb enrichment"
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
call :CHOOSE_MODEL

if /i "%limit%"=="all" (
    python src\main.py --enrich %AIFLAGS%
    python src\main.py --fetch-omdb
) else (
    python src\main.py --enrich %AIFLAGS% --limit %limit%
    python src\main.py --fetch-omdb --limit %limit%
)
set "rc=%errorlevel%"
echo.
call :STATUS %rc% "Full enrichment"
pause
goto MENU

:RETRY_FAILED
cls
echo.
echo  ========================================
echo   RETRY FAILED OMDb ENRICHMENTS
echo  ========================================
echo.
echo  Resets movies that previously failed OMDb enrichment
echo  (state [4] Failed) back to pending and runs OMDb again.
echo.
set /p limit="  Enter limit (default 'all'): "
if "%limit%"=="" set limit=all

if /i "%limit%"=="all" (
    python src\main.py --retry-failed
) else (
    python src\main.py --retry-failed --limit %limit%
)
set "rc=%errorlevel%"
echo.
call :STATUS %rc% "Retry failed"
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
python src\server.py
pause
goto MENU

:TEST_PARSER
cls
echo.
echo  ========================================
echo   PARSER TEST
echo  ========================================
echo.
python src\parser.py
set "rc=%errorlevel%"
echo.
call :STATUS %rc% "Parser test"
pause
goto MENU

:EDIT_ENV
cls
echo  Opening .env file...
start "" notepad ".env"
goto MENU

:HELP
cls
echo.
echo  ========================================
echo   COMMAND LINE HELP
echo  ========================================
echo.
python src\main.py --help
echo.
pause
goto MENU

:RESET
cls
python src\reset_data.py
set "rc=%errorlevel%"
call :STATUS %rc% "Reset data"
pause
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
python src\main.py --check-missing
echo.
set /p confirm="  Remove these movies from database? (Y/N): "
if /i "%confirm%"=="Y" (
    python src\main.py --cleanup
) else (
    echo  %CD%Cancelled.%CR%
    echo.
    pause
    goto MENU
)
set "rc=%errorlevel%"
echo.
call :STATUS %rc% "Cleanup"
pause
goto MENU

:CLEAN_NAMES
cls
echo.
echo  ========================================
echo   CLEAN MOVIE TITLES
echo  ========================================
echo.
echo  This utility analyzes all movies for recurring words 
echo  (like YTS, RARBG, 1080p, etc.) that might have been 
echo  parsed as part of the title.
echo.
echo  Step 1: Perform dry run (find recurring words)
echo.
python src\clean_names.py
echo.
set /p apply="  Do you want to apply these removals to the database? (Y/N): "
if /i "%apply%"=="Y" (
    python src\clean_names.py --apply
) else (
    echo  %CD%Cancelled.%CR%
    echo.
    pause
    goto MENU
)
set "rc=%errorlevel%"
echo.
call :STATUS %rc% "Clean titles"
pause
goto MENU

:SETUP_ENV
cls
call setup_env.bat
goto START

:STATUS
:: Print a colored result line. %1 = exit code (capture %errorlevel% into a
:: var on the line right after the command, then pass it here). %2 = quoted op.
if "%~1"=="0" ( echo  %CG%[ OK ]%CR% %~2 completed. ) else ( echo  %CE%[FAIL]%CR% %~2 failed ^(exit %~1^). )
goto :eof

:CHOOSE_MODEL
:: Prompts for the AI provider/model and sets %AIFLAGS% for the python call.
:: Called by the AI enrichment actions (A, C, K, L).
echo.
echo  --- Select AI Provider / Model ---
echo   [1] Gemini 2.5 Flash  (default, higher free quota)
echo   [2] Gemini 3.5 Flash  (latest)
echo   [3] Groq - Llama 3.3 70B  (fast, identifies from memory)
echo   [4] Groq - Compound  (web-search grounded)
echo   [5] Groq - custom model id
echo   (Groq options require GROQ_API_KEY in .env)
echo.
set /p mc="  Choice [1]: "
if "%mc%"=="" set mc=1
set "AIFLAGS=--provider gemini --model 2.5"
if "%mc%"=="2" set "AIFLAGS=--provider gemini --model 3.5"
if "%mc%"=="3" set "AIFLAGS=--provider groq --model llama-3.3-70b-versatile"
if "%mc%"=="4" set "AIFLAGS=--provider groq --model groq/compound"
if "%mc%"=="5" goto :CHOOSE_MODEL_CUSTOM
echo.
goto :eof

:CHOOSE_MODEL_CUSTOM
:: Read the custom id on its own line (not inside an if-block) so plain
:: %gm% expansion picks up the just-entered value.
set /p gm="  Enter Groq model id: "
set "AIFLAGS=--provider groq --model %gm%"
echo.
goto :eof

:EXIT
cls
echo.
echo  Goodbye!
echo.
timeout /t 2 >nul
exit
