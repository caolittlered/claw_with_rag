# Internal Knowledge Search Skill

Internal knowledge RAG search skill for OpenClaw. When users ask questions about company internal matters, automatically search the knowledge base first.

## When to Activate

Activate when:
- User asks questions containing internal keywords (company, policy, process, employee, etc.)
- User specifically requests internal knowledge search
- Query matches configured internal keywords in config/config.yaml

## How It Works

1. Detect if query is internal-related using keywords
2. If yes, search the vector database using RAG
3. Return relevant context to augment the response
4. Let the LLM generate final answer with retrieved context

## Configuration

Edit `config/config.yaml` to customize:
- `rag.retrieval.top_k`: Initial retrieval count (default: 10)
- `rag.retrieval.rerank_top_k`: Results after reranking (default: 5)
- `rag.retrieval.similarity_threshold`: Minimum similarity score (default: 0.5)
- `internal_keywords`: Keywords to identify internal queries

## Setup

1. Index your documents first:
   ```bash
   python src/main.py index --docs-dir ./docs
   ```

2. Configure your API keys in `config/.env`

3. Start OpenClaw with this skill enabled

## Example Usage

User: "我们公司的请假流程是什么？"
→ Skill detects "公司" and "流程" keywords
→ Searches knowledge base
→ Returns relevant policy documents
→ LLM answers with context

User: "员工报销需要什么材料？"
→ Skill detects "员工" keyword
→ Searches for reimbursement policy
→ Returns relevant information