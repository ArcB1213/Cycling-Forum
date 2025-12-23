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
    wins: Optional[int] = None  # 可选，按冠军数排序时返回
    
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


# ============ 分页模型 ============

class PaginationMeta(BaseModel):
    """分页元数据"""
    total: int  # 总记录数
    page: int  # 当前页码
    limit: int  # 每页记录数
    total_pages: int  # 总页数
    has_next: bool  # 是否有下一页
    has_prev: bool  # 是否有上一页


class PaginatedRidersResponse(BaseModel):
    """分页车手列表响应"""
    data: List[RiderBase]
    pagination: PaginationMeta


class PaginatedStageResultsResponse(BaseModel):
    """分页赛段成绩响应"""
    stage_info: StageBase
    data: List[StageResultWithRelations]
    pagination: PaginationMeta


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
    """车手参赛记录响应（分页）"""
    rider: RiderBase
    data: List[RaceRecord]
    pagination: PaginationMeta


class WinRecord(BaseModel):
    """冠军记录"""
    result_id: int
    race_name: str
    year: int
    stage_number: float
    stage_route: Optional[str]
    time_in_seconds: int
    team_name: str


class GeneralClassificationBase(BaseModel):
    """总成绩排名基础模型"""
    gc_id: int
    edition_id: int
    rider_id: int
    team_id: int
    rank: int
    time_in_seconds: int
    gap_in_seconds: Optional[int] = None
    
    model_config = ConfigDict(from_attributes=True)

class GCResultWithRelations(GeneralClassificationBase):
    """包含车手和车队名称的总成绩"""
    rider_name: Optional[str] = None
    team_name: Optional[str] = None
    race_name: Optional[str] = None
    year: Optional[int] = None

class PaginatedGCResponse(BaseModel):
    """分页总成绩响应"""
    edition_year: Optional[int] = None
    race_name: Optional[str] = None
    data: List[GCResultWithRelations]
    pagination: PaginationMeta

class GCWinRecord(BaseModel):
    """GC冠军记录"""
    gc_id: int
    race_name: str
    year: int
    time_in_seconds: int
    team_name: str

class RiderWinsResponse(BaseModel):
    """车手冠军记录响应"""
    rider: RiderBase
    win_records: List[WinRecord]
    gc_win_records: List[GCWinRecord] = []


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

# ============ 车手评分相关模型 ============

class RatingBase(BaseModel):
    """评分基础模型"""
    score: int = Field(..., ge=1, le=5, description="评分：1-5分")
    comment: Optional[str] = Field(None, max_length=500, description="评价内容（可选）")
    
    model_config = ConfigDict(from_attributes=True)


class RatingCreate(RatingBase):
    """创建评分请求"""
    rider_id: int = Field(..., description="车手ID")


class RatingResponse(RatingBase):
    """评分响应模型"""
    rating_id: int
    rider_id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    user_nickname: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class RiderRatingStatsResponse(BaseModel):
    """车手评分统计模型"""
    stat_id: int
    rider_id: int
    total_rating_count: int = Field(..., description="评价总数")
    average_score: float = Field(..., description="平均评分")
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class RiderDetailWithRatingsResponse(BaseModel):
    """包含评分的车手详细信息"""
    rider_id: int
    rider_name: str
    stats: Optional[RiderRatingStatsResponse] = None
    user_rating: Optional[RatingResponse] = None  # 当前用户的评分
    recent_ratings: List[RatingResponse] = Field(default_factory=list, description="最近的评价列表")
    
    model_config = ConfigDict(from_attributes=True)


class PaginatedRatingsResponse(BaseModel):
    """分页评价响应"""
    data: List[RatingResponse]
    pagination: dict

    model_config = ConfigDict(from_attributes=True)


# ============ 论坛相关模型 ============

class ForumPostCreate(BaseModel):
    """创建帖子请求"""
    title: str = Field(..., min_length=5, max_length=200, description="标题")
    content: str = Field(..., min_length=10, max_length=10000, description="正文")


class ForumPostBase(BaseModel):
    """帖子基础模型"""
    post_id: int
    title: str
    content: str
    author_id: int
    view_count: int
    comment_count: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ForumPostWithAuthor(ForumPostBase):
    """包含作者信息的帖子"""
    author_nickname: Optional[str] = None
    author_avatar: Optional[str] = None


class ForumPostDetail(ForumPostWithAuthor):
    """帖子详情（包含完整信息）"""
    is_deleted: bool = False


class PaginatedForumPostsResponse(BaseModel):
    """分页帖子响应"""
    data: List[ForumPostWithAuthor]
    pagination: PaginationMeta


class CommentCreate(BaseModel):
    """创建评论请求"""
    content: str = Field(..., min_length=1, max_length=2000, description="评论内容")
    parent_id: Optional[int] = Field(None, description="父评论 ID（可选，NULL 表示一级评论）")


class CommentBase(BaseModel):
    """评论基础模型"""
    comment_id: int
    content: str
    post_id: int
    author_id: int
    floor_number: Optional[int] = None
    parent_id: Optional[int] = None
    root_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CommentWithAuthor(CommentBase):
    """包含作者信息的评论"""
    author_nickname: Optional[str] = None
    author_avatar: Optional[str] = None
    replies: List['CommentWithAuthor'] = []


# 递归模型支持
CommentWithAuthor.model_rebuild()


class CommentResponse(CommentWithAuthor):
    """评论响应（包含作者信息）"""
    pass


class CommentsResponse(BaseModel):
    """评论树状响应"""
    floors: List[CommentWithAuthor]
    pagination: PaginationMeta