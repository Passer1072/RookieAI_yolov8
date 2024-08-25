@echo off

:: Check if running as administrator
net session >nul 2>&1
if %errorLevel% NEQ 0 (
    echo [ERROR] Please run as administrator
    pause
    exit /B
)

set CUDA_VERSION=11.8
set CUDNN_VERSION=12.6
set CUDNN_URL=https://mqz0sa.ph.files.1drv.com/y4m7PpXEdYxNetKZbn4_pUslQ6agOXncF16GLDNKgRzvtOhjT0OsgXwAbwgNtGiKaQ3RyZWWx14A910BwWWDRLsGqxsArWT0Zcd-yUEzitrDzLxIyEHH1joDIUXQGFBE4qnYAWF6L8B7vtLvOll1TgAm7CD1SPyfoq7VtiEMbm_ubKEnyKnETDSv-e-qjzmUBBWx6F-4TX7z-a7kg67xlRAdw
set CUDNN_EXE=%TEMP%\cudnn_installer.exe

echo Downloading cuDNN installer with progress bar...

powershell -Command "& { $ProgressPreference = 'Continue'; $webclient = New-Object System.Net.WebClient; $webclient.Headers.Add('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3');$webclient.DownloadFile('%CUDNN_URL%', '%CUDNN_EXE%'); Write-Host 'Download complete.'; }"

echo Running cuDNN installer...
start /wait %CUDNN_EXE%

echo cuDNN installation complete. Copying cuDNN files...
xcopy /s /y "%SystemDrive%\Program Files\NVIDIA\CUDNN\v9.3\bin\%CUDNN_VERSION%\*" "%SystemDrive%\Program Files\NVIDIA\CUDNN\v9.3\bin\"

echo Cleaning up downloaded installer...
del %CUDNN_EXE%

echo All tasks completed.
pause