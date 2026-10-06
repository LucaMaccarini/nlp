@echo off
setlocal

set "CONDA_ACT=C:\Users\luca.maccarini\AppData\Local\anaconda3\Scripts\activate.bat"

if not exist "%CONDA_ACT%" (
    echo Non trovo activate.bat in: %CONDA_ACT%
    pause
    exit /b 1
)

call "%CONDA_ACT%" base
if errorlevel 1 (
    echo Attivazione dell'ambiente fallita.
    pause
    exit /b 1
)

cd /d "%~dp0.."
echo Cartella di lavoro: %CD%
echo.

rem Default: NO. Solo la risposta S attiva la cancellazione.
set "RIGENERA=0"
choice /c SN /n /m "Cancellare TUTTI i PDF in questa cartella e rigenerarli tutti? [S/N] "
if %errorlevel%==1 set "RIGENERA=1"
echo.

if "%RIGENERA%"=="1" (
    echo Elimino tutti i PDF...
    del /q "*.pdf" 2>nul
    echo.
)

for %%f in (*.ipynb) do (
    if exist "%%~nf.pdf" (
        echo Salto, PDF gia presente: %%f
    ) else (
        echo Converto: %%f
        call jupyter nbconvert --to pdf "%%f"
    )
)

echo.
echo Fatto.
pause