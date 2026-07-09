# User Manager

基于 Flask 的用户管理系统，包含多项安全加固功能。

## 功能特性

- 🔐 用户登录 / 登出（Session 管理，2小时过期）
- 📝 用户注册（SQLite 持久化存储，参数化查询防注入）
- 🔍 用户搜索（支持按用户名/邮箱模糊搜索）
- 📷 头像上传（扩展名 + MIME 类型双重白名单，UUID 重命名防覆盖）
- 🛡️ CSRF 保护（Flask-WTF）
- ⏱️ 请求频率限制（Flask-Limiter，全局 200次/天、50次/小时，登录接口 10次/分钟）
- 🔑 随机生成的强 Secret Key
- 🛑 安全响应头（X-Content-Type-Options、X-Frame-Options、X-XSS-Protection）
- ✅ 输入长度校验（用户名最长50字符，密码最长128字符）
- 📦 文件上传大小限制（最大 16MB）

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 运行应用
python app.py
```

访问 http://localhost:5000

## 测试账号

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | admin123 | 管理员 |
| alice | alice2025 | 普通用户 |

## 项目结构

```
├── app.py              # 主应用
├── requirements.txt    # Python 依赖
├── .gitignore
├── static/
│   ├── css/
│   │   └── style.css   # 样式文件
│   └── uploads/        # 上传文件目录（运行时自动创建）
└── templates/
    ├── base.html       # 基础模板（导航栏）
    ├── index.html      # 首页（用户信息 + 搜索）
    ├── login.html      # 登录页
    ├── register.html   # 注册页
    └── upload.html     # 头像上传页
```

## 安全设计

- **SQL 注入防护**：所有数据库操作使用参数化查询（`?` 占位符）
- **CSRF 防护**：所有 POST 表单包含 CSRF Token
- **文件上传安全**：扩展名白名单（jpg/jpeg/png/gif/webp）+ MIME 类型校验 + UUID 重命名
- **会话安全**：Session 2小时自动过期，随机强密钥
- **频率限制**：防止暴力破解和滥用
- **安全响应头**：防止点击劫持、MIME 嗅探、XSS 攻击
