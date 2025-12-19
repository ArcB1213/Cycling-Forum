"""
Pydantic 响应模型定义
用于 FastAPI 的自动序列化和 API 文档生成
"""
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from typing import List, Optional
from datetime import datetime

# ============ 基础模型 ============

class RaceBase(BaseModel):
    """赛事基础模型"""
    race_id: int
    race_name: str
    
    model_config = ConfigDict(from_attributes=True)


class EditionBase(BaseModel):
    """届次基础模型"""
    edition_id: int
    race_id: int
    year: int
    
    model_config = ConfigDict(from_attributes=True)


class TeamBase(BaseModel):
    """车队基础模型"""
    team_id: int
    team_name: str
    
    model_config = ConfigDict(from_attributes=True)


class RiderBase(BaseModel):
    """车手基础模型"""
    rider_id: int
    rider_name: str
    
    model_config = ConfigDict(from_attributes=True)


class StageBase(BaseModel):
    """赛段基础模型"""
    stage_id: int
    edition_id: int
    stage_number: float
    stage_route: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class StageResultBase(BaseModel):
    """赛段成绩基础模型"""
    result_id: int
    stage_id: int
    rider_id: int
    team_id: int
    rank: int
    time_in_seconds: int
    
    model_config = ConfigDict(from_attributes=True)


# ============ 扩展模型（包含关联信息）============

class StageResultWithRelations(StageResultBase):
    """包含车手和车队名称的赛段成绩"""
    rider_name: Optional[str] = None
    team_name: Optional[str] = None


# ============ API 响应模型 ============

class EditionsResponse(BaseModel):
    """赛事届次列表响应"""
    race: str
    editions: List[EditionBase]


class StagesResponse(BaseModel):
    """赛段列表响应"""
    edition_year: int
    race_name: str
    stages: List[StageBase]


class StageResultsResponse(BaseModel):
    """赛段成绩响应"""
    stage_info: StageBase
    results: List[StageResultWithRelations]


class RiderStatsResponse(BaseModel):
    """车手统计响应"""
    rider: RiderBase
    stats: dict  # {"total_races": int, "stage_wins": int, "teams": List[TeamBase]}


class RaceRecord(BaseModel):
    """参赛记录"""
    result_id: int
    race_name: str
    year: int
    stage_number: float
    stage_route: Optional[str]
    rank: int
    time_in_seconds: int
    team_name: str


class RiderRacesResponse(BaseModel):
    """车手参赛记录响应"""
    rider: RiderBase
    race_records: List[RaceRecord]


class WinRecord(BaseModel):
    """冠军记录"""
    result_id: int
    race_name: str
    year: int
    stage_number: float
    stage_route: Optional[str]
    time_in_seconds: int
    team_name: str


class RiderWinsResponse(BaseModel):
    """车手冠军记录响应"""
    rider: RiderBase
    win_records: List[WinRecord]


# ============ 用户认证模型 ============

class UserRegister(BaseModel):
    """用户注册请求"""
    email: EmailStr = Field(..., description="邮箱地址")
    nickname: str = Field(..., min_length=2, max_length=50, description="昵称")
    password: str = Field(..., min_length=6, description="密码")
    avatar: Optional[str] = Field(default="/src/assets/default.jpg", description="头像 URL")


class UserLogin(BaseModel):
    """用户登录请求"""
    email: EmailStr = Field(..., description="邮箱地址")
    password: str = Field(..., description="密码")


class UserResponse(BaseModel):
    """用户信息响应"""
    user_id: int
    email: str
    nickname: str
    avatar: Optional[str]
    created_at: datetime
    is_verified: bool = False
    
    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """Token 响应"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    """刷新 Token 请求"""
    refresh_token: str


# ============ 邮箱验证和密码重置模型 ============

class EmailVerificationRequest(BaseModel):
    """邮箱验证请求（重发验证邮件）"""
    email: EmailStr = Field(..., description="邮箱地址")


class EmailVerificationResponse(BaseModel):
    """邮箱验证响应"""
    message: str
    success: bool


class VerifyEmailRequest(BaseModel):
    """验证邮箱 Token 请求"""
    token: str = Field(..., description="验证令牌")


class ForgotPasswordRequest(BaseModel):
    """忘记密码请求"""
    email: EmailStr = Field(..., description="邮箱地址")


class ResetPasswordRequest(BaseModel):
    """重置密码请求"""
    token: str = Field(..., description="重置令牌")
    new_password: str = Field(..., min_length=6, description="新密码")


class MessageResponse(BaseModel):
    """通用消息响应"""
    message: str
    success: bool = True


class RegisterResponse(BaseModel):
    """注册响应（需要验证邮箱）"""
    message: str
    email: str
    requires_verification: bool = True


# ============ 用户信息修改模型 ============

class UpdateNicknameRequest(BaseModel):
    """修改昵称请求"""
    nickname: str = Field(..., min_length=2, max_length=50, description="新昵称")


class UpdatePasswordRequest(BaseModel):
    """修改密码请求"""
    old_password: str = Field(..., description="当前密码")
    new_password: str = Field(..., min_length=6, description="新密码")
