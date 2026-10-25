@echo off
chcp 65001 >nul
echo ==============================================================================
echo    ATHENA SMARTLIB - HỆ THỐNG QUẢN LÝ THƯ VIỆN HIỆN ĐẠI (DEVOPS STACK)
echo ==============================================================================
echo.

if not exist .env (
    echo [*] Đang sao chép file cấu hình mẫu .env.example sang .env...
    copy .env.example .env >nul
)

echo [*] Đang khởi chạy toàn bộ dịch vụ (8 Containers) bằng Docker Compose...
docker compose up -d --build

echo.
echo [*] Đang kiểm tra trạng thái khởi động của các container...
timeout /t 5 /nobreak >nul
docker compose ps

echo.
echo ==============================================================================
echo    HỆ THỐNG ĐÃ SẴN SÀNG! TRUY CẬP CÁC DỊCH VỤ DƯỚI ĐÂY:
echo ==============================================================================
echo  1. Giao Diện Quản Lý Thư Viện: http://localhost:8080/
echo  2. Trang Quản Trị pgAdmin 4:   http://localhost:8080/pgadmin/ (hoặc port 5050)
echo     - Tài khoản: admin@library.local
echo     - Mật khẩu:  LibraryAdmin@2026!
echo  3. Hệ Thống Giám Sát Grafana:   http://localhost:8080/grafana/ (hoặc port 3000)
echo     - Tài khoản: admin
echo     - Mật khẩu:  admin
echo  4. Hệ Thống Thu Thập Prometheus: http://localhost:8080/prometheus/ (hoặc port 9090)
echo  5. Endpoint Số Liệu Metrics:    http://localhost:8080/metrics
echo ==============================================================================
pause
