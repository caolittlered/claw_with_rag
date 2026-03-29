"""
邮箱服务模块 - 发送验证码邮件（优化版）
支持异步发送、连接池、超时控制
"""

import smtplib
import ssl
import asyncio
import socket
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import logging
import yaml
import os

logger = logging.getLogger(__name__)

# 加载配置
CONFIG_PATH = os.getenv("RAG_CONFIG", "./config/config.yaml")
with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

email_config = config.get('email', {})


class EmailService:
    """邮件服务类 - 优化版"""

    def __init__(self):
        self.smtp_host = email_config.get('smtp_host', 'smtp.gmail.com')
        self.smtp_port = email_config.get('smtp_port', 587)
        self.smtp_user = email_config.get('smtp_user', '')
        self.smtp_password = email_config.get('smtp_password', '')
        self.from_name = email_config.get('from_name', 'Suni AI')
        self.from_email = email_config.get('from_email', self.smtp_user)
        self.use_tls = email_config.get('use_tls', True)
        self.debug_mode = email_config.get('debug_mode', False)

        # 连接超时设置（秒）
        self.connection_timeout = 10
        self.send_timeout = 15
        
    def _create_verification_email(self, to_email: str, code: str, username: str = "") -> MIMEMultipart:
        """创建验证码邮件"""
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f'{self.from_name} - 邮箱验证码'
        msg['From'] = f'{self.from_name} <{self.from_email}>'
        msg['To'] = to_email
        
        # 称呼
        greeting = f"尊敬的 {username}" if username else "尊敬的用户"
        
        # HTML 内容
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; padding: 20px; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }}
                .header {{ background: linear-gradient(135deg, #6366f1 0%, #06b6d4 100%); padding: 40px 30px; text-align: center; }}
                .header h1 {{ color: white; margin: 0; font-size: 24px; }}
                .header p {{ color: rgba(255,255,255,0.9); margin: 10px 0 0; }}
                .content {{ padding: 40px 30px; }}
                .greeting {{ font-size: 16px; color: #333; margin-bottom: 20px; }}
                .code-box {{ background: linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%); border-radius: 12px; padding: 30px; text-align: center; margin: 30px 0; }}
                .code {{ font-size: 42px; font-weight: bold; color: #6366f1; letter-spacing: 8px; font-family: 'Courier New', monospace; }}
                .expiry {{ font-size: 14px; color: #6b7280; margin-top: 15px; }}
                .warning {{ background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px 20px; margin: 30px 0; border-radius: 0 8px 8px 0; }}
                .warning-title {{ font-weight: bold; color: #92400e; margin-bottom: 5px; }}
                .warning-text {{ color: #a16207; font-size: 14px; }}
                .footer {{ background: #f9fafb; padding: 30px; text-align: center; border-top: 1px solid #e5e7eb; }}
                .footer p {{ color: #9ca3af; font-size: 12px; margin: 5px 0; }}
                .brand {{ color: #6366f1; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🌟 Suni AI</h1>
                    <p>专注小企业AI赋能</p>
                </div>
                <div class="content">
                    <p class="greeting">{greeting}，您好！</p>
                    <p style="color: #4b5563; line-height: 1.6;">感谢您注册 Suni AI。请使用以下验证码完成邮箱验证：</p>
                    
                    <div class="code-box">
                        <div class="code">{code}</div>
                        <div class="expiry">⏰ 验证码有效期：10分钟</div>
                    </div>
                    
                    <div class="warning">
                        <div class="warning-title">⚠️ 安全提示</div>
                        <div class="warning-text">
                            • 请勿将验证码透露给他人<br>
                            • 验证码有效期为10分钟<br>
                            • 如非本人操作，请忽略此邮件
                        </div>
                    </div>
                    
                    <p style="color: #6b7280; font-size: 14px; line-height: 1.6;">
                        如有任何问题，请联系我们的支持团队。<br>
                        📧 请查看配置文件中的联系邮箱
                    </p>
                </div>
                <div class="footer">
                    <p>此邮件由 <span class="brand">Suni AI</span> 系统自动发送</p>
                    <p>© 2026 Suni AI. 专注小企业AI赋能</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # 纯文本内容（备用）
        text_content = f"""
{greeting}，您好！

感谢您注册 Suni AI。请使用以下验证码完成邮箱验证：

验证码：{code}
有效期：10分钟

⚠️ 安全提示：
- 请勿将验证码透露给他人
- 验证码有效期为10分钟
- 如非本人操作，请忽略此邮件

如有任何问题，请联系支持团队（请查看配置文件中的联系邮箱）

---
此邮件由 Suni AI 系统自动发送
© 2026 Suni AI. 专注小企业AI赋能
        """
        
        # 添加内容
        msg.attach(MIMEText(text_content, 'plain', 'utf-8'))
        msg.attach(MIMEText(html_content, 'html', 'utf-8'))
        
        return msg
    
    def _send_sync(self, msg: MIMEMultipart, to_email: str) -> bool:
        """同步发送邮件（在线程中执行）"""
        server = None
        try:
            # 设置 socket 超时
            socket.setdefaulttimeout(self.connection_timeout)

            logger.info(f"[Email] 连接 SMTP: {self.smtp_host}:{self.smtp_port}, use_tls={self.use_tls}")

            # 连接 SMTP 服务器
            if self.use_tls:
                # STARTTLS 模式 (端口 587)
                context = ssl.create_default_context()
                server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=self.connection_timeout)
                server.starttls(context=context)
                logger.info("[Email] STARTTLS 连接已建立")
            else:
                # SSL 模式 (端口 465)
                context = ssl.create_default_context()
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=self.connection_timeout, context=context)
                logger.info("[Email] SSL 连接已建立")

            # 登录
            logger.info(f"[Email] 正在登录: {self.smtp_user}")
            server.login(self.smtp_user, self.smtp_password)
            logger.info("[Email] 登录成功")

            # 发送邮件
            server.send_message(msg)
            logger.info(f"[Email] 邮件已发送至 {to_email}")

            # 关闭连接
            server.quit()

            logger.info(f"[Email] 验证码邮件已成功发送至 {to_email}")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"[Email] SMTP 认证失败: {e}")
            logger.error("[Email] 可能原因：授权码错误或邮箱未开启SMTP服务")
            return False
        except smtplib.SMTPServerDisconnected as e:
            logger.error(f"[Email] SMTP 服务器断开连接: {e}")
            logger.error("[Email] 可能原因：1. 端口错误 2. 网络不稳定 3. 邮箱服务器限制")
            return False
        except socket.timeout:
            logger.error(f"[Email] 连接 SMTP 超时")
            logger.error(f"[Email] 尝试连接: {self.smtp_host}:{self.smtp_port}")
            return False
        except socket.gaierror as e:
            logger.error(f"[Email] 无法解析 SMTP 服务器地址: {e}")
            return False
        except OSError as e:
            logger.error(f"[Email] 网络错误: {e}")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"[Email] SMTP 错误: {e}")
            return False
        except Exception as e:
            logger.error(f"[Email] 发送邮件失败: {type(e).__name__}: {e}")
            return False
        finally:
            # 恢复默认超时
            socket.setdefaulttimeout(None)
            # 确保连接关闭
            if server:
                try:
                    server.close()
                except:
                    pass
    
    async def send_verification_code(self, to_email: str, code: str, username: str = "") -> bool:
        """
        异步发送验证码邮件

        Args:
            to_email: 收件人邮箱
            code: 验证码
            username: 用户名（可选）

        Returns:
            bool: 发送是否成功
        """
        if not self.smtp_user or not self.smtp_password:
            logger.error("[Email] SMTP 配置不完整，请检查 config/config.yaml")
            return False

        # 调试模式：只打印验证码到日志，不真正发送
        if self.debug_mode:
            logger.info(f"[Email] 调试模式 - 验证码: {code} -> {to_email}")
            logger.info(f"[Email] 如需真正发送邮件，请将 debug_mode 设为 false")
            return True

        # 检查网络连通性
        try:
            # 测试 DNS 解析
            socket.getaddrinfo(self.smtp_host, None)
        except socket.gaierror:
            logger.error(f"[Email] 无法解析 SMTP 服务器地址: {self.smtp_host}")
            logger.error("[Email] 可能原因：1. 无网络连接 2. DNS 解析失败 3. 防火墙阻止")
            logger.error("[Email] 建议：使用国内邮箱(QQ/163)或开启代理")
            return False

        # 创建邮件
        msg = self._create_verification_email(to_email, code, username)

        # 在线程中执行同步 SMTP 操作
        try:
            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(None, self._send_sync, msg, to_email),
                timeout=self.send_timeout + self.connection_timeout
            )
            return result
        except asyncio.TimeoutError:
            logger.error(f"[Email] 发送邮件超时（总超时 {self.send_timeout + self.connection_timeout}秒）")
            return False
        except Exception as e:
            logger.error(f"[Email] 异步发送失败: {e}")
            return False


# 全局邮件服务实例
email_service = EmailService()
