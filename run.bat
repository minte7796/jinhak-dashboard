@echo off
chcp 65001 > nul
echo ========================================================
echo   2027학년도 수시모집 스마트 경쟁률 대시보드 실행기
echo ========================================================
echo.
echo [1/2] 필요한 패키지 확인 중...
python -m pip install -q flask beautifulsoup4 requests

echo [2/2] 대시보드 서버를 시작합니다...
echo.
echo * 브라우저 주소: http://127.0.0.1:5000
echo * 종료하려면 창을 닫거나 Ctrl+C를 누르세요.
echo.

start "" "http://127.0.0.1:5000"
python app.py
pause
