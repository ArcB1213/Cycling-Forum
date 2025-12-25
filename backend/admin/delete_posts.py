#!/usr/bin/env python
"""
安全删除帖子的脚本

删除方式：
1. 按时间范围删除
2. 按测试用户删除
3. 按帖子标题模式删除
4. 交互式选择删除

"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# 添加父目录到 sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_, func
from models.database import AsyncSessionLocal
from models.models import ForumPost, ForumComment, User


async def show_test_posts():
    """显示可能是测试帖子的帖子列表"""
    print("\n📊 扫描测试帖子...")

    async with AsyncSessionLocal() as db:
        # 查找最近创建的帖子（可能是测试帖子）
        cutoff_time = datetime.now() - timedelta(hours=24)
        result = await db.execute(
            select(ForumPost, User.nickname)
            .join(User, ForumPost.author_id == User.user_id)
            .filter(
                ForumPost.is_deleted == False,
                ForumPost.created_at >= cutoff_time
            )
            .order_by(ForumPost.created_at.desc())
        )
        posts = result.all()

        if not posts:
            print("  ℹ️  没有找到最近24小时内创建的帖子")
            return []

        print(f"\n  找到 {len(posts)} 个最近创建的帖子：")
        print(f"\n{'ID':<8} {'标题':<40} {'作者':<20} {'创建时间':<20}")
        print("-" * 90)

        post_list = []
        for post, author_nickname in posts:
            print(f"{post.post_id:<8} {post.title[:40]:<40} {author_nickname:<20} {post.created_at.strftime('%Y-%m-%d %H:%M'):<20}")
            post_list.append(post)

        return post_list


async def delete_posts_by_time(hours: int = 24):
    """按时间范围删除帖子"""
    print(f"\n🗑️ 删除最近 {hours} 小时内创建的帖子...")

    async with AsyncSessionLocal() as db:
        cutoff_time = datetime.now() - timedelta(hours=hours)

        # 查找要删除的帖子
        result = await db.execute(
            select(ForumPost)
            .filter(
                ForumPost.is_deleted == False,
                ForumPost.created_at >= cutoff_time
            )
        )
        posts_to_delete = result.scalars().all()

        if not posts_to_delete:
            print("  ℹ️  没有找到符合条件的帖子")
            return 0

        print(f"  找到 {len(posts_to_delete)} 个帖子准备删除")

        # 显示将要删除的帖子
        print("\n  将要删除的帖子：")
        for post in posts_to_delete[:10]:
            print(f"    - ID:{post.post_id} | {post.title[:50]}")
        if len(posts_to_delete) > 10:
            print(f"    ... 还有 {len(posts_to_delete) - 10} 个")

        # 软删除帖子和相关评论
        deleted_count = 0
        for post in posts_to_delete:
            # 软删除帖子
            await db.execute(
                update(ForumPost)
                .filter(ForumPost.post_id == post.post_id)
                .values(is_deleted=True)
            )

            # 软删除该帖子的所有评论
            await db.execute(
                update(ForumComment)
                .filter(ForumComment.post_id == post.post_id)
                .values(is_deleted=True)
            )

            deleted_count += 1

        await db.commit()
        print(f"\n  ✅ 已软删除 {deleted_count} 个帖子及其评论")
        return deleted_count


async def delete_posts_by_test_users():
    """按测试用户删除帖子"""
    print("\n🗑️ 删除测试用户创建的帖子...")

    async with AsyncSessionLocal() as db:
        # 查找测试用户
        test_emails = [f"load_test_{i}@test.com" for i in range(10)]
        result = await db.execute(
            select(User.user_id, User.email, User.nickname)
            .filter(User.email.in_(test_emails))
        )
        test_users = result.all()

        if not test_users:
            print("  ℹ️  没有找到测试用户")
            return 0

        print(f"  找到 {len(test_users)} 个测试用户：")
        for user_id, email, nickname in test_users:
            print(f"    - {nickname} ({email})")

        # 查找这些用户的帖子
        test_user_ids = [user[0] for user in test_users]
        result = await db.execute(
            select(ForumPost)
            .filter(
                ForumPost.author_id.in_(test_user_ids),
                ForumPost.is_deleted == False
            )
        )
        posts_to_delete = result.scalars().all()

        if not posts_to_delete:
            print("  ℹ️  测试用户没有创建帖子")
            return 0

        print(f"\n  找到 {len(posts_to_delete)} 个测试帖子准备删除")

        # 软删除帖子和评论
        deleted_count = 0
        for post in posts_to_delete:
            await db.execute(
                update(ForumPost)
                .filter(ForumPost.post_id == post.post_id)
                .values(is_deleted=True)
            )

            await db.execute(
                update(ForumComment)
                .filter(ForumComment.post_id == post.post_id)
                .values(is_deleted=True)
            )

            deleted_count += 1

        await db.commit()
        print(f"  ✅ 已软删除 {deleted_count} 个测试帖子")
        return deleted_count


async def delete_posts_by_title_pattern(pattern: str):
    """按标题模式删除帖子"""
    print(f"\n🗑️ 删除标题包含 '{pattern}' 的帖子...")

    async with AsyncSessionLocal() as db:
        # 查找匹配的帖子
        result = await db.execute(
            select(ForumPost)
            .filter(
                ForumPost.is_deleted == False,
                ForumPost.title.like(f"%{pattern}%")
            )
        )
        posts_to_delete = result.scalars().all()

        if not posts_to_delete:
            print(f"  ℹ️  没有找到标题包含 '{pattern}' 的帖子")
            return 0

        print(f"  找到 {len(posts_to_delete)} 个帖子：")
        for post in posts_to_delete:
            print(f"    - ID:{post.post_id} | {post.title}")

        # 软删除
        deleted_count = 0
        for post in posts_to_delete:
            await db.execute(
                update(ForumPost)
                .filter(ForumPost.post_id == post.post_id)
                .values(is_deleted=True)
            )

            await db.execute(
                update(ForumComment)
                .filter(ForumComment.post_id == post.post_id)
                .values(is_deleted=True)
            )

            deleted_count += 1

        await db.commit()
        print(f"  ✅ 已软删除 {deleted_count} 个帖子")
        return deleted_count


async def show_stats():
    """显示当前数据库统计"""
    print("\n📊 当前数据库统计:")

    async with AsyncSessionLocal() as db:
        # 总帖子数
        result = await db.execute(
            select(func.count(ForumPost.post_id))
            .filter(ForumPost.is_deleted == False)
        )
        total_posts = result.scalar_one()
        print(f"  - 活跃帖子数: {total_posts}")

        # 已删除帖子数
        result = await db.execute(
            select(func.count(ForumPost.post_id))
            .filter(ForumPost.is_deleted == True)
        )
        deleted_posts = result.scalar_one()
        print(f"  - 已删除帖子数: {deleted_posts}")

        # 总评论数
        result = await db.execute(
            select(func.count(ForumComment.comment_id))
            .filter(ForumComment.is_deleted == False)
        )
        total_comments = result.scalar_one()
        print(f"  - 活跃评论数: {total_comments}")

        # 已删除评论数
        result = await db.execute(
            select(func.count(ForumComment.comment_id))
            .filter(ForumComment.is_deleted == True)
        )
        deleted_comments = result.scalar_one()
        print(f"  - 已删除评论数: {deleted_comments}")


async def interactive_delete():
    """交互式删除"""
    print("\n🔍 交互式删除模式")

    # 显示测试帖子
    posts = await show_test_posts()
    if not posts:
        return

    print("\n请选择要删除的帖子ID（用空格或逗号分隔）：")
    print("提示: 输入 'all' 删除所有显示的帖子")
    print("      输入 'cancel' 取消操作")

    choice = input("\n您的选择: ").strip()

    if choice.lower() == 'cancel':
        print("  ℹ️  已取消操作")
        return 0

    if choice.lower() == 'all':
        post_ids = [post.post_id for post in posts]
    else:
        # 解析用户输入的ID
        try:
            post_ids = [int(x.strip()) for x in choice.replace(',', ' ').split() if x.strip()]
            # 验证ID是否在列表中
            valid_ids = {post.post_id for post in posts}
            post_ids = [pid for pid in post_ids if pid in valid_ids]
            if not post_ids:
                print("  ❌ 没有有效的帖子ID")
                return 0
        except ValueError:
            print("  ❌ 输入格式错误")
            return 0

    print(f"\n准备删除 {len(post_ids)} 个帖子...")

    async with AsyncSessionLocal() as db:
        deleted_count = 0
        for post_id in post_ids:
            await db.execute(
                update(ForumPost)
                .filter(ForumPost.post_id == post_id)
                .values(is_deleted=True)
            )

            await db.execute(
                update(ForumComment)
                .filter(ForumComment.post_id == post_id)
                .values(is_deleted=True)
            )

            deleted_count += 1

        await db.commit()
        print(f"  ✅ 已软删除 {deleted_count} 个帖子")

        return deleted_count


async def main():
    """主函数"""
    print("=" * 70)
    print("🗑️ 安全删除测试帖子工具")
    print("=" * 70)

    print("\n请选择删除方式：")
    print("1. 按时间范围删除（推荐）")
    print("2. 按测试用户删除")
    print("3. 按标题模式删除")
    print("4. 交互式选择删除")
    print("5. 查看数据库统计")
    print("0. 退出")

    choice = input("\n请输入选项 (0-5): ").strip()

    if choice == "1":
        print("\n⏰ 按时间范围删除")
        hours = input("请输入小时数（默认24）: ").strip()
        hours = int(hours) if hours else 24
        await delete_posts_by_time(hours)

    elif choice == "2":
        await delete_posts_by_test_users()

    elif choice == "3":
        pattern = input("\n请输入标题关键词: ").strip()
        if pattern:
            await delete_posts_by_title_pattern(pattern)
        else:
            print("  ❌ 标题关键词不能为空")

    elif choice == "4":
        await interactive_delete()

    elif choice == "5":
        await show_stats()

    elif choice == "0":
        print("\n👋 再见！")
        return

    else:
        print("\n❌ 无效的选项")

    # 显示删除后的统计
    await show_stats()

    print("\n" + "=" * 70)
    print("✅ 操作完成")
    print("=" * 70)


if __name__ == "__main__":
    try:
        # Windows平台设置
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

        # 运行主函数
        asyncio.run(main())

    except KeyboardInterrupt:
        print("\n⚠️ 用户中断")
    except Exception as e:
        print(f"❌ 程序异常: {e}")
        import traceback
        traceback.print_exc()
