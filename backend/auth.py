"""
JWT 认证工具模块
处理密码加密、Token 生成和验证
"""
from datetime import datetime, timedelta
from typing import Optional
import secrets
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from models.database import get_db
from models.models import User

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 密码流
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# JWT 配置
SECRET_KEY = "cycling_forum_secret_key_change_in_production"  # 生产环境应使用环境变量
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# 邮箱验证配置
VERIFICATION_TOKEN_EXPIRE_HOURS = 24
RESET_PASSWORD_TOKEN_EXPIRE_HOURS = 1


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """加密密码"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建 Access Token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """创建 Refresh Token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(
    token: str = Depends(oauth2_scheme), 
    db: Session = Depends(get_db)
) -> User:
    """
    从 JWT Token 中获取当前用户
    用作依赖项保护需要认证的路由
    """
    print(f"[DEBUG] Received token: {token[:20]}..." if token else "[DEBUG] No token received")
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str = payload.get("sub")
        token_type: str = payload.get("type")
        print(f"[DEBUG] Decoded payload - user_id: {user_id_str}, type: {token_type}")
        
        if user_id_str is None or token_type != "access":
            print(f"[DEBUG] Invalid token - user_id: {user_id_str}, type: {token_type}")
            raise credentials_exception
        
        # 将字符串转换为整数
        user_id = int(user_id_str)
            
    except JWTError as e:
        print(f"[DEBUG] JWT decode error: {e}")
        raise credentials_exception
    except ValueError:
        print(f"[DEBUG] Invalid user_id format")
        raise credentials_exception
    
    user = db.query(User).filter(User.user_id == user_id).first()
    if user is None:
        print(f"[DEBUG] User not found with id: {user_id}")
        raise credentials_exception
    
    print(f"[DEBUG] User authenticated: {user.nickname}")
    return user


def verify_refresh_token(token: str) -> Optional[int]:
    """
    验证 Refresh Token 并返回用户 ID
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if user_id_str is None or token_type != "refresh":
            return None
        
        return int(user_id_str)
    except (JWTError, ValueError):
        return None


def generate_verification_token() -> str:
    """生成邮箱验证令牌"""
    return secrets.token_urlsafe(32)


def generate_reset_password_token() -> str:
    """生成密码重置令牌"""
    return secrets.token_urlsafe(32)


def get_verification_token_expiry() -> datetime:
    """获取验证令牌过期时间（24小时）"""
    return datetime.utcnow() + timedelta(hours=VERIFICATION_TOKEN_EXPIRE_HOURS)


def get_reset_password_token_expiry() -> datetime:
    """获取密码重置令牌过期时间（1小时）"""
    return datetime.utcnow() + timedelta(hours=RESET_PASSWORD_TOKEN_EXPIRE_HOURS)


def is_token_expired(expiry_time: Optional[datetime]) -> bool:
    """检查令牌是否过期"""
    if expiry_time is None:
        return True
    return datetime.utcnow() > expiry_time
