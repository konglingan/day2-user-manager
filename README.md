# 用户管理系统 (User Manager)

一个基于 **Flask** 构建的轻量级用户管理系统，支持用户注册、登录、信息搜索、头像上传、余额充值等功能，并集成了多项 Web 安全防护措施。

## 功能特性

- **用户认证**：注册、登录、登出，基于 Session 的身份管理
- **用户搜索**：支持按用户名或邮箱模糊搜索
- **头像上传**：支持图片上传（jpg / jpeg / png / gif / webp），UUID 重命名防覆盖
- **个人中心**：查看个人信息与账户余额
- **余额充值**：登录用户可为自己的账户充值
- **帮助中心**：动态页面加载，提供使用指南
- **安全防护**：
  - CSRF 保护（flask-wtf）
  - 随机生成的强密钥
  - Session 过期机制（2 小时）
  - 请求频率限制（200 次/天，50 次/小时）
  - 文件上传白名单（扩展名 + MIME 类型双重校验）
  - 路径遍历攻击防护
  - 安全响应头（X-Content-Type-Options、X-Frame-Options、X-XSS-Protection）

## 技术栈

| 类别       | 技术                          |
| ---------- | ----------------------------- |
| Web 框架   | Flask                         |
| 数据库     | SQLite3                       |
| 模板引擎   | Jinja2                        |
| CSRF 保护  | Flask-WTF                     |
| 频率限制   | Flask-Limiter                 |
| 前端样式   | 原生 CSS                      |

## 项目结构

```
.
├── app.py                  # 主应用程序入口
├── requirements.txt        # Python 依赖
├── templates/              # Jinja2 模板
│   ├── base.html           # 基础布局模板
│   ├── index.html          # 首页（含搜索与动态页面）
│   ├── login.html          # 登录页
│   ├── register.html       # 注册页
│   ├── profile.html        # 个人中心（含充值）
│   └── upload.html         # 头像上传页
├── pages/                  # 静态页面（动态加载）
│   └── help.html           # 帮助中心
├── static/
│   ├── css/
│   │   └── style.css       # 全局样式
│   └── uploads/            # 用户上传文件目录
├── data/                   # SQLite 数据库文件（运行时生成）
└── .gitignore
```

## 快速开始

### 环境要求

- Python 3.8+
- pip

### 安装与运行

```bash
# 1. 克隆仓库
git clone https://github.com/konglingan/user-manager.git
cd user-manager

# 2. 创建虚拟环境（推荐）
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 启动应用
python app.py
```

启动后访问 **http://localhost:5000** 即可使用。

### 默认账号

| 用户名 | 密码      | 角色  |
| ------ | --------- | ----- |
| admin  | admin123  | 管理员 |
| alice  | alice2025 | 普通用户 |

> ⚠️ 请在生产环境中修改默认密码。

## API 路由

| 路由        | 方法   | 描述               | 认证要求 |
| ----------- | ------ | ------------------ | -------- |
| `/`          | GET    | 首页               | 否       |
| `/login`     | GET/POST | 用户登录          | 否       |
| `/register`  | GET/POST | 用户注册          | 否       |
| `/logout`    | GET    | 退出登录           | 是       |
| `/profile`   | GET    | 个人中心           | 是       |
| `/recharge`  | POST   | 余额充值           | 是       |
| `/search`    | GET    | 用户搜索           | 否       |
| `/upload`    | GET/POST | 头像上传          | 是       |
| `/page`      | GET    | 动态页面加载       | 否       |

## 安全说明

本项目作为网络空间安全实训作业，展示了常见的 Web 安全漏洞修复方案：

1. **CSRF 防护**：所有 POST 表单均包含 CSRF Token
2. **文件上传安全**：白名单校验扩展名与 MIME 类型，UUID 重命名，限制文件大小（16MB）
3. **路径遍历防护**：动态页面加载使用 `os.path.realpath` 规范化路径并校验前缀
4. **频率限制**：防止暴力破解与滥用
5. **安全响应头**：`X-Content-Type-Options: nosniff`、`X-Frame-Options: DENY`、`X-XSS-Protection: 1; mode=block`

## License

MIT License
