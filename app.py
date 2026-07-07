import os
from datetime import timedelta
from flask import Flask, render_template, request, redirect, session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect

app = Flask(__name__)

# ========== 安全修复：使用随机生成的强密钥 ==========
app.secret_key = os.urandom(32).hex()

# ========== 安全修复：设置 Session 过期时间（2小时） ==========
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=2)
app.config["SESSION_PERMANENT"] = True

# ========== 安全修复：启用 CSRF 保护 ==========
csrf = CSRFProtect(app)

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


@app.route("/")
def index():
    username = session.get("username")
    user_info = None
    if username and username in USERS:
        # 安全修复：传递到模板前移除密码字段
        user_info = USERS[username].copy()
        user_info.pop("password", None)
    return render_template("index.html", username=username, user=user_info)


@app.route("/login", methods=["GET", "POST"])
# 安全修复：登录接口限制每分钟最多10次
@limiter.limit("10 per minute")
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        # 安全修复：输入长度校验
        if len(username) > 50 or len(password) > 128:
            return render_template("login.html", error="输入内容过长")

        if username in USERS and USERS[username]["password"] == password:
            session["username"] = username
            session.permanent = True
            # 安全修复：传递到模板前移除密码字段
            user_info = USERS[username].copy()
            user_info.pop("password", None)
            return render_template("index.html", username=username, user=user_info)
        else:
            return render_template("login.html", error="用户名或密码错误")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ========== 安全修复：添加安全响应头 ==========
@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response


if __name__ == "__main__":
    # 安全修复：关闭 debug 模式
    app.run(debug=False, host="0.0.0.0", port=5000)
