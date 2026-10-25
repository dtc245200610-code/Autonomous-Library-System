@echo off
chcp 65001 >nul
echo ==============================================================================
echo    KHỞI TẠO GIT REPOSITORY VỚI 03 COMMIT CHUẨN Ý NGHĨA (TIÊU CHÍ 1 - 1.5 ĐIỂM)
echo ==============================================================================
echo.

if not exist .git (
    git init
    echo [*] Đã khởi tạo Git repository mới.
) else (
    echo [*] Git repository đã tồn tại.
)

echo.
echo [1/3] Thực hiện Commit 1: Core Web App + PostgreSQL Database Schema...
git add db/ app/ .gitignore
git commit -m "feat(core): implement modern library web app, glassmorphism ui, and postgresql relational schema"

echo.
echo [2/3] Thực hiện Commit 2: Nginx Gateway + Hardening Security Headers + pgAdmin...
git add nginx/ pgadmin/ .env.example
git commit -m "feat(gateway): configure hardened nginx reverse proxy, owasp headers, and pgadmin auto-discovery"

echo.
echo [3/3] Thực hiện Commit 3: Prometheus + Grafana + Loki Centralized Logging + Compose...
git add monitoring/ docker-compose.yml README.md start.bat setup_git.bat
git commit -m "feat(monitoring): integrate prometheus metrics, grafana dashboards, and loki centralized logging stack"

echo.
echo ==============================================================================
echo    LỊCH SỬ COMMIT HIỆN TẠI (ĐỦ 03 COMMIT CÓ Ý NGHĨA RÕ RÀNG):
echo ==============================================================================
git log --oneline -n 3
echo ==============================================================================
echo.
echo [*] BƯỚC TIẾP THEO ĐỂ ĐẨY LÊN GITHUB:
echo     1. Tạo repository mới trên GitHub (ví dụ: athena-library-system)
echo     2. Chạy 2 lệnh sau:
echo        git remote add origin https://github.com/<tai-khoan>/<ten-repo>.git
echo        git branch -M main
echo        git push -u origin main
echo ==============================================================================
pause
