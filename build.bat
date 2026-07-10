@echo off
rem ============================================================
rem  build.bat  -  打包成單一 exe（dist\JPLiveTranslator.exe）
rem  需求：pip install pyinstaller
rem ============================================================
chcp 65001 >nul

echo [1/2] 清除舊的建置產物...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo [2/2] PyInstaller 打包中（約 1~3 分鐘）...
pyinstaller ^
  --noconfirm ^
  --onefile ^
  --noconsole ^
  --name JPLiveTranslator ^
  --icon assets\icon.ico ^
  --collect-data customtkinter ^
  main.py

if errorlevel 1 (
  echo.
  echo ❌ 打包失敗，請檢查上方錯誤訊息。
  exit /b 1
)

echo.
echo ✅ 完成！輸出：dist\JPLiveTranslator.exe
