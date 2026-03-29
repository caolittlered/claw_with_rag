"""
安全防护模块 - 防止恶意操作
包含：敏感信息过滤、危险操作拦截、输入验证、审计日志
"""

import re
import json
import logging
from typing import Tuple, List, Dict, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# 安全审计日志文件
SECURITY_LOG_FILE = Path("/tmp/security_audit.log")


@dataclass
class SecurityCheckResult:
    """安全检查结果"""
    is_safe: bool
    reason: str = ""
    action: str = "allow"  # allow, block, warn


class SecurityGuard:
    """
    安全防护守卫
    
    功能：
    1. 敏感信息泄露防护（API Key、密码、配置等）
    2. 危险操作拦截（删除、修改系统文件等）
    3. 恶意指令检测
    4. 输入内容过滤
    """
    
    def __init__(self):
        # 敏感信息模式
        self.sensitive_patterns = {
            'api_key': [
                r'api[_-]?key\s*[:=]\s*["\']?[a-zA-Z0-9_-]{16,}["\']?',
                r'apikey\s*[:=]\s*["\']?[a-zA-Z0-9_-]{16,}["\']?',
                r'secret[_-]?key\s*[:=]\s*["\']?[a-zA-Z0-9_-]{16,}["\']?',
                r'app[_-]?secret\s*[:=]\s*["\']?[a-zA-Z0-9_-]{16,}["\']?',
                r'token\s*[:=]\s*["\']?[a-zA-Z0-9_-]{16,}["\']?',
                r'password\s*[:=]\s*["\'][^"\']+["\']?',
                r'passwd\s*[:=]\s*["\'][^"\']+["\']?',
                r'pwd\s*[:=]\s*["\'][^"\']+["\']?',
                r'jwt[_-]?secret\s*[:=]\s*["\']?[a-zA-Z0-9_-]+["\']?',
            ],
            'config_file': [
                r'config\.yaml',
                r'config\.json',
                r'\.env',
                r'settings\.py',
                r'credentials',
            ],
            'system_path': [
                r'/etc/',
                r'/root/',
                r'/var/',
                r'/usr/',
                r'C:\\Windows',
                r'C:\\Program Files',
            ]
        }
        
        # 危险操作关键词
        self.dangerous_keywords = [
            # 删除操作
            '删除所有', '全部删除', '清空数据库', 'drop database', 'drop table',
            'rm -rf', 'del /f', 'format ', '删除系统', '删除核心',

            # 系统命令执行
            'exec(', 'eval(', 'system(', 'os.system', 'subprocess.call',
            '__import__', 'import os', 'import subprocess',

            # 配置获取
            '查看配置', '显示配置', '获取配置', '读取配置',
            'config内容', '配置文件内容', '查看密钥', '显示密钥',

            # 敏感操作
            '修改配置', '更改配置', '更新配置', '写入配置',
            '绕过', '破解', '注入', '攻击', '漏洞',

            # 文件操作
            '删除文件', '删除文档', '清空文件夹', '删除目录',
            '覆盖文件', '修改系统文件', '删除所有文档',

            # 文件列表泄露防护
            '有哪些文件', '有什么文件', '列出文件', '查看文件',
            '显示文件', '文件列表', '所有文件', '文件目录',
            'ls -', 'dir ', 'list files', 'show files',
            '查看目录', '显示目录', '目录结构', '文件结构',
        ]
        
        # 允许的正常操作关键词（白名单）
        self.allowed_keywords = [
            '删除我的', '删除这个', '删除这份', '删除当前',
            '删除选中的', '删除上传的',
        ]
        
        # 系统提示词注入防护
        self.system_prompt_injection = [
            r'忽略.*指令',
            r'忽略.*提示',
            r'忽略.*规则',
            r'绕过.*限制',
            r'forget.*previous',
            r'ignore.*instruction',
            r'system.*prompt',
            r'你是.*现在',
            r'你现在是',
            r'扮演.*角色',
        ]
    
    def check_sensitive_info(self, text: str) -> SecurityCheckResult:
        """
        检查是否包含敏感信息
        
        Returns:
            SecurityCheckResult: 检查结果
        """
        text_lower = text.lower()
        
        # 检查 API Key 模式
        for pattern in self.sensitive_patterns['api_key']:
            if re.search(pattern, text, re.IGNORECASE):
                logger.warning(f"[Security] 检测到敏感信息泄露尝试: API Key/密码模式")
                return SecurityCheckResult(
                    is_safe=False,
                    reason="检测到尝试获取或泄露敏感信息（API Key、密码等）",
                    action="block"
                )
        
        # 检查配置文件访问
        for pattern in self.sensitive_patterns['config_file']:
            if re.search(pattern, text, re.IGNORECASE):
                # 进一步检查是否是恶意意图
                malicious_intent = any(kw in text_lower for kw in [
                    '查看', '显示', '读取', '内容', '给我', '告诉我',
                    '查看配置', '显示配置', '配置内容', '密钥'
                ])
                if malicious_intent:
                    logger.warning(f"[Security] 检测到配置文件访问尝试: {pattern}")
                    return SecurityCheckResult(
                        is_safe=False,
                        reason="检测到尝试访问系统配置文件",
                        action="block"
                    )
        
        # 检查系统路径访问
        for pattern in self.sensitive_patterns['system_path']:
            if pattern in text:
                logger.warning(f"[Security] 检测到系统路径访问: {pattern}")
                return SecurityCheckResult(
                    is_safe=False,
                    reason="检测到尝试访问系统敏感路径",
                    action="block"
                )
        
        return SecurityCheckResult(is_safe=True)
    
    def check_dangerous_operations(self, text: str) -> SecurityCheckResult:
        """
        检查是否包含危险操作
        
        Returns:
            SecurityCheckResult: 检查结果
        """
        text_lower = text.lower()
        
        # 检查白名单（允许的操作）
        for allowed in self.allowed_keywords:
            if allowed in text_lower:
                # 在白名单中，跳过检查
                return SecurityCheckResult(is_safe=True)
        
        # 检查危险关键词
        for keyword in self.dangerous_keywords:
            if keyword in text_lower:
                logger.warning(f"[Security] 检测到危险操作: {keyword}")
                return SecurityCheckResult(
                    is_safe=False,
                    reason=f"检测到潜在的危险操作请求",
                    action="block"
                )
        
        return SecurityCheckResult(is_safe=True)
    
    def check_prompt_injection(self, text: str) -> SecurityCheckResult:
        """
        检查提示词注入攻击
        
        Returns:
            SecurityCheckResult: 检查结果
        """
        for pattern in self.system_prompt_injection:
            if re.search(pattern, text, re.IGNORECASE):
                logger.warning(f"[Security] 检测到提示词注入尝试: {pattern}")
                return SecurityCheckResult(
                    is_safe=False,
                    reason="检测到尝试绕过系统安全限制",
                    action="block"
                )
        
        return SecurityCheckResult(is_safe=True)
    
    def check_user_input(self, text: str, user_id: int = None) -> SecurityCheckResult:
        """
        综合检查用户输入
        
        Args:
            text: 用户输入文本
            user_id: 用户ID（用于日志）
            
        Returns:
            SecurityCheckResult: 检查结果
        """
        user_info = f"用户 {user_id}" if user_id else "未知用户"
        
        # 1. 检查敏感信息
        result = self.check_sensitive_info(text)
        if not result.is_safe:
            logger.warning(f"[Security] {user_info} 敏感信息检查失败: {result.reason}")
            # 记录审计日志
            security_auditor.log_event(
                event_type='sensitive_info_attempt',
                user_id=user_id,
                details={
                    'reason': result.reason,
                    'input_preview': text[:100] + '...' if len(text) > 100 else text
                },
                blocked=True
            )
            return result
        
        # 2. 检查危险操作
        result = self.check_dangerous_operations(text)
        if not result.is_safe:
            logger.warning(f"[Security] {user_info} 危险操作检查失败: {result.reason}")
            # 记录审计日志
            security_auditor.log_event(
                event_type='dangerous_operation_attempt',
                user_id=user_id,
                details={
                    'reason': result.reason,
                    'input_preview': text[:100] + '...' if len(text) > 100 else text
                },
                blocked=True
            )
            return result
        
        # 3. 检查提示词注入
        result = self.check_prompt_injection(text)
        if not result.is_safe:
            logger.warning(f"[Security] {user_info} 提示词注入检查失败: {result.reason}")
            # 记录审计日志
            security_auditor.log_event(
                event_type='prompt_injection_attempt',
                user_id=user_id,
                details={
                    'reason': result.reason,
                    'input_preview': text[:100] + '...' if len(text) > 100 else text
                },
                blocked=True
            )
            return result
        
        return SecurityCheckResult(is_safe=True)
    
    def sanitize_for_logging(self, text: str) -> str:
        """
        清理日志中的敏感信息

        Args:
            text: 原始文本

        Returns:
            str: 清理后的文本
        """
        # 替换可能的敏感信息
        sanitized = text

        # 替换 API Key 模式
        sanitized = re.sub(
            r'(api[_-]?key|apikey|secret|token)\s*[:=]\s*["\']?[a-zA-Z0-9_-]{8,}["\']?',
            r'\1=***REDACTED***',
            sanitized,
            flags=re.IGNORECASE
        )

        # 替换密码
        sanitized = re.sub(
            r'(password|passwd|pwd)\s*[:=]\s*["\'][^"\']+["\']?',
            r'\1=***REDACTED***',
            sanitized,
            flags=re.IGNORECASE
        )

        return sanitized


class ResponseFilter:
    """
    响应过滤器 - 过滤 AI 响应中的敏感信息
    """

    def __init__(self):
        # 文件列表模式
        self.file_list_patterns = [
            r'你有\s*\d+\s*个文件',
            r'文件列表[：:]',
            r'以下是.*文件',
            r'您的文件[：:]',
            r'上传的文件[：:]',
            r'\.doc[\s\n]',
            r'\.pdf[\s\n]',
            r'\.txt[\s\n]',
            r'\.docx[\s\n]',
        ]

        # 系统路径模式
        self.path_patterns = [
            r'/tmp/[^\s\n]+',
            r'/root/[^\s\n]+',
            r'/home/[^\s\n]+',
            r'/var/[^\s\n]+',
            r'/etc/[^\s\n]+',
            r'C:\\\\[^\s\n]+',
        ]

    def contains_file_list(self, text: str) -> bool:
        """检查是否包含文件列表"""
        # 检查是否包含多个文件名
        file_extensions = ['.doc', '.docx', '.pdf', '.txt', '.xlsx', '.xls', '.md']
        file_count = sum(text.count(ext) for ext in file_extensions)

        # 如果包含3个或以上文件扩展名，认为是文件列表
        if file_count >= 3:
            return True

        # 检查文件列表模式
        for pattern in self.file_list_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True

        return False

    def contains_system_paths(self, text: str) -> bool:
        """检查是否包含系统路径"""
        for pattern in self.path_patterns:
            if re.search(pattern, text):
                return True
        return False

    def filter_response(self, text: str) -> Tuple[str, bool]:
        """
        过滤响应内容

        Returns:
            Tuple[str, bool]: (过滤后的文本, 是否被过滤)
        """
        # 检查文件列表
        if self.contains_file_list(text):
            logger.warning("[ResponseFilter] 检测到文件列表泄露，已过滤")
            filtered_text = "抱歉，我无法提供文件列表信息。如有需要请联系管理员。"
            return filtered_text, True

        # 检查系统路径
        if self.contains_system_paths(text):
            logger.warning("[ResponseFilter] 检测到系统路径泄露，已过滤")
            # 移除系统路径
            filtered_text = text
            for pattern in self.path_patterns:
                filtered_text = re.sub(pattern, '[REDACTED]', filtered_text)
            return filtered_text, True

        return text, False


# 全局响应过滤器
response_filter = ResponseFilter()


# 全局安全守卫实例
security_guard = SecurityGuard()


def get_security_response(reason: str) -> str:
    """
    获取安全拦截的统一回复
    
    Args:
        reason: 拦截原因
        
    Returns:
        str: 友好的拒绝回复
    """
    return f"""⚠️ 安全提醒

您的请求涉及系统安全限制，无法执行。

原因：{reason}

如有正当需求，请联系管理员（请查看配置文件中的联系邮箱）"""


class SecurityAuditor:
    """
    安全审计记录器
    
    记录所有安全相关事件，便于后续分析
    """
    
    def __init__(self, log_file: Path = SECURITY_LOG_FILE):
        self.log_file = log_file
        # 确保日志目录存在
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
    
    def log_event(self, event_type: str, user_id: int, details: Dict, blocked: bool = False):
        """
        记录安全事件
        
        Args:
            event_type: 事件类型 (sensitive_info, dangerous_operation, prompt_injection, etc.)
            user_id: 用户ID
            details: 事件详情
            blocked: 是否被拦截
        """
        event = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'user_id': user_id,
            'blocked': blocked,
            'details': details
        }
        
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(event, ensure_ascii=False) + '\n')
        except Exception as e:
            logger.error(f"[SecurityAuditor] 写入日志失败: {e}")
    
    def get_recent_events(self, user_id: Optional[int] = None, limit: int = 100) -> List[Dict]:
        """
        获取最近的安全事件
        
        Args:
            user_id: 可选，过滤特定用户
            limit: 返回数量限制
            
        Returns:
            List[Dict]: 事件列表
        """
        events = []
        
        if not self.log_file.exists():
            return events
        
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            for line in reversed(lines[-limit:]):
                try:
                    event = json.loads(line.strip())
                    if user_id is None or event.get('user_id') == user_id:
                        events.append(event)
                except json.JSONDecodeError:
                    continue
                    
        except Exception as e:
            logger.error(f"[SecurityAuditor] 读取日志失败: {e}")
        
        return events


# 全局审计记录器
security_auditor = SecurityAuditor()
