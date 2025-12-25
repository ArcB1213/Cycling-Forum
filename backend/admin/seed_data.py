#!/usr/bin/env python
"""
数据填充脚本 - 整合版
用于向数据库填充演示数据：帖子和评论、车手评分

功能：
1. 创建论坛帖子（20个）
2. 为帖子创建评论（每个帖子10条）
3. 创建车手评分（100个车手 × 20个评分）
4. 可选：删除现有评论并重置

使用方法：
    python seed_data.py                    # 正常填充数据
    python seed_data.py --reset-comments   # 删除现有评论后重新填充
    python seed_data.py --posts-only       # 只创建帖子和评论
    python seed_data.py --ratings-only     # 只创建评分

"""

import asyncio
import random
import sys
import os
import argparse
from datetime import datetime
from typing import List

# 添加父目录到 sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from models.database import AsyncSessionLocal
from models.models import Rider, ForumPost, ForumComment
import requests

# ============ 配置 ============
BASE_URL = "http://127.0.0.1:8000"
USER_TOKENS = {}

# 帖子标题
POST_TITLES = [
    "2024环法第18赛段个人感想",
    "聊聊公路车训练心得",
    "新手入门：如何选择第一辆公路车？",
    "Pogačar vs Vingegaard：谁是当今最佳？",
    "环法爬坡赛段策略分析",
    "自行车装备升级指南",
    "长途骑行补给技巧",
    "冬训计划制定建议",
    "如何提高FTP功率",
    "经典赛事回顾：1989年环法",
    "山地车vs公路车：如何选择？",
    "骑行安全注意事项",
    "自行车维修保养入门",
    "骑行装备推荐清单",
    "如何克服平台期训练",
    "环意赛段欣赏与战术分析",
    "女子自行车运动的崛起",
    "青少年自行车训练建议",
    "自行车赛事转播礼仪",
    "在户外骑行的乐趣分享"
]

# 帖子内容模板
POST_CONTENTS = [
    """
今天看了比赛，第18赛段的路线设计真的很棒，特别是最后的陡坡爬升。

{rider}在最后3公里的表现令人印象深刻，展现了强大的爬坡能力。他的配速策略很合理，没有过早发力，而在最关键的时刻展现了实力。

不过{rider2}的表现也值得肯定，虽然没能最终获胜，但他的追击很有看点。

大家觉得这场比赛怎么样？
    """,

    """
作为一个骑行爱好者，我想分享一下最近几个月的训练心得。

1. **基础训练的重要性**
   - 有氧耐力是基础
   - 每周至少3次有氧骑行
   - 渐进式增加训练量

2. **力量训练**
   - 每周2次力量房训练
   - 核心力量尤其重要
   - 不要忽视下肢力量

3. **营养补充**
   - 训练前后的碳水化合物补充
   - 蛋白质摄入要充足
   - 水分补充要及时

希望对大家有帮助！
    """,

    """
很多新手都会问：如何选择第一辆公路车？我来分享一下我的建议。

**预算考虑**
- 初学者：3000-5000元
- 进阶玩家：8000-15000元
- 专业级别：20000元以上

**车型选择**
1. **综合型**：适合大多数路况
2. **爬坡型**：轻量化，适合山路
3. **气动型**：适合平路和计时赛

**购买建议**
- 先确定主要用途
- 试骑很重要
- 不要过分追求配置
- 后期可以升级

我第一辆车花了4000元，用了3年才换车，性价比很高。
    """,

    """
Pogačar和Vingegaard的对决是当今自行车界最精彩的 rivalry。

**技术特点对比**
- Pogačar：技术全面，爬坡能力强，冲刺也有实力
- Vingegaard：力量型选手，耐力出色，心理素质稳定

**2024年表现**
- Pogačar：状态波动较大，但技术依然顶尖
- Vingegaard：稳定性强，大赛型选手

**未来展望**
两人都在不断进步，他们的对抗将推动自行车运动的发展。

大家更看好谁呢？
    """
]

# 简单的评论列表
COMMENTS = [
    "说得太好了！很有见地。",
    "学到了很多，感谢分享！",
    "从另一个角度思考这个问题很有启发。",
    "作为老手，我完全同意你的观点。",
    "这篇文章帮我解答了很多疑惑。",
    "期待看到更多这样的深度分析。",
    "数据很详实，分析很到位！",
    "这个观点很独特，让我重新思考了这个问题。",
    "实操性很强，马上就去试试！",
    "写得很用心，感谢作者的分享。",
    "感谢分享，学到了很多！",
    "很有用，收藏了！",
    "分析得很到位，学习了。",
    "说得对，确实如此！",
    "期待更多好文章！",
    "受益匪浅，谢谢！",
    "很有深度，值得细细品味。",
    "通俗易懂，讲得很清楚。",
    "非常有价值的内容。",
    "谢谢分享，很有帮助！"
]

# 评分评论
RATING_COMMENTS = [
    "实力派车手，{achievement}证明了能力。",
    "状态稳定，大赛型选手。",
    "年轻有为，未来可期！",
    "技术全面，有冠军相。",
    "经验丰富，值得信赖。",
    "这个赛季表现很出色。",
    "关键时刻总能站出来。",
    "团队协作做得很好。",
    "还有提升空间，但已经很强了。",
    "期待更多精彩表现！"
]

# ============ 工具函数 ============

async def login_users():
    """登录测试用户"""
    print("🔐 登录测试用户...")

    users = [
        {"email": "load_test_0@test.com", "password": "password123"},
        {"email": "load_test_1@test.com", "password": "password123"},
        {"email": "load_test_2@test.com", "password": "password123"},
        {"email": "load_test_3@test.com", "password": "password123"},
        {"email": "load_test_4@test.com", "password": "password123"},
    ]

    for user in users:
        try:
            response = requests.post(
                f"{BASE_URL}/api/async/auth/login",
                json={"email": user["email"], "password": user["password"]}
            )
            if response.status_code == 200:
                token = response.json()["access_token"]
                USER_TOKENS[user["email"]] = token
                print(f"  ✅ {user['email']} 登录成功")
            else:
                print(f"  ❌ {user['email']} 登录失败")
        except Exception as e:
            print(f"  ❌ {user['email']} 登录异常: {e}")

    return len(USER_TOKENS) > 0


async def reset_comments():
    """删除所有评论并重置帖子的comment_count"""
    print("\n🗑️ 删除所有评论并重置计数...")

    try:
        async with AsyncSessionLocal() as db:
            # 1. 先重置所有帖子的comment_count为0
            await db.execute(
                update(ForumPost).values(comment_count=0)
            )
            print("  ✓ 已重置所有帖子的comment_count")

            # 2. 物理删除所有评论
            await db.execute(delete(ForumComment))
            await db.commit()
            print("  ✓ 已删除所有评论")
            print("  ✅ 评论重置完成")
            return True

    except Exception as e:
        print(f"  ❌ 删除评论失败: {e}")
        return False


async def get_rider_names(db: AsyncSession) -> List[str]:
    """获取所有车手名字"""
    result = await db.execute(select(Rider.rider_name).limit(200))
    return [row[0] for row in result.fetchall()]


async def create_posts(db: AsyncSession, rider_names: List[str]) -> List[int]:
    """创建20个帖子"""
    print("\n📝 创建论坛帖子...")

    post_ids = []
    users = list(USER_TOKENS.keys())

    for i in range(20):
        try:
            # 选择用户
            user_email = random.choice(users)
            token = USER_TOKENS[user_email]

            # 准备帖子内容
            title = POST_TITLES[i]
            content = POST_CONTENTS[i % len(POST_CONTENTS)].format(
                rider=random.choice(rider_names),
                rider2=random.choice(rider_names)
            )

            # 创建帖子
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.post(
                f"{BASE_URL}/api/async/forum/posts",
                json={"title": title, "content": content},
                headers=headers
            )

            if response.status_code == 200:
                post_data = response.json()
                post_id = post_data["post_id"]
                post_ids.append(post_id)
                print(f"  ✅ 帖子 {i+1}/20 创建成功 (ID: {post_id})")

                # 创建评论
                await create_comments_for_post(post_id, user_email)
            else:
                print(f"  ❌ 帖子 {i+1} 创建失败: {response.status_code}")

        except Exception as e:
            print(f"  ❌ 帖子 {i+1} 创建异常: {e}")

    print(f"✅ 成功创建 {len(post_ids)} 个帖子")
    return post_ids


async def create_comments_for_post(post_id: int, author_email: str):
    """为帖子创建10条评论"""
    users = list(USER_TOKENS.keys())

    for i in range(10):
        try:
            # 随机选择评论作者
            comment_author = random.choice(users)
            token = USER_TOKENS[comment_author]

            # 选择评论内容
            content = random.choice(COMMENTS)

            # 发送请求创建评论
            headers = {"Authorization": f"Bearer {token}"}

            comment_data = {
                "content": content,
                "parent_id": None
            }

            response = requests.post(
                f"{BASE_URL}/api/async/forum/posts/{post_id}/comments",
                json=comment_data,
                headers=headers
            )

            if response.status_code == 200:
                pass  # 成功，不输出避免刷屏
            else:
                print(f"    ❌ 帖子 {post_id} 的评论 {i+1} 创建失败: {response.status_code}")

        except Exception as e:
            print(f"    ❌ 帖子 {post_id} 的评论 {i+1} 创建异常: {e}")


async def create_ratings(db: AsyncSession, rider_names: List[str]):
    """为100个车手创建评分"""
    print("\n⭐ 创建车手评分...")

    # 选择100个车手
    selected_riders = rider_names[:100]
    users = list(USER_TOKENS.keys())

    for i, rider_name in enumerate(selected_riders):
        try:
            # 获取车手ID
            result = await db.execute(select(Rider).filter(Rider.rider_name == rider_name))
            rider = result.scalar_one_or_none()
            if not rider:
                print(f"    ⚠️ 找不到车手: {rider_name}")
                continue

            rider_id = rider.rider_id

            # 为每个车手创建20个评分
            rating_users = random.sample(users, k=min(20, len(users)))

            for j, user_email in enumerate(rating_users):
                try:
                    token = USER_TOKENS[user_email]

                    # 生成评分数据
                    score = random.randint(1, 5)
                    comment = random.choice(RATING_COMMENTS).format(
                        achievement=random.choice([
                            "环法总冠军", "爬坡总冠军", "多个赛段冠军",
                            "世界冠军", "稳定发挥", "大赛型选手"
                        ])
                    )

                    # 创建评分
                    headers = {"Authorization": f"Bearer {token}"}
                    response = requests.post(
                        f"{BASE_URL}/api/riders/{rider_id}/ratings",
                        json={"rider_id": rider_id, "score": score, "comment": comment},
                        headers=headers
                    )

                    if response.status_code in (200, 409):  # 409表示评分已存在
                        pass  # 成功
                    else:
                        print(f"    ❌ 评分创建失败: {response.status_code}")

                except Exception as e:
                    pass  # 忽略个别错误

            if (i + 1) % 10 == 0:
                print(f"  🎯 进度: {i+1}/100 车手")

        except Exception as e:
            print(f"    ❌ 处理车手 {rider_name} 异常: {e}")

    print(f"✅ 车手评分创建完成")


# ============ 主函数 ============

async def main(reset_comments=False, posts_only=False, ratings_only=False):
    """主函数"""
    print("=" * 70)
    print("🚀 数据填充脚本 - 整合版")
    print("=" * 70)

    # 登录用户
    if not await login_users():
        print("❌ 用户登录失败，退出")
        return

    # 可选：重置评论
    if reset_comments:
        if not await reset_comments():
            print("❌ 评论重置失败，退出")
            return

    # 只创建评分
    if ratings_only:
        try:
            async with AsyncSessionLocal() as db:
                rider_names = await get_rider_names(db)
                if not rider_names:
                    print("❌ 没有找到车手数据")
                    return
                print(f"✅ 找到 {len(rider_names)} 个车手")
                await create_ratings(db, rider_names)
        except Exception as e:
            print(f"❌ 创建评分失败: {e}")
        return

    # 只创建帖子和评论
    if posts_only:
        try:
            async with AsyncSessionLocal() as db:
                rider_names = await get_rider_names(db)
                if not rider_names:
                    print("❌ 没有找到车手数据")
                    return
                print(f"✅ 找到 {len(rider_names)} 个车手")
                await create_posts(db, rider_names)
        except Exception as e:
            print(f"❌ 创建帖子失败: {e}")
        return

    # 默认：创建所有数据
    try:
        async with AsyncSessionLocal() as db:
            rider_names = await get_rider_names(db)

            if not rider_names:
                print("❌ 没有找到车手数据，请先导入自行车数据")
                return

            print(f"✅ 找到 {len(rider_names)} 个车手")

            # 创建帖子和评论
            await create_posts(db, rider_names)

            # 创建评分
            await create_ratings(db, rider_names)

    except Exception as e:
        print(f"❌ 数据填充失败: {e}")
        import traceback
        traceback.print_exc()
        return

    print("\n" + "=" * 70)
    print("🎉 数据填充完成！")
    print("=" * 70)


if __name__ == "__main__":
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='数据填充脚本')
    parser.add_argument('--reset-comments', action='store_true',
                        help='删除现有评论并重置')
    parser.add_argument('--posts-only', action='store_true',
                        help='只创建帖子和评论')
    parser.add_argument('--ratings-only', action='store_true',
                        help='只创建车手评分')

    args = parser.parse_args()

    try:
        # Windows平台设置
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

        # 运行主函数
        asyncio.run(main(
            reset_comments=args.reset_comments,
            posts_only=args.posts_only,
            ratings_only=args.ratings_only
        ))

    except KeyboardInterrupt:
        print("\n⚠️ 用户中断")
    except Exception as e:
        print(f"❌ 程序异常: {e}")
        import traceback
        traceback.print_exc()
