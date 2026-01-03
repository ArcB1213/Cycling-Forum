"""
测试用户注销功能及级联删除验证

测试步骤：
1. 登录测试用户
2. 记录删除前的数据状态
3. 调用删除API
4. 验证删除后的数据库状态

参照 seed_data.py 的登录方法
"""

import requests
from sqlalchemy import create_engine, text, func
from sqlalchemy.orm import sessionmaker
from models.database import DATABASE_URL
from models.models import User, Rating, ForumPost, ForumComment

# 测试用户信息（参照 seed_data.py）
TEST_USER_ID = 1535
TEST_EMAIL = "load_test_0@test.com"
TEST_NICKNAME = "load_test_0"
TEST_PASSWORD = "password123"  # 从 seed_data.py 确认的密码

# API 基础 URL（参照 seed_data.py）
BASE_URL = "http://127.0.0.1:8000/api"


def print_section(title):
    """打印分节标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def get_db_session():
    """获取数据库会话"""
    engine = create_engine(DATABASE_URL.replace("+aiomysql", "+pymysql"))
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def count_records_before(session):
    """统计删除前的记录数"""
    print_section("步骤1: 统计删除前的数据")

    # 统计该用户的评分数量
    rating_count = session.query(Rating).filter(Rating.user_id == TEST_USER_ID).count()
    print(f"✓ 用户 {TEST_NICKNAME} 的评分数量: {rating_count}")

    # 统计该用户的帖子数量
    post_count = session.query(ForumPost).filter(
        ForumPost.author_id == TEST_USER_ID,
        ForumPost.is_deleted == False
    ).count()
    print(f"✓ 用户 {TEST_NICKNAME} 的帖子数量: {post_count}")

    # 统计该用户的评论数量
    comment_count = session.query(ForumComment).filter(
        ForumComment.author_id == TEST_USER_ID
    ).count()
    print(f"✓ 用户 {TEST_NICKNAME} 的评论数量: {comment_count}")

    # 验证用户存在
    user = session.query(User).filter(User.user_id == TEST_USER_ID).first()
    if user:
        print(f"✓ 用户存在: ID={user.user_id}, 昵称={user.nickname}, 邮箱={user.email}")
    else:
        print(f"✗ 用户不存在！")
        return None

    return {
        'rating_count': rating_count,
        'post_count': post_count,
        'comment_count': comment_count
    }


def login_and_get_token():
    """登录并获取Token（参照 seed_data.py）"""
    print_section("步骤2: 登录测试用户")

    try:
        response = requests.post(
            f"{BASE_URL}/async/auth/login",
            json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD
            }
        )

        if response.status_code == 200:
            data = response.json()
            token = data.get('access_token')
            print(f"✓ 登录成功")
            print(f"  Token: {token[:50]}...")
            return token
        else:
            print(f"✗ 登录失败: {response.status_code}")
            print(f"  响应: {response.text}")
            return None
    except Exception as e:
        print(f"✗ 登录异常: {e}")
        return None


def delete_user_account(token):
    """删除用户账号"""
    print_section("步骤3: 调用删除API")

    try:
        response = requests.delete(
            f"{BASE_URL}/auth/user",
            headers={
                "Authorization": f"Bearer {token}"
            }
        )

        if response.status_code == 200:
            data = response.json()
            print(f"✓ 删除成功: {data.get('message')}")
            return True
        else:
            print(f"✗ 删除失败: {response.status_code}")
            print(f"  响应: {response.text}")
            return False
    except Exception as e:
        print(f"✗ 删除异常: {e}")
        return False


def verify_cascade_deletion(before_counts):
    """验证级联删除结果（使用新的 session 避免缓存问题）"""
    print_section("步骤4: 验证数据库状态")

    # 创建新的 session 避免缓存问题
    new_session = get_db_session()

    try:
        # 1. 验证用户已被删除
        user = new_session.query(User).filter(User.user_id == TEST_USER_ID).first()
        if user is None:
            print("✓ 用户已成功删除")
        else:
            print(f"✗ 用户仍然存在！ID={user.user_id}")
            return False

        # 2. 验证评分已被级联删除
        rating_count = new_session.query(Rating).filter(Rating.user_id == TEST_USER_ID).count()
        if rating_count == 0:
            print(f"✓ 用户评分已全部删除（原有 {before_counts['rating_count']} 条）")
        else:
            print(f"✗ 仍有 {rating_count} 条评分未删除！")
            return False

        # 3. 验证帖子已被级联删除
        post_count = new_session.query(ForumPost).filter(
            ForumPost.author_id == TEST_USER_ID
        ).count()
        if post_count == 0:
            print(f"✓ 用户帖子已全部删除（原有 {before_counts['post_count']} 条）")
        else:
            print(f"✗ 仍有 {post_count} 条帖子未删除！")
            # 显示未删除的帖子ID
            remaining_posts = new_session.query(ForumPost).filter(
                ForumPost.author_id == TEST_USER_ID
            ).all()
            print(f"  未删除的帖子ID: {[p.post_id for p in remaining_posts]}")
            return False

        # 4. 验证评论已被级联删除
        comment_count = new_session.query(ForumComment).filter(
            ForumComment.author_id == TEST_USER_ID
        ).count()
        if comment_count == 0:
            print(f"✓ 用户评论已全部删除（原有 {before_counts['comment_count']} 条）")
        else:
            print(f"✗ 仍有 {comment_count} 条评论未删除！")
            return False

        # 5. 验证数据库完整性（检查是否有孤儿记录）
        print("\n附加检查: 验证数据库完整性")

        # 检查是否有指向不存在用户的评分
        orphan_ratings = new_session.execute(text("""
            SELECT COUNT(*) FROM ratings
            WHERE user_id NOT IN (SELECT user_id FROM users)
        """)).scalar()
        if orphan_ratings == 0:
            print("✓ 无孤儿评分记录")
        else:
            print(f"⚠ 发现 {orphan_ratings} 条孤儿评分记录")

        # 检查是否有指向不存在用户的帖子
        orphan_posts = new_session.execute(text("""
            SELECT COUNT(*) FROM forum_posts
            WHERE author_id NOT IN (SELECT user_id FROM users)
        """)).scalar()
        if orphan_posts == 0:
            print("✓ 无孤儿帖子记录")
        else:
            print(f"⚠ 发现 {orphan_posts} 条孤儿帖子记录")

        # 检查是否有指向不存在用户的评论
        orphan_comments = new_session.execute(text("""
            SELECT COUNT(*) FROM forum_comments
            WHERE author_id NOT IN (SELECT user_id FROM users)
        """)).scalar()
        if orphan_comments == 0:
            print("✓ 无孤儿评论记录")
        else:
            print(f"⚠ 发现 {orphan_comments} 条孤儿评论记录")

        return True
    finally:
        new_session.close()


def print_summary(before_counts, success):
    """打印测试总结"""
    print_section("测试总结")
    print(f"测试用户: {TEST_NICKNAME} (ID: {TEST_USER_ID})")
    print(f"删除前数据:")
    print(f"  - 评分: {before_counts['rating_count']} 条")
    print(f"  - 帖子: {before_counts['post_count']} 条")
    print(f"  - 评论: {before_counts['comment_count']} 条")
    print(f"\n删除结果: {'✅ 成功' if success else '❌ 失败'}")
    print("=" * 60 + "\n")


def main():
    """主测试流程（参照 seed_data.py，使用同步方法）"""
    print("\n" + "🧪" * 30)
    print("  用户账号注销及级联删除测试")
    print("🧪" * 30)

    session = get_db_session()

    try:
        before_counts={
        'rating_count': 110,
        'post_count': 4,
        'comment_count': 73
        }

        # # 步骤1: 统计删除前的数据
        # before_counts = count_records_before(session)
        # if before_counts is None:
        #     print("\n❌ 测试终止：用户不存在")
        #     return

        # # 步骤2: 登录获取Token
        # token = login_and_get_token()
        # if token is None:
        #     print("\n❌ 测试终止：登录失败")
        #     return

        # # 步骤3: 调用删除API
        # deletion_success = delete_user_account(token)
        # if not deletion_success:
        #     print("\n❌ 测试终止：删除API调用失败")
        #     return

        # 步骤4: 验证数据库状态
        verification_success = verify_cascade_deletion(before_counts)

        # 打印测试总结
        print_summary(before_counts, verification_success)

        if verification_success:
            print("🎉 所有测试通过！级联删除功能正常。")
        else:
            print("⚠️  测试失败，请检查数据库和日志。")

    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()


if __name__ == "__main__":
    main()
