-- ==============================================================================
-- DATABASE INITIALIZATION SCRIPT - SMART LIBRARY MANAGEMENT SYSTEM (ATHENA)
-- Course: Triển khai và Quản trị Hệ thống Phần mềm
-- Database: PostgreSQL 16
-- Hardening: Least Privilege User + Relational Schema + Seed Data
-- ==============================================================================

-- 1. Create Core Tables
CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    code VARCHAR(30) NOT NULL UNIQUE,
    description TEXT,
    icon VARCHAR(50) DEFAULT 'fa-book',
    badge_color VARCHAR(30) DEFAULT '#0284c7',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS books (
    id SERIAL PRIMARY KEY,
    isbn VARCHAR(20) NOT NULL UNIQUE,
    title VARCHAR(255) NOT NULL,
    author VARCHAR(255) NOT NULL,
    category_id INTEGER REFERENCES categories(id) ON DELETE RESTRICT,
    publisher VARCHAR(150),
    publish_year INTEGER,
    shelf_location VARCHAR(50) NOT NULL,
    total_copies INTEGER NOT NULL DEFAULT 1 CHECK (total_copies >= 0),
    available_copies INTEGER NOT NULL DEFAULT 1 CHECK (available_copies >= 0 AND available_copies <= total_copies),
    cover_theme VARCHAR(50) DEFAULT 'gradient-cyan',
    summary TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS patrons (
    id SERIAL PRIMARY KEY,
    card_number VARCHAR(20) NOT NULL UNIQUE,
    full_name VARCHAR(150) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    phone VARCHAR(20),
    department VARCHAR(100) DEFAULT 'Công nghệ thông tin',
    patron_type VARCHAR(30) DEFAULT 'Sinh viên' CHECK (patron_type IN ('Sinh viên', 'Giảng viên', 'Nghiên cứu sinh', 'Nhân viên')),
    max_borrow_limit INTEGER DEFAULT 5,
    status VARCHAR(20) DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'SUSPENDED', 'EXPIRED')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS borrowings (
    id SERIAL PRIMARY KEY,
    borrow_code VARCHAR(30) NOT NULL UNIQUE,
    book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE RESTRICT,
    patron_id INTEGER NOT NULL REFERENCES patrons(id) ON DELETE RESTRICT,
    borrow_date DATE NOT NULL DEFAULT CURRENT_DATE,
    due_date DATE NOT NULL,
    return_date DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'BORROWED' CHECK (status IN ('BORROWED', 'RETURNED', 'OVERDUE')),
    fine_amount NUMERIC(10,2) DEFAULT 0.00,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    operator VARCHAR(100) DEFAULT 'system_admin',
    client_ip VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Indexes for High Performance Querying
CREATE INDEX IF NOT EXISTS idx_books_isbn ON books(isbn);
CREATE INDEX IF NOT EXISTS idx_books_title ON books(title);
CREATE INDEX IF NOT EXISTS idx_books_category ON books(category_id);
CREATE INDEX IF NOT EXISTS idx_borrowings_status ON borrowings(status);
CREATE INDEX IF NOT EXISTS idx_borrowings_patron ON borrowings(patron_id);
CREATE INDEX IF NOT EXISTS idx_borrowings_due_date ON borrowings(due_date);

-- 3. Seed Initial Categories
INSERT INTO categories (name, code, description, icon, badge_color) VALUES
('Công nghệ phần mềm & Lập trình', 'SE_DEV', 'Sách về kiến trúc phần mềm, DevOps, Docker, CI/CD, Python, Cloud', 'fa-code', '#38bdf8'),
('Cơ sở dữ liệu & Phân tích dữ liệu', 'DB_DATA', 'Sách về PostgreSQL, NoSQL, BigData, Machine Learning và Data Warehouse', 'fa-database', '#a855f7'),
('Mạng máy tính & An toàn thông tin', 'NET_SEC', 'Bảo mật hệ thống, Network Hardening, Pentesting, Kỹ thuật phòng thủ', 'fa-shield-halved', '#f43f5e'),
('Trí tuệ nhân tạo & Khoa học máy tính', 'AI_CS', 'Thuật toán nâng cao, Deep Learning, LLM, Computer Vision', 'fa-brain', '#10b981'),
('Kỹ năng mềm & Quản trị dự án', 'MGMT_SKILL', 'Agile/Scrum, Quản lý thời gian, Kỹ năng giao tiếp và lãnh đạo', 'fa-users', '#f59e0b')
ON CONFLICT (code) DO NOTHING;

-- 4. Seed Books with Unique Cover Gradients & Real Shelves
INSERT INTO books (isbn, title, author, category_id, publisher, publish_year, shelf_location, total_copies, available_copies, cover_theme, summary) VALUES
('978-604-0-12345-1', 'Thiết Kế Hệ Thống & Vi Dịch Vụ Với Docker', 'Nguyễn Xuân Phong', 1, 'NXB Thông Tin & Truyền Thông', 2024, 'Kệ A1 - Ngăn 02', 5, 3, 'gradient-indigo', 'Cẩm nang toàn diện về triển khai container, Nginx reverse proxy, microservices và orchestrating bằng Docker Compose.'),
('978-604-0-12345-2', 'Làm Chủ PostgreSQL: Từ Cơ Bản Đến Tối Ưu', 'Trần Đình Trọng', 2, 'NXB Khoa Học Kỹ Thuật', 2023, 'Kệ A2 - Ngăn 01', 4, 2, 'gradient-blue', 'Hướng dẫn chi tiết về cấu trúc lưu trữ PostgreSQL, indexing nâng cao, tối ưu truy vấn SQL, phân quyền an toàn.'),
('978-604-0-12345-3', 'Giám Sát Hệ Thống Với Prometheus & Grafana', 'Hoàng Minh Tuấn', 1, 'NXB Bách Khoa', 2024, 'Kệ A1 - Ngăn 04', 6, 4, 'gradient-emerald', 'Kiến trúc thu thập số liệu metrics, thiết lập exporter, xây dựng dashboard trực quan hóa hiệu năng container và database.'),
('978-604-0-12345-4', 'Quản Lý Log Tập Trung Với Loki & Promtail', 'Lê Hải Đăng', 1, 'NXB Bách Khoa', 2023, 'Kệ A1 - Ngăn 05', 3, 1, 'gradient-violet', 'Kỹ thuật thu thập log phân tán từ Docker, truy vấn log tốc độ cao với LogQL, kết hợp giám sát trên Grafana.'),
('978-604-0-12345-5', 'Hardening Máy Chủ Linux & Ứng Dụng Web', 'Phạm Quốc Bảo', 3, 'NXB An Toàn Thông Tin', 2024, 'Kệ B1 - Ngăn 01', 4, 3, 'gradient-rose', 'Các kỹ thuật tăng cường bảo mật container: non-root user, network segmentation, least privilege DB và OWASP headers.'),
('978-604-0-12345-6', 'Học Sâu & Trí Tuệ Nhân Tạo Hiện Đại', 'Nguyễn Thị Mai', 4, 'NXB Giáo Dục', 2024, 'Kệ C1 - Ngăn 03', 5, 5, 'gradient-amber', 'Nền tảng toán học, mạng nơ-ron tích chập CNN, Transformer và các mô hình thị giác máy tính tiên tiến.'),
('978-604-0-12345-7', 'Lập Trình Web Hiện Đại Với Python & FastAPI', 'Vũ Đức Thịnh', 1, 'NXB Khoa Học Kỹ Thuật', 2023, 'Kệ A3 - Ngăn 02', 4, 3, 'gradient-cyan', 'Xây dựng RESTful API tốc độ cao, xác thực JWT, tương tác async database, tích hợp OpenAPI tự động.'),
('978-604-0-12345-8', 'Nghệ Thuật Quản Trị Dự Án Phần Mềm Agile', 'Đỗ Minh Quân', 5, 'NXB Lao Động', 2022, 'Kệ D1 - Ngăn 01', 7, 6, 'gradient-orange', 'Ứng dụng thực chiến mô hình Scrum, Kanban, Jira quản lý backlog và tối ưu năng suất nhóm phát triển.')
ON CONFLICT (isbn) DO NOTHING;

-- 5. Seed Patrons (Độc giả thư viện)
INSERT INTO patrons (card_number, full_name, email, phone, department, patron_type, max_borrow_limit, status) VALUES
('LIB-2024-001', 'Nguyễn Văn An', 'an.nv@ictu.edu.vn', '0912345678', 'Công nghệ thông tin', 'Sinh viên', 5, 'ACTIVE'),
('LIB-2024-002', 'Trần Thị Bích Ngọc', 'ngoc.ttb@ictu.edu.vn', '0987654321', 'Kỹ thuật phần mềm', 'Sinh viên', 5, 'ACTIVE'),
('LIB-2024-003', 'ThS. Lê Hoàng Nam', 'nam.lh@ictu.edu.vn', '0903112233', 'Khoa CNTT', 'Giảng viên', 10, 'ACTIVE'),
('LIB-2024-004', 'Vũ Quang Huy', 'huy.vq@ictu.edu.vn', '0945678901', 'Hệ thống thông tin', 'Sinh viên', 5, 'ACTIVE'),
('LIB-2024-005', 'TS. Phan Thanh Tùng', 'tung.pt@ictu.edu.vn', '0933445566', 'Viện Nghiên cứu AI', 'Nghiên cứu sinh', 8, 'ACTIVE')
ON CONFLICT (card_number) DO NOTHING;

-- 6. Seed Borrowings (Phiếu mượn - có mượn đang diễn ra, quá hạn, và đã trả)
INSERT INTO borrowings (borrow_code, book_id, patron_id, borrow_date, due_date, return_date, status, fine_amount, notes) VALUES
('BRW-2026-0001', 1, 1, CURRENT_DATE - INTERVAL '5 days', CURRENT_DATE + INTERVAL '9 days', NULL, 'BORROWED', 0.00, 'Mượn phục vụ làm đồ án chuyên ngành'),
('BRW-2026-0002', 2, 2, CURRENT_DATE - INTERVAL '20 days', CURRENT_DATE - INTERVAL '6 days', NULL, 'OVERDUE', 30000.00, 'Quá hạn 6 ngày - Đã gửi email nhắc nhở'),
('BRW-2026-0003', 3, 3, CURRENT_DATE - INTERVAL '10 days', CURRENT_DATE + INTERVAL '20 days', NULL, 'BORROWED', 0.00, 'Giảng viên mượn nghiên cứu bài giảng'),
('BRW-2026-0004', 4, 4, CURRENT_DATE - INTERVAL '15 days', CURRENT_DATE - INTERVAL '1 days', CURRENT_DATE, 'RETURNED', 0.00, 'Đã trả sách nguyên vẹn đúng hạn'),
('BRW-2026-0005', 5, 5, CURRENT_DATE - INTERVAL '3 days', CURRENT_DATE + INTERVAL '27 days', NULL, 'BORROWED', 0.00, 'Nghiên cứu sinh mượn tài liệu bảo mật')
ON CONFLICT (borrow_code) DO NOTHING;

-- 7. Seed Audit Logs
INSERT INTO audit_logs (event_type, description, operator, client_ip) VALUES
('SYSTEM_INIT', 'Hệ thống Quản lý Thư viện Athena khởi tạo thành công với PostgreSQL', 'system', '127.0.0.1'),
('SEED_DATA', 'Nạp dữ liệu mẫu: 8 đầu sách, 5 độc giả, 5 phiếu mượn', 'system', '127.0.0.1'),
('HARDENING_APPLIED', 'Áp dụng phân quyền bảo mật Least Privilege cho tài khoản ứng dụng lib_app', 'sec_admin', '127.0.0.1');

-- ==============================================================================
-- 8. SECURITY HARDENING: LEAST PRIVILEGE APPLICATION USER (Tiêu chí 6)
-- Tạo user ứng dụng 'lib_app' với quyền hạn tối thiểu:
-- Chỉ SELECT, INSERT, UPDATE trên bảng; CẤM DROP, ALTER, TRUNCATE
-- ==============================================================================
DO
$do$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'lib_app') THEN
      CREATE USER lib_app WITH PASSWORD 'LibAppSecurePass_2026#';
   END IF;
END
$do$;

GRANT CONNECT ON DATABASE library_db TO lib_app;
GRANT USAGE ON SCHEMA public TO lib_app;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO lib_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO lib_app;
-- Ngăn lib_app xóa cấu trúc bảng hoặc can thiệp quản trị
REVOKE CREATE ON SCHEMA public FROM lib_app;
REVOKE DROP, TRUNCATE ON ALL TABLES IN SCHEMA public FROM lib_app;
