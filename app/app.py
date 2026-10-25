import os
import sys
import time
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template, request, jsonify, Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

from database import Database

# 1. Setup Structured Logging for Loki / Promtail
LOG_DIR = os.environ.get("LOG_DIR", "/var/log/library")
os.makedirs(LOG_DIR, exist_ok=True)
log_file_path = os.path.join(LOG_DIR, "app.log")

formatter = logging.Formatter(
    '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "service": "library_web", "logger": "%(name)s", "message": "%(message)s"}'
)

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(formatter)

file_handler = RotatingFileHandler(log_file_path, maxBytes=10*1024*1024, backupCount=5, encoding="utf-8")
file_handler.setFormatter(formatter)

logger = logging.getLogger("library.app")
logger.setLevel(logging.INFO)
logger.addHandler(stream_handler)
logger.addHandler(file_handler)

# 2. Flask Application Initialization
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "AthenaSecureKey_2026_SmartLib!#")

# 3. Prometheus Metrics Setup
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP Requests processed by Library Web App",
    ["method", "endpoint", "status"]
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP Request Latency in seconds",
    ["method", "endpoint"]
)

GAUGE_TOTAL_BOOKS = Gauge("library_total_books", "Total unique book titles in library")
GAUGE_ACTIVE_LOANS = Gauge("library_active_loans", "Active ongoing book loans")
GAUGE_OVERDUE_LOANS = Gauge("library_overdue_loans", "Total overdue book loans")
GAUGE_TOTAL_PATRONS = Gauge("library_total_patrons", "Total registered library patrons")

# Request timer middleware
@app.before_request
def start_timer():
    request._start_time = time.time()

@app.after_request
def record_metrics_and_log(response):
    if hasattr(request, "_start_time"):
        latency = time.time() - request._start_time
        endpoint = request.endpoint or request.path
        status = str(response.status_code)
        method = request.method

        # Record to Prometheus
        HTTP_REQUESTS_TOTAL.labels(method=method, endpoint=endpoint, status=status).inc()
        HTTP_REQUEST_DURATION_SECONDS.labels(method=method, endpoint=endpoint).observe(latency)

        # Structured log (exclude health and metrics spam)
        if request.path not in ["/metrics", "/api/health", "/static"]:
            client_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
            logger.info(f"{method} {request.path} {status} in {latency*1000:.2f}ms from {client_ip}")

    return response

# 4. Prometheus Metrics Endpoint
@app.route("/metrics", methods=["GET"])
def metrics():
    """Prometheus Scrape Target"""
    try:
        # Refresh business gauges before scrape
        stats = Database.get_dashboard_stats()
        GAUGE_TOTAL_BOOKS.set(stats["total_titles"])
        GAUGE_ACTIVE_LOANS.set(stats["active_borrowings"])
        GAUGE_OVERDUE_LOANS.set(stats["overdue_borrowings"])
        GAUGE_TOTAL_PATRONS.set(stats["total_patrons"])
    except Exception as e:
        logger.warning(f"Could not refresh business gauges: {e}")
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

# 5. Health Check Endpoint
@app.route("/api/health", methods=["GET"])
def health():
    db_ok = Database.check_health()
    status_code = 200 if db_ok else 503
    return jsonify({
        "status": "healthy" if db_ok else "unhealthy",
        "database": "connected" if db_ok else "disconnected",
        "service": "athena_library_core",
        "timestamp": time.time()
    }), status_code

# 6. Web Frontend Route
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

# 7. REST APIs
@app.route("/api/stats", methods=["GET"])
def get_stats():
    try:
        stats = Database.get_dashboard_stats()
        # Update metrics gauges
        GAUGE_TOTAL_BOOKS.set(stats["total_titles"])
        GAUGE_ACTIVE_LOANS.set(stats["active_borrowings"])
        GAUGE_OVERDUE_LOANS.set(stats["overdue_borrowings"])
        GAUGE_TOTAL_PATRONS.set(stats["total_patrons"])
        return jsonify({"success": True, "data": stats})
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/books", methods=["GET", "POST"])
def manage_books():
    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    if request.method == "POST":
        try:
            data = request.json or {}
            required = ["isbn", "title", "author", "shelf_location"]
            for field in required:
                if not data.get(field):
                    return jsonify({"success": False, "error": f"Trường '{field}' là bắt buộc."}), 400
            new_book = Database.add_book(data, client_ip=client_ip)
            logger.info(f"BOOK_CREATED: {data['title']} (ISBN: {data['isbn']}) by IP {client_ip}")
            return jsonify({"success": True, "message": "Thêm sách thành công", "book": new_book}), 201
        except Exception as e:
            logger.error(f"Error creating book: {e}")
            return jsonify({"success": False, "error": str(e)}), 400

    # GET
    search = request.args.get("q", "").strip() or None
    category_id = request.args.get("category_id")
    available_only = request.args.get("available") == "true"
    books = Database.get_books(search=search, category_id=category_id, available_only=available_only)
    return jsonify({"success": True, "total": len(books), "data": books})

@app.route("/api/categories", methods=["GET"])
def get_categories():
    categories = Database.get_categories()
    return jsonify({"success": True, "data": categories})

@app.route("/api/patrons", methods=["GET", "POST"])
def manage_patrons():
    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    if request.method == "POST":
        try:
            data = request.json or {}
            for field in ["card_number", "full_name", "email"]:
                if not data.get(field):
                    return jsonify({"success": False, "error": f"Trường '{field}' là bắt buộc."}), 400
            new_patron = Database.add_patron(data, client_ip=client_ip)
            logger.info(f"PATRON_REGISTERED: {data['full_name']} (Card: {data['card_number']}) by IP {client_ip}")
            return jsonify({"success": True, "message": "Đăng ký độc giả thành công", "patron": new_patron}), 201
        except Exception as e:
            logger.error(f"Error creating patron: {e}")
            return jsonify({"success": False, "error": str(e)}), 400

    search = request.args.get("q", "").strip() or None
    patrons = Database.get_patrons(search=search)
    return jsonify({"success": True, "total": len(patrons), "data": patrons})

@app.route("/api/borrowings", methods=["GET", "POST"])
def manage_borrowings():
    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    if request.method == "POST":
        try:
            data = request.json or {}
            book_id = data.get("book_id")
            patron_id = data.get("patron_id")
            days = int(data.get("days", 14))
            notes = data.get("notes", "")

            if not book_id or not patron_id:
                return jsonify({"success": False, "error": "Vui lòng chọn Sách và Độc giả."}), 400

            result = Database.create_borrowing(book_id, patron_id, days=days, notes=notes, client_ip=client_ip)
            logger.info(f"BORROW_SUCCESS: Code {result['borrow_code']} for BookID {book_id} to PatronID {patron_id}")
            return jsonify({"success": True, "message": "Lập phiếu mượn sách thành công!", "borrowing": result}), 201
        except Exception as e:
            logger.warning(f"BORROW_FAILED: {e}")
            return jsonify({"success": False, "error": str(e)}), 400

    status = request.args.get("status", "ALL")
    borrowings = Database.get_borrowings(status=status)
    return jsonify({"success": True, "total": len(borrowings), "data": borrowings})

@app.route("/api/borrowings/<int:borrowing_id>/return", methods=["POST"])
def return_borrowing(borrowing_id):
    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    try:
        res = Database.return_book(borrowing_id, client_ip=client_ip)
        logger.info(f"RETURN_SUCCESS: BorrowID {borrowing_id} - '{res['title']}' returned by {res['patron_name']} (Overdue: {res['overdue_days']} days)")
        return jsonify({
            "success": True,
            "message": f"Trả sách '{res['title']}' thành công!",
            "data": res
        })
    except Exception as e:
        logger.warning(f"RETURN_FAILED: BorrowID {borrowing_id} - {e}")
        return jsonify({"success": False, "error": str(e)}), 400

# Error Handlers
@app.errorhandler(404)
def not_found(e):
    return jsonify({"success": False, "error": "Tài nguyên không tồn tại (404)"}), 404

@app.errorhandler(500)
def server_error(e):
    logger.error(f"Internal Server Error: {e}")
    return jsonify({"success": False, "error": "Lỗi máy chủ nội bộ (500)"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
