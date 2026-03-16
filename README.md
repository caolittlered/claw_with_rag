# 企业知识库 RAG Agent

基于 OpenClaw + RAG 的企业内部知识搜索 Agent，支持一键部署。

## 🚀 特性

- **智能问答**: 基于企业内部知识库的精准问答
- **多格式支持**: txt, pdf, docx, xlsx 等常见文档格式
- **中文优化**: 使用 BGE 系列模型，针对中文优化
- **重排序**: BGE Reranker 提升检索精度
- **一键部署**: 完整安装脚本，快速上线

## 📦 技术栈

| 组件 | 技术选型 |
|------|----------|
| Agent 框架 | OpenClaw |
| LLM | 阿里云百炼 GLM-5 |
| Embedding | BAAI/bge-large-zh-v1.5 |
| Reranker | BAAI/bge-reranker-large |
| 向量数据库 | ChromaDB |
| 文档处理 | LangChain |

## 🛠️ 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/caolittlered/claw_with_rag.git
cd claw_with_rag
```

### 2. 运行安装脚本

**Linux/Mac:**
```bash
chmod +x scripts/install.sh
./scripts/install.sh
```

**Windows:**
```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
.\scripts\install.ps1
```

### 3. 配置 API 密钥

编辑 `config/.env`:
```env
ALIYUN_API_KEY=your_aliyun_api_key
FEISHU_APP_ID=your_feishu_app_id
FEISHU_APP_SECRET=your_feishu_app_secret
```

### 4. 下载模型

首次使用需要下载 BGE 模型（约 2GB）：

```bash
# 国内用户推荐使用镜像
python scripts/download_models.py --mirror

# 国外用户直接下载
python scripts/download_models.py
```

或者配置环境变量：
```bash
# Linux/Mac
export HF_ENDPOINT=https://hf-mirror.com

# Windows PowerShell
$env:HF_ENDPOINT = "https://hf-mirror.com"
```

### 5. 添加知识文档

将企业文档放入 `docs/` 目录：
```
docs/
├── 员工手册.pdf
├── 报销流程.docx
├── 公司制度.xlsx
└── ...
```

### 6. 索引文档

```bash
python src/main.py index
```

### 7. 测试搜索

```bash
python src/main.py search "公司请假流程是什么？"
```

## 📁 项目结构

```
claw_with_rag/
├── config/                 # 配置文件
│   ├── config.yaml        # 主配置
│   ├── openclaw.json      # OpenClaw 配置模板
│   └── .env.example       # 环境变量模板
├── docs/                   # 知识文档目录
├── src/                    # 核心代码
│   ├── rag_engine.py      # RAG 引擎
│   ├── document_processor.py  # 文档处理
│   └── main.py            # 命令行工具
├── skills/                 # OpenClaw Skills
│   └── internal-search/   # 内部知识搜索 Skill
├── scripts/               # 安装脚本
│   ├── install.sh         # Linux/Mac
│   └── install.ps1        # Windows
├── data/                   # 数据目录 (自动创建)
│   └── chroma/            # 向量数据库
├── requirements.txt       # Python 依赖
└── README.md
```

## ⚙️ 配置说明

### RAG 配置 (config/config.yaml)

```yaml
rag:
  retrieval:
    top_k: 10              # 初始召回数量
    rerank_top_k: 5        # 重排后返回数量
    similarity_threshold: 0.5  # 相似度阈值
  
  chunking:
    chunk_size: 500        # 文档切分大小
    chunk_overlap: 50      # 切分重叠
```

### 内部问题关键词

在 `config/config.yaml` 中配置用于识别内部问题的关键词：

```yaml
internal_keywords:
  - "公司"
  - "内部"
  - "员工"
  - "流程"
  - "制度"
  # 添加更多...
```

## 🔧 高级用法

### 自定义 Embedding 模型

```yaml
rag:
  embedding:
    model: "BAAI/bge-large-zh-v1.5"
    device: "cuda"  # 使用 GPU 加速
```

### 调整相似度阈值

降低阈值会返回更多结果，但可能降低相关性：
```yaml
rag:
  retrieval:
    similarity_threshold: 0.3  # 更宽松
```

## 🌐 部署到 VPS

### 1. 准备 VPS

推荐配置：
- CPU: 2核+
- 内存: 4GB+
- 存储: 20GB+
- 系统: Ubuntu 22.04 / CentOS 8

### 2. 安装依赖

```bash
# 安装 Python
sudo apt update
sudo apt install python3 python3-pip python3-venv -y

# 安装 Node.js
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install nodejs -y

# 安装 OpenClaw
sudo npm install -g openclaw
```

### 3. 部署项目

```bash
git clone https://github.com/caolittlered/claw_with_rag.git
cd claw_with_rag
./scripts/install.sh
```

### 4. 配置飞书

1. 创建飞书应用: https://open.feishu.cn/app
2. 配置事件订阅和权限
3. 填入 App ID 和 App Secret

### 5. 启动服务

```bash
# 启动 OpenClaw
openclaw gateway start

# 配置飞书 Webhook
openclaw config set channels.feishu.appId YOUR_APP_ID
openclaw config set channels.feishu.appSecret YOUR_SECRET
```

## 📝 示例

### 员工问答

```
用户: 我们公司的年假政策是什么？
Agent: 根据公司规定，员工年假如下：
- 工作满1年不满10年：5天
- 工作满10年不满20年：10天
- 工作满20年：15天
（来源：员工手册.pdf）

用户: 报销需要哪些材料？
Agent: 报销需要以下材料：
1. 正规发票原件
2. 费用明细单
3. 相关审批单据
（来源：报销流程.docx）
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 License

MIT License