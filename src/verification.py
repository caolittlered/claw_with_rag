"""
验证码管理模块 - 带防刷机制
包含：验证码生成、存储、验证、频率限制
"""

import random
import string
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
from dataclasses import dataclass, field
import logging
import yaml
import os

logger = logging.getLogger(__name__)

# 加载配置
CONFIG_PATH = os.getenv("RAG_CONFIG", "./config/config.yaml")
with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

verification_config = config.get('verification', {})
CODE_LENGTH = verification_config.get('code_length', 6)
CODE_EXPIRE_MINUTES = verification_config.get('code_expire_minutes', 10)
SEND_INTERVAL_SECONDS = verification_config.get('send_interval_seconds', 60)
MAX_DAILY_PER_EMAIL = verification_config.get('max_daily_per_email', 5)
MAX_DAILY_PER_IP = verification_config.get('max_daily_per_ip', 10)


@dataclass
class VerificationCode:
    """验证码数据类"""
    code: str
    email: str
    created_at: float
    expires_at: float
    attempts: int = 0
    max_attempts: int = 3
    verified: bool = False
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        return time.time() > self.expires_at
    
    def is_valid(self) -> bool:
        """检查是否有效（未过期且未验证过）"""
        return not self.is_expired() and not self.verified
    
    def can_attempt(self) -> bool:
        """检查是否还可以尝试验证"""
        return self.attempts < self.max_attempts and not self.is_expired()


@dataclass
class RateLimitRecord:
    """频率限制记录"""
    count: int = 0
    first_request_time: float = field(default_factory=time.time)
    last_request_time: float = field(default_factory=time.time)
    
    def is_expired(self, window_hours: int = 24) -> bool:
        """检查记录是否过期（默认24小时）"""
        return time.time() - self.first_request_time > window_hours * 3600
    
    def reset(self):
        """重置记录"""
        self.count = 0
        self.first_request_time = time.time()
        self.last_request_time = time.time()


class VerificationManager:
    """
    验证码管理器
    
    功能：
    1. 生成验证码
    2. 存储验证码（内存缓存）
    3. 验证验证码
    4. 频率限制（防刷）
    """
    
    def __init__(self):
        # 验证码存储: {email: VerificationCode}
        self._codes: Dict[str, VerificationCode] = {}
        
        # 邮箱频率限制: {email: RateLimitRecord}
        self._email_limits: Dict[str, RateLimitRecord] = {}
        
        # IP频率限制: {ip: RateLimitRecord}
        self._ip_limits: Dict[str, RateLimitRecord] = {}
        
        # 滑动验证码/行为验证的临时token: {token: {email, expires_at}}
        self._captcha_tokens: Dict[str, Dict] = {}
    
    def _generate_code(self, length: int = CODE_LENGTH) -> str:
        """
        生成随机验证码
        
        使用数字+大写字母，排除容易混淆的字符（0, O, 1, I, L）
        """
        # 排除容易混淆的字符
        chars = ''.join(c for c in (string.digits + string.ascii_uppercase) 
                       if c not in '0O1IL')
        return ''.join(random.choices(chars, k=length))
    
    def _cleanup_expired(self):
        """清理过期的验证码和频率限制记录"""
        current_time = time.time()
        
        # 清理过期验证码
        expired_emails = [
            email for email, code in self._codes.items() 
            if code.is_expired()
        ]
        for email in expired_emails:
            del self._codes[email]
        
        # 清理过期频率限制
        expired_limits = [
            key for key, record in self._email_limits.items()
            if record.is_expired()
        ]
        for key in expired_limits:
            del self._email_limits[key]
        
        expired_ip_limits = [
            key for key, record in self._ip_limits.items()
            if record.is_expired()
        ]
        for key in expired_ip_limits:
            del self._ip_limits[key]
        
        # 清理过期captcha token
        expired_tokens = [
            token for token, data in self._captcha_tokens.items()
            if current_time > data.get('expires_at', 0)
        ]
        for token in expired_tokens:
            del self._captcha_tokens[token]
    
    def check_rate_limit(self, email: str, ip: str) -> Tuple[bool, str]:
        """
        检查频率限制
        
        Returns:
            (是否允许发送, 错误信息)
        """
        self._cleanup_expired()
        current_time = time.time()
        
        # 检查邮箱频率
        email_record = self._email_limits.get(email)
        if email_record:
            if email_record.is_expired():
                email_record.reset()
            elif email_record.count >= MAX_DAILY_PER_EMAIL:
                return False, f"该邮箱今日发送次数已达上限（{MAX_DAILY_PER_EMAIL}次），请明天再试"
        
        # 检查IP频率
        ip_record = self._ip_limits.get(ip)
        if ip_record:
            if ip_record.is_expired():
                ip_record.reset()
            elif ip_record.count >= MAX_DAILY_PER_IP:
                return False, f"该IP今日发送次数已达上限，请明天再试"
        
        # 检查发送间隔
        if email in self._codes:
            last_code = self._codes[email]
            time_since_last = current_time - last_code.created_at
            if time_since_last < SEND_INTERVAL_SECONDS:
                wait_seconds = int(SEND_INTERVAL_SECONDS - time_since_last)
                return False, f"发送过于频繁，请{wait_seconds}秒后再试"
        
        return True, ""
    
    def create_verification_code(self, email: str, ip: str) -> Tuple[str, bool, str]:
        """
        创建新的验证码
        
        Args:
            email: 邮箱地址
            ip: 用户IP地址
            
        Returns:
            (验证码, 是否成功, 错误信息)
        """
        # 检查频率限制
        allowed, error_msg = self.check_rate_limit(email, ip)
        if not allowed:
            return "", False, error_msg
        
        # 生成验证码
        code = self._generate_code()
        current_time = time.time()
        
        # 存储验证码
        self._codes[email] = VerificationCode(
            code=code,
            email=email,
            created_at=current_time,
            expires_at=current_time + (CODE_EXPIRE_MINUTES * 60)
        )
        
        # 更新频率限制
        if email not in self._email_limits:
            self._email_limits[email] = RateLimitRecord()
        self._email_limits[email].count += 1
        self._email_limits[email].last_request_time = current_time
        
        if ip not in self._ip_limits:
            self._ip_limits[ip] = RateLimitRecord()
        self._ip_limits[ip].count += 1
        self._ip_limits[ip].last_request_time = current_time
        
        logger.info(f"[Verification] 为 {email} 生成验证码，IP: {ip}")
        return code, True, ""
    
    def verify_code(self, email: str, code: str) -> Tuple[bool, str]:
        """
        验证验证码
        
        Args:
            email: 邮箱地址
            code: 用户输入的验证码
            
        Returns:
            (是否验证成功, 错误信息)
        """
        self._cleanup_expired()
        
        # 检查是否存在验证码
        if email not in self._codes:
            return False, "验证码不存在或已过期，请重新获取"
        
        record = self._codes[email]
        
        # 检查是否已验证过
        if record.verified:
            return False, "该验证码已使用，请重新获取"
        
        # 检查是否过期
        if record.is_expired():
            return False, "验证码已过期，请重新获取"
        
        # 检查尝试次数
        if not record.can_attempt():
            return False, "验证失败次数过多，请重新获取验证码"
        
        # 增加尝试次数
        record.attempts += 1
        
        # 验证验证码（不区分大小写）
        if code.upper() != record.code:
            remaining = record.max_attempts - record.attempts
            return False, f"验证码错误，还剩{remaining}次尝试机会"
        
        # 验证成功
        record.verified = True
        logger.info(f"[Verification] {email} 验证码验证成功")
        return True, ""
    
    def remove_code(self, email: str):
        """删除验证码（验证成功后调用）"""
        if email in self._codes:
            del self._codes[email]
    
    # ==================== 真人验证（行为验证）====================
    
    def generate_captcha_challenge(self) -> Tuple[str, str]:
        """
        生成简单的数学验证码挑战（作为真人验证）
        
        Returns:
            (token, 问题文本)
        """
        # 生成简单数学题
        num1 = random.randint(1, 20)
        num2 = random.randint(1, 20)
        operation = random.choice(['+', '-'])
        
        if operation == '+':
            answer = num1 + num2
            question = f"{num1} + {num2} = ?"
        else:
            # 确保结果为正数
            if num1 < num2:
                num1, num2 = num2, num1
            answer = num1 - num2
            question = f"{num1} - {num2} = ?"
        
        # 生成token
        token = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
        
        # 存储答案
        self._captcha_tokens[token] = {
            'answer': str(answer),
            'expires_at': time.time() + 300,  # 5分钟有效
            'verified': False
        }
        
        return token, question
    
    def verify_captcha(self, token: str, answer: str) -> Tuple[bool, str]:
        """
        验证数学验证码
        
        Returns:
            (是否验证成功, 错误信息)
        """
        if token not in self._captcha_tokens:
            return False, "验证已过期，请刷新页面重试"
        
        record = self._captcha_tokens[token]
        
        if time.time() > record['expires_at']:
            del self._captcha_tokens[token]
            return False, "验证已过期，请刷新页面重试"
        
        if record['verified']:
            return False, "该验证已使用，请刷新页面重试"
        
        if answer.strip() != record['answer']:
            return False, "答案错误，请重试"
        
        # 标记为已验证
        record['verified'] = True
        return True, ""
    
    def is_captcha_verified(self, token: str) -> bool:
        """检查验证码是否已通过验证"""
        if token not in self._captcha_tokens:
            return False
        return self._captcha_tokens[token].get('verified', False)


# 全局验证码管理器实例
verification_manager = VerificationManager()
