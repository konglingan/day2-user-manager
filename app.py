import os
import sqlite3
import uuid
from datetime import timedelta
from flask import Flask, render_template, request, redirect, session, url_for
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from werkzeug.utils import secure_filename

app = Flask(__name__)

# ========== 安全修复：使用随机生成的强密钥 ==========
app.secret_key = os.urandom(32).hex()

# ========== 安全修复：设置 Session 过期时间（2小时） ==========
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=2)
app.config["SESSION_PERMANENT"] = True

# ========== 安全修复：启用 CSRF 保护 ==========
csrf = CSRFProtect(app)

# ========== 上传配置：限制最大 16MB ==========
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "uploads")

# ========== 文件上传安全配置：白名单 ==========
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}
ALLOWED_MIMETYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}


def allowed_file(filename):
    """检查文件扩展名是否在白名单中"""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# ========== 安全修复：添加请求频率限制 ==========
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)

USERS = {
    "admin": {
        "username": "admin",
        "password": "admin123",
        "role": "admin",
        "email": "admin@example.com",
        "phone": "13800138000",
        "balance": 99999
    },
    "alice": {
        "username": "alice",
        "password": "alice2025",
        "role": "user",
        "email": "alice@example.com",
        "phone": "13900139001",
        "balance": 100
    }
}

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "users.db")


def init_db():
    """初始化数据库，创建 users 表并插入默认用户"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        email TEXT,
        phone TEXT
    )''')
    c.execute("INSERT OR IGNORE INTO users (username, password, email, phone) VALUES ('admin', 'admin123', 'admin@example.com', '13800138000')")
    c.execute("INSERT OR IGNORE INTO users (username, password, email, phone) VALUES ('alice', 'alice2025', 'alice@example.com', '13900139001')")
    conn.commit()
    conn.close()


@app.route("/")
def index():
    username = session.get("username")
    user_info = None
    if username and username in USERS:
        user_info = USERS[username].copy()
        user_info.pop("password", None)
    return render_template("index.html", username=username, user=user_info)


@app.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if len(username) > 50 or len(password) > 128:
            return render_template("login.html", error="输入内容过长")

        user_info = None

        # 先查 USERS 字典（admin/alice）
        if username in USERS and USERS[username]["password"] == password:
            session["username"] = username
            session.permanent = True
            user_info = USERS[username].copy()
            user_info.pop("password", None)

        # 再查 SQLite 数据库（注册用户）
        if not user_info:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            sql = "SELECT username, email, phone FROM users WHERE username = ? AND password = ?"
            print(f"[SQL LOGIN] {sql}")
            c.execute(sql, (username, password))
            row = c.fetchone()
            conn.close()
            if row:
                session["username"] = username
                session.permanent = True
                user_info = {"username": row[0], "email": row[1], "phone": row[2], "role": "user", "balance": 0}

        if user_info:
            return render_template("index.html", username=username, user=user_info)
        else:
            return render_template("login.html", error="用户名或密码错误")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        email = request.form.get("email", "")
        phone = request.form.get("phone", "")

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        sql = "INSERT INTO users (username, password, email, phone) VALUES (?, ?, ?, ?)"
        print(f"[SQL] {sql}")
        try:
            c.execute(sql, (username, password, email, phone))
            conn.commit()
        except Exception as e:
            print(f"[SQL ERROR] {e}")
            conn.close()
            return render_template("register.html", error="注册失败，用户名可能已存在")
        conn.close()
        return redirect("/login?registered=1")
    return render_template("register.html")


@app.route("/search")
def search():
    keyword = request.args.get("keyword", "")
    results = []
    if keyword:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        sql = "SELECT id, username, email, phone FROM users WHERE username LIKE ? OR email LIKE ?"
        print(f"[SQL] {sql}")
        c.execute(sql, (f'%{keyword}%', f'%{keyword}%'))
        rows = c.fetchall()
        for row in rows:
            results.append({"id": row[0], "username": row[1], "email": row[2], "phone": row[3]})
        conn.close()

    username = session.get("username")
    user_info = None
    if username and username in USERS:
        user_info = USERS[username].copy()
        user_info.pop("password", None)

    return render_template("index.html", username=username, user=user_info, search_results=results, keyword=keyword)


@app.route("/upload", methods=["GET", "POST"])
def upload():
    username = session.get("username")
    if not username:
        return redirect("/login")

    uploaded_url = None
    error = None

    if request.method == "POST":
        file = request.files.get("file")
        if file and file.filename:
            # 检查文件扩展名
            if not allowed_file(file.filename):
                error = "仅允许上传图片文件（jpg、jpeg、png、gif、webp）"
            # 检查 MIME 类型
            elif file.content_type not in ALLOWED_MIMETYPES:
                error = "文件类型不合法"
            else:
                # 使用 secure_filename 过滤文件名中的特殊字符
                safe_name = secure_filename(file.filename)
                # 提取扩展名并用 UUID 重命名，防止文件覆盖
                ext = safe_name.rsplit(".", 1)[1].lower() if "." in safe_name else ""
                filename = f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex
                save_path = os.path.join(UPLOAD_FOLDER, filename)
                file.save(save_path)
                uploaded_url = url_for("static", filename=f"uploads/{filename}")
        else:
            error = "请选择要上传的文件"

    return render_template("upload.html", username=username, uploaded_url=uploaded_url, error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response


if __name__ == "__main__":
    init_db()
    app.run(debug=False, host="0.0.0.0", port=5000)
