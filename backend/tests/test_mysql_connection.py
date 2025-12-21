"""
测试 MySQL 连接配置
"""
import os
from dotenv import load_dotenv
import pymysql

# 加载环境变量
load_dotenv()

def test_mysql_connection():
    """测试 MySQL 连接"""
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_PORT = int(os.getenv('MYSQL_PORT', '3306'))
    MYSQL_USER = os.getenv('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
    
    print("="*60)
    print("测试 MySQL 连接")
    print("="*60)
    print(f"主机: {MYSQL_HOST}")
    print(f"端口: {MYSQL_PORT}")
    print(f"用户: {MYSQL_USER}")
    print(f"密码: {'*' * len(MYSQL_PASSWORD) if MYSQL_PASSWORD else '(空)'}")
    print()
    
    try:
        # 尝试连接
        connection = pymysql.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD
        )
        
        cursor = connection.cursor()
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()
        
        print("✓ MySQL 连接成功！")
        print(f"  MySQL 版本: {version[0]}")
        
        # 检查数据库是否存在
        MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'cycling_stats')
        cursor.execute("SHOW DATABASES")
        databases = [db[0] for db in cursor.fetchall()]
        
        if MYSQL_DATABASE in databases:
            print(f"  数据库 '{MYSQL_DATABASE}' 已存在")
        else:
            print(f"  数据库 '{MYSQL_DATABASE}' 不存在（迁移脚本会自动创建）")
        
        cursor.close()
        connection.close()
        
        print("\n下一步:")
        print("1. 如果你还没有配置 .env 文件，请先编辑 .env 设置 MySQL 密码")
        print("2. 运行迁移脚本: python backend/migrate_to_mysql.py")
        print("3. 启动服务: cd backend && uvicorn app:app --reload")
        
        return True
        
    except pymysql.err.OperationalError as e:
        print("✗ MySQL 连接失败！")
        print(f"  错误: {e}")
        print("\n可能的原因:")
        print("1. MySQL 服务未启动")
        print("   - Windows: 在服务中启动 MySQL")
        print("   - Linux: sudo systemctl start mysql")
        print("2. 用户名或密码错误（检查 .env 文件）")
        print("3. MySQL 端口不是 3306（检查 .env 文件）")
        print("4. 防火墙阻止连接")
        return False
    
    except Exception as e:
        print(f"✗ 发生错误: {e}")
        return False

if __name__ == "__main__":
    test_mysql_connection()
