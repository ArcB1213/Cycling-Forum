# 论坛功能实现方案

## 1. 需求概述

为自行车运动数据平台添加完整的论坛功能，包括：
- 用户发布帖子（标题 + 正文）
- Write-Back 策略处理浏览量（Redis + 定时任务）
- 多级评论架构（楼层 + 子回复树状结构）
- 实时更新评论列表

---

## 2. 数据库模型设计

### 2.1 论坛帖子表 (`forum_posts`)

```python
class ForumPost(Base):
    """论坛帖子表"""
    __tablename__ = 'forum_posts'

    # 基础字段
    post_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(String(10000), nullable=False)

    # 关联字段
    author_id: Mapped[int] = mapped_column(ForeignKey('users.user_id'), nullable=False, index=True)

    # 统计字段（Write-Back 策略：Redis 异步更新）
    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    comment_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 软删除
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    # 关系
    author: Mapped["User"] = relationship(back_populates='forum_posts')
    comments: Mapped[List["ForumComment"]] = relationship(
        back_populates='post',
        lazy='select',
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index('idx_post_created_at', 'created_at'),
        Index('idx_author_created_at', 'author_id', 'created_at'),
        {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}
    )
```

### 2.2 论坛评论表 (`forum_comments`)

```python
class ForumComment(Base):
    """论坛评论表 - 支持多级嵌套"""
    __tablename__ = 'forum_comments'

    # 基础字段
    comment_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    content: Mapped[str] = mapped_column(String(2000), nullable=False)

    # 关联字段
    post_id: Mapped[int] = mapped_column(ForeignKey('forum_posts.post_id'), nullable=False, index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey('users.user_id'), nullable=False, index=True)

    # 多级嵌套支持
    # floor_number: 一级评论（楼层号），从 1 开始
    floor_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    # parent_id: 父评论 ID（NULL 表示一级评论）
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey('forum_comments.comment_id'), nullable=True, index=True)
    # root_id: 根评论 ID（指向一级评论，用于快速查询某个楼层的所有子回复）
    root_id: Mapped[Optional[int]] = mapped_column(ForeignKey('forum_comments.comment_id'), nullable=True, index=True)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 软删除
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # 关系
    post: Mapped["ForumPost"] = relationship(back_populates='comments')
    author: Mapped["User"] = relationship(back_populates='forum_comments')
    parent: Mapped[Optional["ForumComment"]] = relationship(
        back_populates='replies',
        remote_side=[comment_id]
    )
    replies: Mapped[List["ForumComment"]] = relationship(
        back_populates='parent',
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index('idx_post_created_at', 'post_id', 'created_at'),
        Index('idx_root_id', 'root_id'),
        {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}
    )
```

### 2.3 更新 User 模型关系

```python
# 在 User 模型中添加
forum_posts: Mapped[List["ForumPost"]] = relationship(
    back_populates='author',
    lazy='select',
    cascade="all, delete-orphan"
)
forum_comments: Mapped[List["ForumComment"]] = relationship(
    back_populates='author',
    lazy='select',
    cascade="all, delete-orphan"
)
```

---

## 3. Write-Back 策略实现

### 3.1 Redis 浏览量计数器

```python
# backend/forum_utils.py

import redis.asyncio as aioredis
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from models.models import ForumPost

# Redis 键前缀
POST_VIEW_KEY = "forum:post:view:{post_id}"
POST_VIEW_BATCH_KEY = "forum:post:view:batch"  # 存储需要回写的帖子 ID

async def increment_view_count(post_id: int) -> int:
    """增加帖子浏览量（仅操作 Redis）"""
    redis = await get_async_redis()

    # 使用 Hash 存储浏览量，支持批量操作
    key = POST_VIEW_KEY.format(post_id=post_id)

    # Redis HINCRBY 原子操作
    new_view_count = await redis.hincrby(key, "count", 1)

    # 设置过期时间（7 天）
    await redis.expire(key, 604800)

    # 将帖子 ID 添加到待回写集合
    await redis.sadd(POST_VIEW_BATCH_KEY, post_id)

    return new_view_count

async def get_view_count_from_redis(post_id: int) -> int:
    """从 Redis 获取浏览量"""
    redis = await get_async_redis()
    key = POST_VIEW_KEY.format(post_id=post_id)
    count = await redis.hget(key, "count")
    return int(count) if count else 0

async def get_total_view_count(db: AsyncSession, post_id: int) -> int:
    """获取总浏览量（MySQL + Redis）"""
    # 从 MySQL 获取基础浏览量
    result = await db.execute(
        select(ForumPost.view_count).filter(ForumPost.post_id == post_id)
    )
    db_view_count = result.scalar_one_or_none() or 0

    # 加上 Redis 中的增量
    redis_view_count = await get_view_count_from_redis(post_id)

    return db_view_count + redis_view_count
```

### 3.2 定时任务：批量回写到 MySQL

```python
# backend/forum_write_back_task.py

import asyncio
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, text
from models.database import get_async_db
from models.models import ForumPost
from cache import get_async_redis
import logging

logger = logging.getLogger(__name__)

# 配置
WRITE_BACK_INTERVAL = 300  # 5 分钟执行一次
BATCH_SIZE = 100  # 每次处理 100 个帖子

async def write_back_view_counts():
    """将 Redis 中的浏览量批量回写到 MySQL"""

    redis = await get_async_redis()

    # 从待回写集合获取所有帖子 ID
    batch_key = "forum:post:view:batch"
    post_ids = await redis.smembers(batch_key)

    if not post_ids:
        logger.info("没有需要回写的浏览量数据")
        return

    logger.info(f"开始回写 {len(post_ids)} 个帖子的浏览量")

    async for db in get_async_db():
        try:
            # 批量获取帖子当前浏览量
            post_id_list = [int(pid) for pid in post_ids]

            # 分批处理
            for i in range(0, len(post_id_list), BATCH_SIZE):
                batch = post_id_list[i:i + BATCH_SIZE]

                # 获取当前数据库中的浏览量
                posts = await db.execute(
                    select(ForumPost.post_id, ForumPost.view_count)
                    .filter(ForumPost.post_id.in_(batch))
                )
                current_view_counts = {row[0]: row[1] for row in posts.all()}

                # 构建批量更新
                update_cases = []
                update_params = {}

                for post_id in batch:
                    # 获取 Redis 中的增量
                    redis_key = f"forum:post:view:{post_id}"
                    redis_count = await redis.hget(redis_key, "count")
                    if not redis_count:
                        continue

                    increment = int(redis_count)
                    db_count = current_view_counts.get(post_id, 0)
                    new_count = db_count + increment

                    update_cases.append(f"WHEN {post_id} THEN :count_{post_id}")
                    update_params[f"count_{post_id}"] = new_count

                    # 清除 Redis 数据
                    await redis.delete(redis_key)

                if update_cases:
                    # 执行批量更新（使用 CASE WHEN）
                    case_statement = " ".join(update_cases)
                    query = text(f"""
                        UPDATE forum_posts
                        SET view_count = CASE post_id {case_statement} ELSE view_count END
                        WHERE post_id IN :post_ids
                    """)

                    await db.execute(query, {**update_params, "post_ids": tuple(batch)})
                    await db.commit()

                    # 从待回写集合移除已处理的帖子
                    await redis.srem(batch_key, *batch)

                    logger.info(f"已回写 {len(batch)} 个帖子的浏览量")

        except Exception as e:
            logger.error(f"回写浏览量失败: {e}")
            await db.rollback()
        break

async def write_back_scheduler():
    """定时任务调度器"""
    while True:
        try:
            await write_back_view_counts()
        except Exception as e:
            logger.error(f"定时任务执行失败: {e}")

        await asyncio.sleep(WRITE_BACK_INTERVAL)

@asynccontextmanager
async def lifespan_with_write_back(app):
    """FastAPI 生命周期管理（集成定时任务）"""
    # 启动时创建后台任务
    task = asyncio.create_task(write_back_scheduler())
    yield
    # 关闭时取消任务
    task.cancel()
```

---

## 4. 多级评论架构设计

### 4.1 数据结构

```
一级评论（楼层）
├── floor_number: 1
├── parent_id: NULL
├── root_id: NULL
│   └── 子回复 1
│       ├── parent_id: 1 (指向一级评论)
│       ├── root_id: 1 (指向一级评论)
│       └── 子回复 1-1
│           ├── parent_id: 2 (指向子回复 1)
│           └── root_id: 1 (指向根评论)
└── 子回复 2
    ├── parent_id: 1
    └── root_id: 1

一级评论（楼层）
├── floor_number: 2
├── parent_id: NULL
├── root_id: NULL
```

### 4.2 API 设计

#### 创建评论

```python
@app.post("/api/async/forum/posts/{post_id}/comments", tags=["Forum"])
async def create_comment(
    post_id: int,
    comment_data: CommentCreate,
    current_user: User = Depends(get_current_user_async),
    db: AsyncSession = Depends(get_async_db)
):
    """
    创建评论

    请求体:
    - content: 评论内容
    - parent_id: 父评论 ID（可选，NULL 表示一级评论）
    """

    # 验证帖子是否存在
    post = await db.get(ForumPost, post_id)
    if not post or post.is_deleted:
        raise HTTPException(status_code=404, detail="帖子不存在")

    floor_number = None
    root_id = None

    if comment_data.parent_id:
        # 子回复
        parent = await db.get(ForumComment, comment_data.parent_id)
        if not parent or parent.is_deleted:
            raise HTTPException(status_code=404, detail="父评论不存在")

        # 获取根评论 ID
        root_id = parent.root_id if parent.root_id else parent.comment_id
    else:
        # 一级评论：分配楼层号
        result = await db.execute(
            select(func.coalesce(func.max(ForumComment.floor_number), 0))
            .filter(
                ForumComment.post_id == post_id,
                ForumComment.parent_id.is_(None)
            )
        )
        max_floor = result.scalar() or 0
        floor_number = max_floor + 1

    # 创建评论
    new_comment = ForumComment(
        post_id=post_id,
        author_id=current_user.user_id,
        content=comment_data.content,
        parent_id=comment_data.parent_id,
        root_id=root_id,
        floor_number=floor_number
    )
    db.add(new_comment)

    # 更新帖子评论计数
    await db.execute(
        update(ForumPost)
        .filter(ForumPost.post_id == post_id)
        .values(comment_count=ForumPost.comment_count + 1)
    )

    await db.commit()
    await db.refresh(new_comment)

    # 清除缓存
    await invalidate_cache_async(f"forum:comments:{post_id}:*")

    return new_comment.to_dict()
```

#### 获取评论列表（树状结构）

```python
@app.get("/api/async/forum/posts/{post_id}/comments", tags=["Forum"])
@cache_response("forum_comments", expire=60)
async def get_post_comments(
    post_id: int,
    page: int = 1,
    limit: int = 20,
    db: AsyncSession = Depends(get_async_db)
):
    """
    获取帖子评论（树状结构）

    返回格式:
    {
        "floors": [
            {
                "comment_id": 1,
                "floor_number": 1,
                "content": "...",
                "replies": [
                    {"comment_id": 2, "content": "...", "replies": []}
                ]
            }
        ],
        "pagination": {...}
    }
    """

    # 只查询一级评论（分页）
    count_result = await db.execute(
        select(func.count())
        .select_from(ForumComment)
        .filter(
            ForumComment.post_id == post_id,
            ForumComment.parent_id.is_(None),
            ForumComment.is_deleted == False
        )
    )
    total = count_result.scalar() or 0

    total_pages = (total + limit - 1) // limit
    offset = (page - 1) * limit

    # 查询一级评论
    result = await db.execute(
        select(ForumComment)
        .options(selectinload(ForumComment.author))
        .filter(
            ForumComment.post_id == post_id,
            ForumComment.parent_id.is_(None),
            ForumComment.is_deleted == False
        )
        .order_by(ForumComment.created_at)
        .offset(offset)
        .limit(limit)
    )
    floors = result.scalars().all()

    # 为每个楼层加载所有子回复（递归）
    async def load_replies(root_id: int) -> list:
        """递归加载子回复"""
        result = await db.execute(
            select(ForumComment)
            .options(selectinload(ForumComment.author))
            .filter(
                ForumComment.root_id == root_id,
                ForumComment.comment_id != root_id,
                ForumComment.is_deleted == False
            )
            .order_by(ForumComment.created_at)
        )
        replies = result.scalars().all()

        output = []
        for reply in replies:
            reply_dict = reply.to_dict()
            # 递归加载子回复
            reply_dict['replies'] = await load_replies(reply.comment_id)
            output.append(reply_dict)

        return output

    # 构建响应
    floors_data = []
    for floor in floors:
        floor_dict = floor.to_dict()
        # 加载该楼层的所有子回复
        floor_dict['replies'] = await load_replies(floor.comment_id)
        floors_data.append(floor_dict)

    return {
        "floors": floors_data,
        "pagination": {
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    }
```

---

## 5. Pydantic Schema 设计

```python
# backend/schemas.py 添加

class ForumPostBase(BaseModel):
    """帖子基础模型"""
    post_id: int
    title: str
    content: str
    view_count: int
    comment_count: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ForumPostCreate(BaseModel):
    """创建帖子请求"""
    title: str = Field(..., min_length=5, max_length=200, description="标题")
    content: str = Field(..., min_length=10, max_length=10000, description="正文")


class ForumPostWithAuthor(ForumPostBase):
    """包含作者信息的帖子"""
    author_id: int
    author_nickname: Optional[str] = None
    author_avatar: Optional[str] = None


class CommentBase(BaseModel):
    """评论基础模型"""
    comment_id: int
    content: str
    floor_number: Optional[int] = None
    parent_id: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CommentCreate(BaseModel):
    """创建评论请求"""
    content: str = Field(..., min_length=1, max_length=2000, description="评论内容")
    parent_id: Optional[int] = Field(None, description="父评论 ID（可选）")


class CommentWithAuthor(CommentBase):
    """包含作者信息的评论"""
    author_id: int
    author_nickname: Optional[str] = None
    author_avatar: Optional[str] = None
    replies: List['CommentWithAuthor'] = []


# 递归模型支持
CommentWithAuthor.model_rebuild()


class PaginatedForumPostsResponse(BaseModel):
    """分页帖子响应"""
    data: List[ForumPostWithAuthor]
    pagination: PaginationMeta


class CommentsResponse(BaseModel):
    """评论树状响应"""
    floors: List[CommentWithAuthor]
    pagination: PaginationMeta
```

---

## 6. 前端实现

### 6.1 API 服务扩展

```typescript
// cycling-forum/src/services/ApiServices.ts

/**
 * 创建帖子
 */
export const createForumPost = async (postData: {
  title: string
  content: string
}): Promise<ForumPost> => {
  const response = await apiClient.post<ForumPost>('/async/forum/posts', postData)
  return response.data
}

/**
 * 获取帖子列表（分页）
 */
export const fetchForumPosts = async (
  page = 1,
  limit = 20
): Promise<PaginatedForumPostsResponse> => {
  const response = await apiClient.get<PaginatedForumPostsResponse>('/async/forum/posts', {
    params: { page, limit }
  })
  return response.data
}

/**
 * 获取帖子详情
 */
export const fetchForumPostDetail = async (postId: number): Promise<ForumPostDetail> => {
  const response = await apiClient.get<ForumPostDetail>(`/async/forum/posts/${postId}`)
  return response.data
}

/**
 * 增加浏览量
 */
export const incrementPostView = async (postId: number): Promise<void> => {
  await apiClient.post(`/async/forum/posts/${postId}/view`)
}

/**
 * 创建评论
 */
export const createComment = async (
  postId: number,
  commentData: { content: string; parent_id?: number }
): Promise<Comment> => {
  const response = await apiClient.post<Comment>(
    `/async/forum/posts/${postId}/comments`,
    commentData
  )
  return response.data
}

/**
 * 获取评论列表（树状）
 */
export const fetchPostComments = async (
  postId: number,
  page = 1,
  limit = 20
): Promise<CommentsResponse> => {
  const response = await apiClient.get<CommentsResponse>(
    `/async/forum/posts/${postId}/comments`,
    { params: { page, limit } }
  )
  return response.data
}
```

### 6.2 类型定义

```typescript
// cycling-forum/src/interfaces/types.ts

export interface ForumPost {
  post_id: number
  title: string
  content: string
  view_count: number
  comment_count: number
  created_at: string
  updated_at: string
  author_id: number
  author_nickname?: string
  author_avatar?: string
}

export interface ForumPostCreate {
  title: string
  content: string
}

export interface Comment {
  comment_id: number
  content: string
  floor_number?: number
  parent_id?: number
  created_at: string
  author_id: number
  author_nickname?: string
  author_avatar?: string
  replies: Comment[]
}

export interface PaginatedForumPostsResponse {
  data: ForumPost[]
  pagination: PaginationMeta
}

export interface CommentsResponse {
  floors: Comment[]
  pagination: PaginationMeta
}
```

### 6.3 Vue 组件结构

```
cycling-forum/src/views/
├── ForumView.vue                 # 论坛首页（帖子列表）
├── PostDetailView.vue            # 帖子详情（含评论）
└── CreatePostView.vue            # 创建帖子

cycling-forum/src/components/
└── forum/
    ├── PostCard.vue              # 帖子卡片
    ├── CommentTree.vue           # 评论树组件
    ├── CommentItem.vue           # 单条评论
    └── CommentForm.vue           # 评论表单
```

### 6.4 评论树组件示例

```vue
<!-- CommentTree.vue -->
<template>
  <div class="comment-tree">
    <CommentItem
      v-for="floor in comments"
      :key="floor.comment_id"
      :comment="floor"
      :post-id="postId"
      @reply="handleReply"
      @refresh="emit('refresh')"
    />
  </div>
</template>

<script setup lang="ts">
import CommentItem from './CommentItem.vue'

const props = defineProps<{
  comments: Comment[]
  postId: number
}>()

const emit = defineEmits<{
  reply: [commentId: number]
  refresh: []
}>()

const handleReply = (commentId: number) => {
  emit('reply', commentId)
}
</script>

<!-- CommentItem.vue (递归组件) -->
<template>
  <div :class="['comment-item', depth > 0 ? 'reply' : 'floor']">
    <div class="comment-header">
      <img :src="getAvatarUrl(comment.author_avatar)" class="avatar" />
      <span class="author">{{ comment.author_nickname }}</span>
      <span v-if="comment.floor_number" class="floor-number">#{{ comment.floor_number }}</span>
      <span class="time">{{ formatTime(comment.created_at) }}</span>
    </div>
    <div class="comment-content">{{ comment.content }}</div>
    <div class="comment-actions">
      <button @click="handleReply" class="btn-reply">回复</button>
    </div>
    <!-- 递归渲染子回复 -->
    <div v-if="comment.replies?.length" class="replies">
      <CommentItem
        v-for="reply in comment.replies"
        :key="reply.comment_id"
        :comment="reply"
        :post-id="postId"
        :depth="depth + 1"
        @reply="$emit('reply', $event)"
      />
    </div>
  </div>
</template>
```

---

## 7. 实时更新策略

### 7.1 轮询方案（简单实现）

```typescript
// PostDetailView.vue
const POLLING_INTERVAL = 30000 // 30 秒

const startPolling = () => {
  const interval = setInterval(async () => {
    const newComments = await fetchPostComments(props.postId)
    if (newComments.floors.length !== comments.value.length) {
      comments.value = newComments.floors
    }
  }, POLLING_INTERVAL)

  onUnmounted(() => clearInterval(interval))
}
```

### 7.2 高级方案：WebSocket（可选扩展）

如果需要真正的实时更新，可以考虑：

1. 后端添加 WebSocket 支持（FastAPI + websockets）
2. 当有新评论时，通过 WebSocket 广播
3. 前端监听 WebSocket 消息，动态插入新评论

---

## 8. 数据库迁移

```bash
# 生成迁移文件
alembic revision --autogenerate -m "add forum tables"

# 执行迁移
alembic upgrade head
```

---

## 9. 性能优化要点

1. **浏览量 Write-Back**: 避免频繁的 MySQL 写入，减少行锁竞争
2. **评论查询优化**: 使用 `selectinload` 预加载作者信息，避免 N+1 问题
3. **缓存策略**:
   - 帖子列表缓存 60 秒
   - 评论列表缓存 30 秒（实时更新需求）
   - 浏览量从 Redis 读取，不依赖缓存
4. **索引设计**:
   - `post_id + created_at`: 评论时间线查询
   - `root_id`: 快速查询某楼层的所有子回复
   - `parent_id`: 验证父评论存在性

---

## 10. 实现步骤总结

| 步骤 | 任务 | 文件 |
|------|------|------|
| 1 | 创建数据库模型 | `backend/models/models.py` |
| 2 | 生成并执行迁移 | `alembic` |
| 3 | 实现 Write-Back 工具 | `backend/forum_utils.py` |
| 4 | 实现定时任务 | `backend/forum_write_back_task.py` |
| 5 | 添加 Pydantic Schema | `backend/schemas.py` |
| 6 | 实现后端 API 端点 | `backend/app.py` |
| 7 | 更新前端类型定义 | `cycling-forum/src/interfaces/types.ts` |
| 8 | 扩展 API 服务 | `cycling-forum/src/services/ApiServices.ts` |
| 9 | 创建 Vue 组件 | `cycling-forum/src/views/`, `cycling-forum/src/components/forum/` |
| 10 | 更新路由配置 | `cycling-forum/src/router/index.ts` |
| 11 | 集成定时任务到生命周期 | `backend/app.py` (lifespan) |
