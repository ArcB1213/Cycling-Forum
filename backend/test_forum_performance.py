"""
论坛性能测试脚本
测试评论查询优化效果
"""
import asyncio
import time
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.database import AsyncSessionLocal
from models.models import ForumPost, ForumComment
from sqlalchemy.orm import selectinload

async def test_comment_query_performance(post_id: int = 1):
    """测试评论查询性能"""
    async with AsyncSessionLocal() as db:
        print(f"\n🔍 测试帖子 {post_id} 的评论查询性能...")
        
        # 统计评论总数
        count_result = await db.execute(
            select(ForumComment).filter(
                ForumComment.post_id == post_id,
                ForumComment.is_deleted == False
            )
        )
        total_comments = len(count_result.scalars().all())
        print(f"📊 评论总数: {total_comments}")
        
        # 测试批量查询性能
        start_time = time.time()
        
        # 查询一级评论ID
        floor_ids_result = await db.execute(
            select(ForumComment.comment_id)
            .filter(
                ForumComment.post_id == post_id,
                ForumComment.parent_id.is_(None),
                ForumComment.is_deleted == False
            )
        )
        floor_ids = [row[0] for row in floor_ids_result.all()]
        
        # 批量查询所有评论
        all_comments_result = await db.execute(
            select(ForumComment)
            .options(selectinload(ForumComment.author))
            .filter(
                ForumComment.post_id == post_id,
                ForumComment.is_deleted == False,
                (ForumComment.comment_id.in_(floor_ids)) | (ForumComment.root_id.in_(floor_ids))
            )
        )
        all_comments = all_comments_result.scalars().all()
        
        end_time = time.time()
        query_time = (end_time - start_time) * 1000  # 转换为毫秒
        
        print(f"⏱️  批量查询耗时: {query_time:.2f}ms")
        print(f"📈 查询到 {len(all_comments)} 条评论")
        print(f"🚀 平均每条评论查询时间: {query_time/len(all_comments) if all_comments else 0:.3f}ms")
        
        # 在内存中构建树
        start_build = time.time()
        comment_map = {}
        for comment in all_comments:
            comment_dict = {
                'comment_id': comment.comment_id,
                'content': comment.content[:20] + '...' if len(comment.content) > 20 else comment.content,
                'replies': []
            }
            comment_map[comment.comment_id] = comment_dict
        
        floors_data = []
        for comment in all_comments:
            if comment.parent_id is None:
                floors_data.append(comment_map[comment.comment_id])
            else:
                parent = comment_map.get(comment.parent_id)
                if parent:
                    parent['replies'].append(comment_map[comment.comment_id])
        
        end_build = time.time()
        build_time = (end_build - start_build) * 1000
        
        print(f"🌲 构建树结构耗时: {build_time:.2f}ms")
        print(f"📦 构建了 {len(floors_data)} 个楼层")
        print(f"⚡ 总耗时: {query_time + build_time:.2f}ms\n")
        
        return {
            'total_comments': total_comments,
            'query_time_ms': query_time,
            'build_time_ms': build_time,
            'total_time_ms': query_time + build_time
        }

async def test_multiple_posts():
    """测试多个帖子的查询性能"""
    async with AsyncSessionLocal() as db:
        # 获取前5个帖子
        posts_result = await db.execute(
            select(ForumPost.post_id)
            .filter(ForumPost.is_deleted == False)
            .limit(5)
        )
        post_ids = [row[0] for row in posts_result.all()]
        
        print("="*60)
        print("🚀 论坛评论查询性能测试")
        print("="*60)
        
        results = []
        for post_id in post_ids:
            result = await test_comment_query_performance(post_id)
            results.append(result)
        
        # 统计平均性能
        if results:
            avg_query = sum(r['query_time_ms'] for r in results) / len(results)
            avg_total = sum(r['total_time_ms'] for r in results) / len(results)
            total_comments = sum(r['total_comments'] for r in results)
            
            print("="*60)
            print("📊 性能统计汇总")
            print("="*60)
            print(f"✅ 测试帖子数: {len(results)}")
            print(f"✅ 评论总数: {total_comments}")
            print(f"✅ 平均查询时间: {avg_query:.2f}ms")
            print(f"✅ 平均总处理时间: {avg_total:.2f}ms")
            print(f"\n💡 性能评估:")
            if avg_total < 100:
                print("   🟢 优秀 - 响应速度非常快")
            elif avg_total < 300:
                print("   🟡 良好 - 响应速度可接受")
            else:
                print("   🔴 需要优化 - 响应较慢")
            print("="*60)

if __name__ == "__main__":
    asyncio.run(test_multiple_posts())
