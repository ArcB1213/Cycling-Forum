"""
邮件服务模块 - 使用 SMTP 发送邮件
"""
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# 邮件服务配置 - 从环境变量读取
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.qq.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")  # QQ邮箱使用授权码
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "Cycling Forum")
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

# 前端URL配置
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: Optional[str] = None
) -> bool:
    """
    发送邮件
    
    Args:
        to_email: 收件人邮箱
        subject: 邮件主题
        html_content: HTML格式的邮件内容
        text_content: 纯文本格式的邮件内容（可选）
    
    Returns:
        bool: 发送是否成功
    """
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.error("SMTP配置不完整，请检查环境变量 SMTP_USER 和 SMTP_PASSWORD")
        return False
    
    try:
        # 创建邮件
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = formataddr((SMTP_FROM_NAME, SMTP_USER))
        msg["To"] = to_email
        
        # 添加纯文本内容
        if text_content:
            msg.attach(MIMEText(text_content, "plain", "utf-8"))
        
        # 添加HTML内容
        msg.attach(MIMEText(html_content, "html", "utf-8"))
        
        # 发送邮件
        server = None
        try:
            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30)
            if SMTP_USE_TLS:
                server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, to_email, msg.as_string())
            logger.info(f"邮件发送成功: {to_email}")
            return True
        finally:
            # 安全关闭连接，忽略关闭时的异常
            if server:
                try:
                    server.quit()
                except Exception as close_error:
                    logger.debug(f"关闭SMTP连接时出现异常（可忽略）: {close_error}")
                    pass

        
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP认证失败: {e}")
        return False
    except smtplib.SMTPException as e:
        logger.error(f"SMTP错误: {e}")
        return False
    except Exception as e:
        logger.error(f"发送邮件时发生错误: {e}")
        return False


def send_verification_email(to_email: str, nickname: str, token: str) -> bool:
    """
    发送邮箱验证邮件
    
    Args:
        to_email: 收件人邮箱
        nickname: 用户昵称
        token: 验证令牌
    
    Returns:
        bool: 发送是否成功
    """
    verification_link = f"{FRONTEND_URL}/verify-email?token={token}"
    
    subject = "【Cycling Forum】请验证您的邮箱"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                text-align: center;
                border-radius: 10px 10px 0 0;
            }}
            .content {{
                background: #f9f9f9;
                padding: 30px;
                border: 1px solid #e0e0e0;
                border-top: none;
                border-radius: 0 0 10px 10px;
            }}
            .button {{
                display: inline-block;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 12px 30px;
                text-decoration: none;
                border-radius: 5px;
                margin: 20px 0;
                font-weight: bold;
            }}
            .button:hover {{
                opacity: 0.9;
            }}
            .footer {{
                text-align: center;
                color: #888;
                font-size: 12px;
                margin-top: 20px;
            }}
            .link {{
                word-break: break-all;
                color: #667eea;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🚴 Cycling Forum</h1>
            <p>邮箱验证</p>
        </div>
        <div class="content">
            <h2>您好，{nickname}！</h2>
            <p>感谢您注册 Cycling Forum！请点击下方按钮验证您的邮箱地址：</p>
            <p style="text-align: center;">
                <a href="{verification_link}" class="button">验证邮箱</a>
            </p>
            <p>如果按钮无法点击，请复制以下链接到浏览器地址栏：</p>
            <p class="link">{verification_link}</p>
            <p><strong>注意：</strong>此链接将在 24 小时后失效。</p>
            <p>如果您没有注册 Cycling Forum 账号，请忽略此邮件。</p>
        </div>
        <div class="footer">
            <p>此邮件由系统自动发送，请勿直接回复。</p>
            <p>© 2025 Cycling Forum. All rights reserved.</p>
        </div>
    </body>
    </html>
    """
    
    text_content = f"""
    您好，{nickname}！
    
    感谢您注册 Cycling Forum！
    
    请访问以下链接验证您的邮箱地址：
    {verification_link}
    
    注意：此链接将在 24 小时后失效。
    
    如果您没有注册 Cycling Forum 账号，请忽略此邮件。
    
    © 2025 Cycling Forum
    """
    
    return send_email(to_email, subject, html_content, text_content)


def send_password_reset_email(to_email: str, nickname: str, token: str) -> bool:
    """
    发送密码重置邮件
    
    Args:
        to_email: 收件人邮箱
        nickname: 用户昵称
        token: 重置令牌
    
    Returns:
        bool: 发送是否成功
    """
    reset_link = f"{FRONTEND_URL}/reset-password?token={token}"
    
    subject = "【Cycling Forum】密码重置请求"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                color: white;
                padding: 30px;
                text-align: center;
                border-radius: 10px 10px 0 0;
            }}
            .content {{
                background: #f9f9f9;
                padding: 30px;
                border: 1px solid #e0e0e0;
                border-top: none;
                border-radius: 0 0 10px 10px;
            }}
            .button {{
                display: inline-block;
                background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                color: white;
                padding: 12px 30px;
                text-decoration: none;
                border-radius: 5px;
                margin: 20px 0;
                font-weight: bold;
            }}
            .button:hover {{
                opacity: 0.9;
            }}
            .footer {{
                text-align: center;
                color: #888;
                font-size: 12px;
                margin-top: 20px;
            }}
            .link {{
                word-break: break-all;
                color: #f5576c;
            }}
            .warning {{
                background: #fff3cd;
                border: 1px solid #ffc107;
                padding: 15px;
                border-radius: 5px;
                margin: 15px 0;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🔐 Cycling Forum</h1>
            <p>密码重置</p>
        </div>
        <div class="content">
            <h2>您好，{nickname}！</h2>
            <p>我们收到了您的密码重置请求。请点击下方按钮设置新密码：</p>
            <p style="text-align: center;">
                <a href="{reset_link}" class="button">重置密码</a>
            </p>
            <p>如果按钮无法点击，请复制以下链接到浏览器地址栏：</p>
            <p class="link">{reset_link}</p>
            <div class="warning">
                <strong>⚠️ 安全提示：</strong>
                <ul>
                    <li>此链接将在 1 小时后失效</li>
                    <li>如果您没有请求重置密码，请忽略此邮件</li>
                    <li>请勿将此链接分享给他人</li>
                </ul>
            </div>
        </div>
        <div class="footer">
            <p>此邮件由系统自动发送，请勿直接回复。</p>
            <p>© 2025 Cycling Forum. All rights reserved.</p>
        </div>
    </body>
    </html>
    """
    
    text_content = f"""
    您好，{nickname}！
    
    我们收到了您的密码重置请求。
    
    请访问以下链接设置新密码：
    {reset_link}
    
    安全提示：
    - 此链接将在 1 小时后失效
    - 如果您没有请求重置密码，请忽略此邮件
    - 请勿将此链接分享给他人
    
    © 2025 Cycling Forum
    """
    
    return send_email(to_email, subject, html_content, text_content)
