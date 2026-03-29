# Internal Knowledge Search Skill

Internal knowledge RAG search skill for OpenClaw. When users ask questions about company internal matters, automatically search the knowledge base via API.

## When to Activate

Activate when:
- User asks questions containing internal keywords (company, policy, process, employee, etc.)
- User specifically requests internal knowledge search
- Query matches configured internal keywords

## Setup

### 1. Start the RAG API Service

**重要：** 使用此 Skill 前必须先启动 RAG API 服务：

```bash
cd /path/to/claw_with_rag
python src/api.py
```

服务启动后：
- API 地址: `http://localhost:8000`
- API 文档: `http://localhost:8000/docs`

### 2. Index Your Documents

```bash
# 全量索引
python src/main.py index

# 增量索引
python src/main.py inc-index docs_inc/inc_1/
```

### 3. Configure (Optional)

设置环境变量自定义 API 地址：

```bash
export RAG_API_URL="http://localhost:8000"
export RAG_API_TIMEOUT="30"
```

## How It Works

1. Detect if query is internal-related using local keyword matching
2. Call RAG API to search the knowledge base
3. Return relevant context to augment the response
4. Let the LLM generate final answer with retrieved context

## Performance

- **API 模式**: 模型常驻内存，查询响应 100-300ms
- **无需重复加载模型**: API 启动时加载一次，后续查询复用

## API Endpoints Used

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Check if API is running |
| `/search` | POST | Search knowledge base |

## Example Usage

User: "我们公司的请假流程是什么？"
→ Skill detects "公司" and "流程" keywords
→ Calls RAG API /search endpoint
→ Returns relevant policy documents
→ LLM answers with context

User: "员工报销需要什么材料？"
→ Skill detects "员工" keyword
→ Calls API for reimbursement policy
→ Returns relevant information

## Troubleshooting

**问题**: 返回 "RAG API 服务未启动"

**解决**: 确保已启动 API 服务：
```bash
python src/api.py
```

**问题**: 连接超时

**解决**: 检查 API 地址和端口是否正确，或增加超时时间：
```bash
export RAG_API_TIMEOUT="60"
```