import os
import sqlite3
import uuid
import ipaddress
import socket
import urllib.request
import urllib.error
from datetime import timedelta
from urllib.parse import urlparse
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
    # 为旧数据库添加 balance 字段（幂等）
    try:
        c.execute("ALTER TABLE users ADD COLUMN balance REAL DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    c.execute("INSERT OR IGNORE INTO users (username, password, email, phone) VALUES ('admin', 'admin123', 'admin@example.com', '13800138000')")
    c.execute("INSERT OR IGNORE INTO users (username, password, email, phone) VALUES ('alice', 'alice2025', 'alice@example.com', '13900139001')")
    # 设置默认用户的初始余额
    c.execute("UPDATE users SET balance = 99999 WHERE username = 'admin'")
    c.execute("UPDATE users SET balance = 100 WHERE username = 'alice'")
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


@app.route("/page")
def dynamic_page():
    """动态页面加载：根据 name 参数读取 pages/ 下的文件并显示"""
    name = request.args.get("name", "")
    page_content = ""

    # 安全修复：定义 pages 目录的绝对路径
    PAGES_BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pages")

    if name:
        # 拼接路径后规范化，防止路径遍历攻击
        filepath = os.path.realpath(os.path.join(PAGES_BASE, name))

        # 校验路径是否在 pages 目录内
        if not filepath.startswith(PAGES_BASE):
            page_content = "页面不存在"
        elif os.path.exists(filepath) and os.path.isfile(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                page_content = f.read()
        else:
            # 尝试加上 .html 后缀再找一次
            filepath_html = os.path.realpath(os.path.join(PAGES_BASE, name + ".html"))
            if filepath_html.startswith(PAGES_BASE) and os.path.exists(filepath_html) and os.path.isfile(filepath_html):
                with open(filepath_html, "r", encoding="utf-8") as f:
                    page_content = f.read()
            else:
                page_content = "页面不存在"
    else:
        page_content = "页面不存在"

    username = session.get("username")
    user_info = None
    if username and username in USERS:
        user_info = USERS[username].copy()
        user_info.pop("password", None)

    return render_template("index.html", username=username, user=user_info, page_content=page_content)


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


@app.route("/fetch-url", methods=["POST"])
def fetch_url():
    """URL 抓取：访问用户提交的 URL 并返回响应内容（含 SSRF 防护）"""
    username = session.get("username")
    if not username:
        return redirect("/login")

    url = request.form.get("url", "").strip()
    fetch_status = None
    fetch_content = ""

    if url:
        # ===== SSRF 防护 1：协议白名单 =====
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            fetch_status = "拒绝"
            fetch_content = "不允许的协议，仅支持 http:// 和 https://"
            return render_template(
                "index.html", username=username, user=USERS.get(username),
                fetch_status=fetch_status, fetch_content=fetch_content, fetch_url=url,
            )

        # ===== SSRF 防护 2：内网地址拦截 =====
        try:
            hostname = parsed.hostname
            # 解析域名得到所有 IP 地址
            addrs = socket.getaddrinfo(hostname, None)
            for addr in addrs:
                ip = ipaddress.ip_address(addr[4][0])
                if ip.is_private or ip.is_loopback or ip.is_link_local:
                    fetch_status = "拒绝"
                    fetch_content = f"目标地址 {ip} 为内网/回环地址，禁止访问"
                    return render_template(
                        "index.html", username=username, user=USERS.get(username),
                        fetch_status=fetch_status, fetch_content=fetch_content, fetch_url=url,
                    )
                # 拦截云元数据地址
                if ip == ipaddress.ip_address("169.254.169.254"):
                    fetch_status = "拒绝"
                    fetch_content = "目标地址为云元数据服务地址，禁止访问"
                    return render_template(
                        "index.html", username=username, user=USERS.get(username),
                        fetch_status=fetch_status, fetch_content=fetch_content, fetch_url=url,
                    )
        except (socket.gaierror, ValueError) as e:
            fetch_status = "拒绝"
            fetch_content = f"无法解析目标地址：{str(e)}"
            return render_template(
                "index.html", username=username, user=USERS.get(username),
                fetch_status=fetch_status, fetch_content=fetch_content, fetch_url=url,
            )

        # ===== SSRF 防护通过，执行请求 =====
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10) as response:
                fetch_status = response.status
                raw = response.read()
                try:
                    content = raw.decode("utf-8")
                except UnicodeDecodeError:
                    content = raw.decode("utf-8", errors="replace")
                fetch_content = content[:5000]
        except urllib.error.HTTPError as e:
            fetch_status = e.code
            fetch_content = f"HTTP 错误：{e.code} {e.reason}"
        except urllib.error.URLError as e:
            fetch_status = "失败"
            fetch_content = f"URL 访问失败：{e.reason}"
        except Exception as e:
            fetch_status = "错误"
            fetch_content = f"发生异常：{str(e)}"

    return render_template(
        "index.html",
        username=username,
        user=USERS.get(username),
        fetch_status=fetch_status,
        fetch_content=fetch_content,
        fetch_url=url,
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/profile")
def profile():
    """个人中心：展示当前登录用户的资料"""
    username = session.get("username")
    if not username:
        return redirect("/login")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, username, email, phone, balance FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    conn.close()

    if not row:
        return render_template("profile.html", error="用户不存在", user=None)

    user_data = {
        "id": row[0],
        "username": row[1],
        "email": row[2] or "",
        "phone": row[3] or "",
        "balance": row[4] or 0
    }
    return render_template("profile.html", user=user_data, error=None)


@app.route("/recharge", methods=["POST"])
def recharge():
    """充值：仅允许已登录用户为自己充值（金额必须为正数）"""
    username = session.get("username")
    if not username:
        return redirect("/login")

    amount = request.form.get("amount")
    if not amount:
        return render_template("profile.html", error="请输入充值金额", user=None)

    try:
        amount = float(amount)
    except ValueError:
        return render_template("profile.html", error="金额格式错误", user=None)

    if amount <= 0:
        return render_template("profile.html", error="充值金额必须为正数", user=None)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 从 session 用户名获取当前用户 ID
    c.execute("SELECT id FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    if not row:
        conn.close()
        return redirect("/login")
    user_id = row[0]

    # 更新余额
    c.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (amount, user_id))
    conn.commit()

    # 同步内存中的 USERS 字典
    if username in USERS:
        c.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
        bal_row = c.fetchone()
        USERS[username]["balance"] = bal_row[0]

    conn.close()
    return redirect("/profile")


@app.route("/change-password", methods=["POST"])
def change_password():
    """修改密码：修改当前登录用户的密码"""
    username = session.get("username")
    if not username:
        return redirect("/login")

    new_password = request.form.get("new_password", "")

    if not new_password:
        return render_template("profile.html", error="密码不能为空", user=None)

    if len(new_password) > 128:
        return render_template("profile.html", error="输入内容过长", user=None)

    # 更新 SQLite 数据库中的密码
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET password = ? WHERE username = ?", (new_password, username))
    conn.commit()
    conn.close()

    # 同步更新内存中的 USERS 字典
    if username in USERS:
        USERS[username]["password"] = new_password

    return redirect("/profile")


@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response


if __name__ == "__main__":
    init_db()
    app.run(debug=False, host="0.0.0.0", port=5000)
