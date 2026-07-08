# Day2 - User Manager

基于 Flask 的用户管理系统，包含以下安全功能：

## 功能特性

- 🔐 用户登录 / 登出
- 📝 用户注册
- 🔍 用户搜索
- 🛡️ CSRF 保护（Flask-WTF）
- ⏱️ 请求频率限制（Flask-Limiter）
- 🔑 随机生成的强密钥
- ⏳ Session 过期时间设置（2小时）
- 🛑 安全响应头（X-Content-Type-Options, X-Frame-Options, X-XSS-Protection）
- ✅ 输入长度校验

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
├── requirements.txt    # 依赖列表
├── static/
│   └── css/
│       └── style.css   # 样式文件
└── templates/
    ├── base.html       # 基础模板
    ├── index.html      # 首页
    ├── login.html      # 登录页
    └── register.html   # 注册页
```
