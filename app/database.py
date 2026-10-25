import os
import time
import logging
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor

logger = logging.getLogger("library.database")

class Database:
    _pool = None

    @classmethod
    def get_pool(cls):
        if cls._pool is None:
            db_host = os.environ.get("DB_HOST", "postgres")
            db_port = int(os.environ.get("DB_PORT", "5432"))
            db_name = os.environ.get("DB_NAME", "library_db")
            db_user = os.environ.get("DB_USER", "lib_app")
            db_password = os.environ.get("DB_PASSWORD", "LibAppSecurePass_2026#")

            # Retry loop for resilience during container startup
            max_retries = 10
            for attempt in range(1, max_retries + 1):
                try:
                    logger.info(f"Connecting to PostgreSQL ({db_host}:{db_port}/{db_name}) as '{db_user}'... (Attempt {attempt}/{max_retries})")
                    cls._pool = psycopg2.pool.SimpleConnectionPool(
                        minconn=1,
                        maxconn=15,
                        host=db_host,
                        port=db_port,
                        dbname=db_name,
                        user=db_user,
                        password=db_password,
                        cursor_factory=RealDictCursor,
                        connect_timeout=5
                    )
                    logger.info("Successfully established PostgreSQL connection pool.")
                    break
                except Exception as e:
                    logger.warning(f"Connection attempt {attempt} failed: {e}")
                    if attempt == max_retries:
                        logger.error("Could not connect to PostgreSQL after maximum retries.")
                        raise
                    time.sleep(3)
        return cls._pool

    @classmethod
    def execute_query(cls, query, params=None, fetch_all=True, fetch_one=False, commit=False):
        """Executes a SQL query safely using connection pooling."""
        pool_inst = cls.get_pool()
        conn = pool_inst.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(query, params or ())
                result = None
                if fetch_one:
                    result = cur.fetchone()
                elif fetch_all:
                    result = cur.fetchall()
                if commit:
                    conn.commit()
                return result
        except Exception as e:
            if commit:
                conn.rollback()
            logger.error(f"Database query error: {e} | Query: {query}")
            raise
        finally:
            pool_inst.putconn(conn)

    @classmethod
    def check_health(cls):
        """Check PostgreSQL database connectivity."""
        try:
            row = cls.execute_query("SELECT 1 AS ok;", fetch_one=True)
            return row and row.get("ok") == 1
        except Exception:
            return False

    # ========================== REPOSITORY METHODS ==========================

    @classmethod
    def get_dashboard_stats(cls):
        """Aggregate high-level library operational metrics."""
        stats = {}
        # Total & Available Books
        book_stats = cls.execute_query(
            "SELECT COUNT(id) as total_titles, COALESCE(SUM(total_copies), 0) as total_copies, COALESCE(SUM(available_copies), 0) as available_copies FROM books;",
            fetch_one=True
        )
        stats["total_titles"] = book_stats["total_titles"]
        stats["total_copies"] = book_stats["total_copies"]
        stats["available_copies"] = book_stats["available_copies"]

        # Borrowings Status
        borrow_stats = cls.execute_query("""
            SELECT 
                COUNT(*) FILTER (WHERE status = 'BORROWED') as active_borrowings,
                COUNT(*) FILTER (WHERE status = 'OVERDUE' OR (status = 'BORROWED' AND due_date < CURRENT_DATE)) as overdue_borrowings,
                COUNT(*) FILTER (WHERE status = 'RETURNED') as returned_borrowings,
                COALESCE(SUM(fine_amount), 0) as total_fines
            FROM borrowings;
        """, fetch_one=True)
        stats["active_borrowings"] = borrow_stats["active_borrowings"]
        stats["overdue_borrowings"] = borrow_stats["overdue_borrowings"]
        stats["returned_borrowings"] = borrow_stats["returned_borrowings"]
        stats["total_fines"] = float(borrow_stats["total_fines"])

        # Total Patrons
        patron_stats = cls.execute_query("SELECT COUNT(id) as total_patrons FROM patrons WHERE status = 'ACTIVE';", fetch_one=True)
        stats["total_patrons"] = patron_stats["total_patrons"]

        # Category Breakdown
        categories = cls.execute_query("""
            SELECT c.name, c.badge_color, COUNT(b.id) as book_count
            FROM categories c
            LEFT JOIN books b ON b.category_id = c.id
            GROUP BY c.id, c.name, c.badge_color
            ORDER BY book_count DESC;
        """)
        stats["categories"] = [dict(r) for r in categories]

        return stats

    @classmethod
    def get_books(cls, search=None, category_id=None, available_only=False):
        """Retrieve books with rich metadata, search, and category filters."""
        query = """
            SELECT b.*, c.name as category_name, c.badge_color, c.icon as category_icon
            FROM books b
            LEFT JOIN categories c ON b.category_id = c.id
            WHERE 1=1
        """
        params = []
        if search:
            query += " AND (b.title ILIKE %s OR b.author ILIKE %s OR b.isbn ILIKE %s)"
            pattern = f"%{search}%"
            params.extend([pattern, pattern, pattern])
        if category_id:
            query += " AND b.category_id = %s"
            params.append(category_id)
        if available_only:
            query += " AND b.available_copies > 0"
        query += " ORDER BY b.id DESC;"
        return [dict(r) for r in cls.execute_query(query, params)]

    @classmethod
    def get_categories(cls):
        """Retrieve all book categories."""
        rows = cls.execute_query("SELECT * FROM categories ORDER BY id ASC;")
        return [dict(r) for r in rows]

    @classmethod
    def get_patrons(cls, search=None):
        """Retrieve patrons with active borrowing count."""
        query = """
            SELECT p.*,
                COUNT(br.id) FILTER (WHERE br.status IN ('BORROWED', 'OVERDUE')) as current_borrowed_count
            FROM patrons p
            LEFT JOIN borrowings br ON br.patron_id = p.id
            WHERE 1=1
        """
        params = []
        if search:
            query += " AND (p.full_name ILIKE %s OR p.card_number ILIKE %s OR p.email ILIKE %s)"
            pattern = f"%{search}%"
            params.extend([pattern, pattern, pattern])
        query += " GROUP BY p.id ORDER BY p.id ASC;"
        return [dict(r) for r in cls.execute_query(query, params)]

    @classmethod
    def get_borrowings(cls, status=None):
        """Retrieve borrowings with book and patron details."""
        query = """
            SELECT br.*, 
                   b.title as book_title, b.isbn, b.shelf_location,
                   p.full_name as patron_name, p.card_number, p.phone, p.email,
                   CASE 
                       WHEN br.status = 'BORROWED' AND br.due_date < CURRENT_DATE THEN 'OVERDUE'
                       ELSE br.status
                   END as computed_status
            FROM borrowings br
            JOIN books b ON br.book_id = b.id
            JOIN patrons p ON br.patron_id = p.id
            WHERE 1=1
        """
        params = []
        if status and status != 'ALL':
            if status == 'OVERDUE':
                query += " AND (br.status = 'OVERDUE' OR (br.status = 'BORROWED' AND br.due_date < CURRENT_DATE))"
            else:
                query += " AND br.status = %s"
                params.append(status)
        query += " ORDER BY br.id DESC;"
        return [dict(r) for r in cls.execute_query(query, params)]

    @classmethod
    def create_borrowing(cls, book_id, patron_id, days=14, notes="", client_ip="127.0.0.1"):
        """Creates a borrowing transaction, updates book stock, and logs audit event."""
        pool_inst = cls.get_pool()
        conn = pool_inst.getconn()
        try:
            with conn.cursor() as cur:
                # 1. Check book availability
                cur.execute("SELECT title, available_copies FROM books WHERE id = %s FOR UPDATE;", (book_id,))
                book = cur.fetchone()
                if not book:
                    raise ValueError("Không tìm thấy sách yêu cầu.")
                if book["available_copies"] <= 0:
                    raise ValueError(f"Sách '{book['title']}' đã hết bản sao có sẵn trong kho.")

                # 2. Check patron limit
                cur.execute("""
                    SELECT p.full_name, p.max_borrow_limit,
                           COUNT(br.id) FILTER (WHERE br.status IN ('BORROWED', 'OVERDUE')) as active_count
                    FROM patrons p
                    LEFT JOIN borrowings br ON br.patron_id = p.id
                    WHERE p.id = %s
                    GROUP BY p.id;
                """, (patron_id,))
                patron = cur.fetchone()
                if not patron:
                    raise ValueError("Không tìm thấy độc giả yêu cầu.")
                if patron["active_count"] >= patron["max_borrow_limit"]:
                    raise ValueError(f"Độc giả '{patron['full_name']}' đã đạt giới hạn mượn ({patron['max_borrow_limit']} cuốn).")

                # 3. Insert borrowing
                borrow_code = f"BRW-{int(time.time())}-{book_id}"
                cur.execute("""
                    INSERT INTO borrowings (borrow_code, book_id, patron_id, borrow_date, due_date, status, notes)
                    VALUES (%s, %s, %s, CURRENT_DATE, CURRENT_DATE + %s * INTERVAL '1 day', 'BORROWED', %s)
                    RETURNING id, borrow_code, due_date;
                """, (borrow_code, book_id, patron_id, days, notes))
                new_borrow = cur.fetchone()

                # 4. Decrement book stock
                cur.execute("UPDATE books SET available_copies = available_copies - 1 WHERE id = %s;", (book_id,))

                # 5. Insert audit log
                cur.execute("""
                    INSERT INTO audit_logs (event_type, description, operator, client_ip)
                    VALUES ('BORROW_BOOK', %s, 'librarian', %s);
                """, (f"Độc giả {patron['full_name']} mượn sách '{book['title']}' (Mã: {borrow_code})", client_ip))

                conn.commit()
                return dict(new_borrow)
        except Exception:
            conn.rollback()
            raise
        finally:
            pool_inst.putconn(conn)

    @classmethod
    def return_book(cls, borrowing_id, client_ip="127.0.0.1"):
        """Returns a book, marks status, calculates fines if overdue, and updates stock."""
        pool_inst = cls.get_pool()
        conn = pool_inst.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT br.*, b.title, b.id as b_id, p.full_name,
                           CURRENT_DATE - br.due_date as overdue_days
                    FROM borrowings br
                    JOIN books b ON br.book_id = b.id
                    JOIN patrons p ON br.patron_id = p.id
                    WHERE br.id = %s FOR UPDATE;
                """, (borrowing_id,))
                record = cur.fetchone()
                if not record:
                    raise ValueError("Không tìm thấy phiếu mượn tương ứng.")
                if record["status"] == "RETURNED":
                    raise ValueError("Phiếu mượn này đã được trả trước đó.")

                overdue_days = max(0, record["overdue_days"] or 0)
                fine = overdue_days * 5000.0  # 5,000 VND / day overdue

                # Update borrowing
                cur.execute("""
                    UPDATE borrowings 
                    SET return_date = CURRENT_DATE, status = 'RETURNED', fine_amount = %s
                    WHERE id = %s;
                """, (fine, borrowing_id))

                # Increment book stock
                cur.execute("UPDATE books SET available_copies = available_copies + 1 WHERE id = %s;", (record["b_id"],))

                # Audit log
                cur.execute("""
                    INSERT INTO audit_logs (event_type, description, operator, client_ip)
                    VALUES ('RETURN_BOOK', %s, 'librarian', %s);
                """, (f"Độc giả {record['full_name']} trả sách '{record['title']}' (Quá hạn {overdue_days} ngày, phạt: {fine:,.0f} đ)", client_ip))

                conn.commit()
                return {
                    "id": borrowing_id,
                    "title": record["title"],
                    "patron_name": record["full_name"],
                    "overdue_days": overdue_days,
                    "fine_amount": fine
                }
        except Exception:
            conn.rollback()
            raise
        finally:
            pool_inst.putconn(conn)

    @classmethod
    def add_book(cls, data, client_ip="127.0.0.1"):
        """Adds a new book record."""
        query = """
            INSERT INTO books (isbn, title, author, category_id, publisher, publish_year, shelf_location, total_copies, available_copies, cover_theme, summary)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
        """
        params = (
            data["isbn"], data["title"], data["author"], data.get("category_id", 1),
            data.get("publisher", "NXB Công nghệ"), data.get("publish_year", 2024),
            data.get("shelf_location", "Kệ A1"), data.get("total_copies", 1),
            data.get("total_copies", 1), data.get("cover_theme", "gradient-indigo"),
            data.get("summary", "")
        )
        row = cls.execute_query(query, params, fetch_one=True, commit=True)
        # Log
        cls.execute_query(
            "INSERT INTO audit_logs (event_type, description, client_ip) VALUES ('ADD_BOOK', %s, %s);",
            (f"Thêm sách mới: {data['title']} (ISBN: {data['isbn']})", client_ip),
            commit=True
        )
        return row

    @classmethod
    def add_patron(cls, data, client_ip="127.0.0.1"):
        """Registers a new library member."""
        query = """
            INSERT INTO patrons (card_number, full_name, email, phone, department, patron_type, max_borrow_limit)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
        """
        params = (
            data["card_number"], data["full_name"], data["email"],
            data.get("phone", ""), data.get("department", "Công nghệ thông tin"),
            data.get("patron_type", "Sinh viên"), data.get("max_borrow_limit", 5)
        )
        row = cls.execute_query(query, params, fetch_one=True, commit=True)
        # Log
        cls.execute_query(
            "INSERT INTO audit_logs (event_type, description, client_ip) VALUES ('ADD_PATRON', %s, %s);",
            (f"Đăng ký độc giả mới: {data['full_name']} (Thẻ: {data['card_number']})", client_ip),
            commit=True
        )
        return row
