"""
Web API - 用户系统 + 聊天接口
与 RAG 引擎和 OpenClaw Gateway 集成
"""

import os
import uuid
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
import yaml
import asyncio

from models import User, UserKnowledge, init_db, get_db, async_session
from auth import hash_password, verify_password, create_access_token, get_current_user
from rag_engine import RAGEngine
from document_processor import process_file

# 加载配置
CONFIG_PATH = os.getenv("RAG_CONFIG", "./config/config.yaml")
with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

# 创建应用
app = FastAPI(
    title="Suni AI - 企业知识智能体",
    description="基于 RAG 的企业知识问答系统",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件和模板
app.mount("/static", StaticFiles(directory="web/static"), name="static")
templates = Jinja2Templates(directory="web/templates")

# RAG 引擎缓存（按用户隔离）
_rag_engines = {}

def get_user_rag_engine(user_id: int) -> RAGEngine:
    """获取用户的 RAG 引擎"""
    if user_id not in _rag_engines:
        _rag_engines[user_id] = RAGEngine(
            config_path=CONFIG_PATH,
            collection_name=f"user_{user_id}_kb"
        )
    return _rag_engines[user_id]


# ==================== 页面路由 ====================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """主页"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """登录页"""
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """注册页"""
    return templates.TemplateResponse("register.html", {"request": request})


@app.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    """聊天页面"""
    return templates.TemplateResponse("chat.html", {"request": request})


# ==================== API 模型 ====================

class RegisterRequest(BaseModel):
    email: EmailStr
    username: str
    password: str
    company: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    company: Optional[str] = None


class ChatRequest(BaseModel):
    message: str
    use_knowledge: bool = True


class ChatResponse(BaseModel):
    response: str


# ==================== 认证 API ====================

@app.post("/api/register", response_model=UserResponse)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """用户注册"""
    # 检查邮箱
    result = await db.execute(select(User).where(User.email == request.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="邮箱已被注册")
    
    # 检查用户名
    result = await db.execute(select(User).where(User.username == request.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名已被使用")
    
    # 创建用户
    user = User(
        email=request.email,
        username=request.username,
        hashed_password=hash_password(request.password),
        company=request.company
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        company=user.company
    )


@app.post("/api/login")
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """用户登录"""
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="邮箱或密码错误")
    
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账户已被禁用")
    
    # 更新登录时间
    user.last_login = datetime.utcnow()
    await db.commit()
    
    # 创建 token
    access_token = create_access_token(data={"sub": user.id})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "company": user.company
        }
    }


@app.get("/api/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "company": current_user.company,
        "chat_count": current_user.chat_count,
        "max_chats": current_user.max_chats,
        "doc_count": current_user.doc_count,
        "max_docs": current_user.max_docs,
        "remaining_chats": current_user.max_chats - current_user.chat_count,
        "remaining_docs": current_user.max_docs - current_user.doc_count
    }


# ==================== 聊天 API ====================

import json
import aiohttp
from fastapi.responses import StreamingResponse

# OpenClaw Gateway 配置
OPENCLAW_GATEWAY_URL = os.getenv("OPENCLAW_GATEWAY_URL", "http://localhost:8080")
OPENCLAW_GATEWAY_TOKEN = os.getenv("OPENCLAW_GATEWAY_TOKEN", "")


async def call_openclaw_stream(message: str, context: str = ""):
    """调用 OpenClaw Gateway 流式接口"""
    
    # 构建系统提示
    system_prompt = """你是 Suni AI 智能助手，一个基于企业知识库的AI助手。
请根据用户的问题和提供的知识库上下文给出准确、有帮助的回答。
如果上下文中有相关信息，请优先基于上下文回答；
如果没有相关信息，请基于你的知识回答，并说明这不是来自知识库的内容。"""

    # 构建完整消息
    if context:
        full_message = f"{context}\n\n用户问题：{message}"
    else:
        full_message = message
    
    # 准备请求体
    payload = {
        "message": full_message,
        "system_prompt": system_prompt,
        "stream": True
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENCLAW_GATEWAY_TOKEN}" if OPENCLAW_GATEWAY_TOKEN else ""
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{OPENCLAW_GATEWAY_URL}/v1/chat",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=300)
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    yield f"data: [ERROR]{error_text}\n\n"
                    return
                
                # 读取流式响应
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    if line.startswith('data: '):
                        data = line[6:]
                        if data == '[DONE]':
                            yield "data: [DONE]\n\n"
                            break
                        try:
                            chunk = json.loads(data)
                            if 'choices' in chunk and len(chunk['choices']) > 0:
                                delta = chunk['choices'][0].get('delta', {})
                                if 'content' in delta:
                                    content = delta['content']
                                    yield f"data: {json.dumps({'content': content})}\n\n"
                        except json.JSONDecodeError:
                            continue
    except Exception as e:
        yield f"data: [ERROR]{str(e)}\n\n"


@app.post("/api/chat/stream")
async def chat_stream(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """与智能体对话（流式输出）"""
    # 检查问答次数限制
    if current_user.chat_count >= current_user.max_chats:
        async def limit_exceeded_stream():
            yield f"data: {json.dumps({'content': '⛔ 您的免费试用次数已用完（10次）。\\n\\n如需 unlimited 使用和定制化部署，请联系我们：\\n📧 contact@suniai.com\\n📱 或扫描页面底部二维码'})}\n\n"
            yield "data: [DONE]\n\n"
        
        return StreamingResponse(
            limit_exceeded_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    
    # 获取用户的 RAG 引擎
    rag_engine = get_user_rag_engine(current_user.id)
    
    # 获取知识库上下文
    context = ""
    if request.use_knowledge:
        results = rag_engine.retrieve_with_rerank(request.message)
        if results:
            context_parts = ["【知识库相关信息】"]
            for i, r in enumerate(results[:3], 1):  # 最多取3条
                context_parts.append(f"[{i}] {r['content'][:800]}")
                context_parts.append(f"来源: {r['metadata'].get('filename', '未知')}")
            context = "\n\n".join(context_parts)
    
    # 增加问答计数
    current_user.chat_count += 1
    await db.commit()
    
    # 流式生成器
    async def generate_stream():
        try:
            # 尝试调用 OpenClaw Gateway
            gateway_url = os.getenv("OPENCLAW_GATEWAY_URL", "").strip()
            
            if gateway_url:
                # 使用 OpenClaw Gateway
                async for chunk in call_openclaw_stream(request.message, context):
                    yield chunk
            else:
                # 模拟流式输出（用于演示或Gateway未配置时）
                import asyncio
                
                if context:
                    response_text = f"根据您的知识库，我找到了以下相关信息来回答您的问题：\n\n"
                    response_text += f"关于 \"{request.message}\"，"
                    response_text += "基于知识库中的文档内容，"
                    response_text += "我可以为您提供以下解答：\n\n"
                    
                    # 模拟逐字输出
                    words = response_text.split(' ')
                    for word in words:
                        yield f"data: {json.dumps({'content': word + ' '})}\n\n"
                        await asyncio.sleep(0.05)
                    
                    # 输出知识库结果
                    results = rag_engine.retrieve_with_rerank(request.message)
                    if results:
                        for i, r in enumerate(results[:3], 1):
                            chunk_text = f"\n**参考{i}**: {r['content'][:300]}...\n"
                            chunk_text += f"📁 来源: {r['metadata'].get('filename', '未知')}\n"
                            for char in chunk_text:
                                yield f"data: {json.dumps({'content': char})}\n\n"
                                await asyncio.sleep(0.01)
                    
                    remaining = current_user.max_chats - current_user.chat_count
                    footer = f"\n\n---\n💡 剩余 {remaining} 次免费问答机会"
                    for char in footer:
                        yield f"data: {json.dumps({'content': char})}\n\n"
                        await asyncio.sleep(0.01)
                else:
                    response_text = f"您好！我是 Suni AI 智能助手。\n\n"
                    response_text += f"您的问题是：{request.message}\n\n"
                    response_text += "💡 提示：上传企业文档后，我可以基于您的内部知识库为您提供更准确的回答。\n\n"
                    response_text += "当前未使用知识库增强，因为您还没有上传文档或选择不使用知识库。"
                    
                    for char in response_text:
                        yield f"data: {json.dumps({'content': char})}\n\n"
                        await asyncio.sleep(0.01)
                
                yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: [ERROR]{str(e)}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/api/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """与智能体对话（基于 RAG，非流式）"""
    # 检查问答次数限制
    if current_user.chat_count >= current_user.max_chats:
        return ChatResponse(
            response="⛔ 您的免费试用次数已用完（10次）。\n\n"
                    "如需 unlimited 使用和定制化部署，请联系我们：\n"
                    "📧 contact@suniai.com\n"
                    "📱 或扫描页面底部二维码"
        )
    
    # 获取用户的 RAG 引擎
    rag_engine = get_user_rag_engine(current_user.id)
    
    # 获取上下文
    context = ""
    if request.use_knowledge:
        context = rag_engine.build_context(request.message)
    
    # 增加问答计数
    current_user.chat_count += 1
    await db.commit()
    
    # 如果有知识库上下文，构建增强提示
    if context:
        # 这里可以接入 OpenClaw Gateway 或直接调用 LLM
        # 暂时返回 RAG 检索结果
        results = rag_engine.retrieve_with_rerank(request.message)
        
        if results:
            response_parts = ["根据您的知识库，找到以下相关信息：\n"]
            for i, r in enumerate(results, 1):
                response_parts.append(f"**[{i}]** {r['content'][:500]}...")
                response_parts.append(f"📁 来源: {r['metadata'].get('filename', '未知')}")
                response_parts.append(f"📊 相关度: {r['score']:.2f}\n")
            
            remaining = current_user.max_chats - current_user.chat_count
            response_parts.append(f"\n---\n💡 剩余 {remaining} 次免费问答机会")
            
            return ChatResponse(response="\n".join(response_parts))
        else:
            remaining = current_user.max_chats - current_user.chat_count
            return ChatResponse(
                response=f"抱歉，在您的知识库中没有找到相关信息。请尝试上传相关文档或换一种问法。\n\n"
                        f"---\n💡 剩余 {remaining} 次免费问答机会"
            )
    else:
        remaining = current_user.max_chats - current_user.chat_count
        return ChatResponse(
            response=f"您好！我是企业知识智能助手。请上传您的企业文档，我可以帮您查询和解答相关问题。\n\n"
                    f"---\n💡 剩余 {remaining} 次免费问答机会"
        )


# ==================== 知识库 API ====================

@app.post("/api/knowledge/upload")
async def upload_knowledge(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """上传知识文档"""
    # 检查文档数量限制
    if current_user.doc_count >= current_user.max_docs:
        raise HTTPException(
            status_code=400, 
            detail="您的免费文档配额已满（10个）。如需更多容量，请联系我们定制化部署。"
        )
    
    # 检查文件类型
    allowed_extensions = ['.txt', '.pdf', '.docx', '.xlsx', '.md']
    file_ext = Path(file.filename).suffix.lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {file_ext}")
    
    # 读取文件内容
    content = await file.read()
    max_size = 50 * 1024 * 1024  # 50MB
    if len(content) > max_size:
        raise HTTPException(status_code=400, detail="文件过大（最大 50MB）")
    
    # 保存文件
    upload_dir = Path(config.get('knowledge', {}).get('upload_dir', './data/user_docs')) / str(current_user.id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = upload_dir / file.filename
    with open(file_path, "wb") as f:
        f.write(content)
    
    # 增加文档计数
    current_user.doc_count += 1
    
    # 创建记录
    doc = UserKnowledge(
        user_id=current_user.id,
        filename=file.filename,
        file_path=str(file_path),
        file_size=len(content),
        file_type=file_ext
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    
    # 异步索引
    asyncio.create_task(index_user_document(doc.id))
    
    return {
        "message": "上传成功，正在建立索引...",
        "document_id": doc.id,
        "filename": file.filename
    }


async def index_user_document(document_id: int):
    """异步索引用户文档"""
    async with async_session() as db:
        result = await db.execute(
            select(UserKnowledge).where(UserKnowledge.id == document_id)
        )
        doc = result.scalar_one_or_none()
        if not doc:
            return
        
        try:
            # 处理文档
            document = process_file(doc.file_path, doc.user_id)
            if not document:
                return
            
            # 索引
            rag_engine = get_user_rag_engine(doc.user_id)
            chunk_count = rag_engine.index_documents([document])
            
            # 更新状态
            doc.is_indexed = True
            doc.chunk_count = chunk_count
            await db.commit()
            
            print(f"[Knowledge] 用户 {doc.user_id} 文档索引完成: {doc.filename}, {chunk_count} 片段")
        
        except Exception as e:
            print(f"[Knowledge] 索引失败: {e}")


@app.get("/api/knowledge/documents")
async def list_documents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """列出用户的知识文档"""
    result = await db.execute(
        select(UserKnowledge)
        .where(UserKnowledge.user_id == current_user.id)
        .order_by(UserKnowledge.uploaded_at.desc())
    )
    documents = result.scalars().all()
    
    return {
        "documents": [
            {
                "id": doc.id,
                "filename": doc.filename,
                "file_size": doc.file_size,
                "file_type": doc.file_type,
                "is_indexed": doc.is_indexed,
                "chunk_count": doc.chunk_count,
                "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None
            }
            for doc in documents
        ]
    }


@app.delete("/api/knowledge/documents/{document_id}")
async def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除知识文档"""
    result = await db.execute(
        select(UserKnowledge)
        .where(UserKnowledge.id == document_id)
        .where(UserKnowledge.user_id == current_user.id)
    )
    doc = result.scalar_one_or_none()
    
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    # 删除文件
    file_path = Path(doc.file_path)
    if file_path.exists():
        file_path.unlink()
    
    # 删除记录
    await db.delete(doc)
    
    # 减少文档计数
    if current_user.doc_count > 0:
        current_user.doc_count -= 1
    
    await db.commit()
    
    return {"message": "已删除"}


# ==================== 启动 ====================

@app.on_event("startup")
async def startup_event():
    """启动时初始化"""
    await init_db()
    print("[Suni AI] Web 服务启动完成")