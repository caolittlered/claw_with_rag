# Suni AI - 企业知识智能体平台

基于 OpenClaw + RAG 的企业内部知识智能问答系统。

## 🌟 功能特性

- **智能问答**: 基于企业内部知识库的自然语言问答
- **知识库管理**: 上传文档自动构建向量索引
- **用户系统**: 注册、登录、独立知识空间
- **RAG 增强**: BGE Embedding + Reranker，精准检索

## 🏗️ 项目架构

```
claw_with_rag/
├── config/
│   └── config.yaml          # 配置文件
├── docs/                     # 示例知识文档
├── src/
│   ├── rag_engine.py        # RAG 引擎
│   ├── document_processor.py # 文档处理
│   ├── api.py               # RAG API（原有）
│   ├── web_api.py           # Web 用户系统 API
│   ├── models.py            # 用户数据模型
│   └── auth.py              # JWT 认证
├── web/
│   ├── static/              # CSS/JS
│   └── templates/           # HTML 模板
├── data/
│   ├── chroma/              # 向量数据库
│   ├── user_docs/           # 用户上传文档
│   └── suni.db              # 用户数据库
├── run.py                    # 统一启动入口
└── start.bat                 # Windows 启动脚本
```

## 🚀 快速开始

### 1. 启动 OpenClaw Gateway

```bash
openclaw gateway start
```

### 2. 启动 Suni AI

**Windows:**
```powershell
.\start.bat
```

**Linux/Mac:**
```bash
python run.py
```

### 3. 访问

打开浏览器访问 http://localhost:3000

## 📝 API 接口

### 认证
- `POST /api/register` - 用户注册
- `POST /api/login` - 用户登录
- `GET /api/me` - 获取当前用户

### 聊天
- `POST /api/chat` - 与智能体对话

### 知识库
- `POST /api/knowledge/upload` - 上传文档
- `GET /api/knowledge/documents` - 文档列表
- `DELETE /api/knowledge/documents/{id}` - 删除文档

### RAG API（原有）
- `POST /search` - 搜索知识库
- `POST /index` - 索引文档
- `GET /context` - 构建 RAG 上下文

## 🔧 配置说明

编辑 `config/config.yaml`:

```yaml
# JWT 密钥（生产环境务必修改）
jwt:
  secret: "your-random-secret-key"

# 数据库
database:
  url: "sqlite+aiosqlite:///./data/suni.db"

# 知识库
knowledge:
  upload_dir: "./data/user_docs"
  max_file_size_mb: 50
```

## 🛠️ 技术栈

| 组件 | 技术 |
|------|------|
| Web 框架 | FastAPI |
| 数据库 | SQLite + SQLAlchemy |
| AI 后端 | OpenClaw Gateway |
| Embedding | BAAI/bge-large-zh-v1.5 |
| Reranker | BAAI/bge-reranker-large |
| 向量数据库 | ChromaDB |

## 📄 License

MIT License