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


@app.get("/api/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        company=current_user.company
    )


# ==================== 聊天 API ====================

@app.post("/api/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user)
):
    """与智能体对话（基于 RAG）"""
    # 获取用户的 RAG 引擎
    rag_engine = get_user_rag_engine(current_user.id)
    
    # 获取上下文
    context = ""
    if request.use_knowledge:
        context = rag_engine.build_context(request.message)
    
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
            
            return ChatResponse(response="\n".join(response_parts))
        else:
            return ChatResponse(response="抱歉，在您的知识库中没有找到相关信息。请尝试上传相关文档或换一种问法。")
    else:
        return ChatResponse(response="您好！我是企业知识智能助手。请上传您的企业文档，我可以帮您查询和解答相关问题。")


# ==================== 知识库 API ====================

@app.post("/api/knowledge/upload")
async def upload_knowledge(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """上传知识文档"""
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
    await db.commit()
    
    return {"message": "已删除"}


# ==================== 启动 ====================

@app.on_event("startup")
async def startup_event():
    """启动时初始化"""
    await init_db()
    print("[Suni AI] Web 服务启动完成")