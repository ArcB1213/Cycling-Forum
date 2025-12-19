"""
SQLite 到 MySQL 数据迁移脚本
"""
import sqlite3
import sys
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 导入数据库模型
from models.database import engine as mysql_engine, SessionLocal
from models.models import Base, Race, Edition, Team, Rider, Stage, StageResult
from sqlalchemy import text

def create_mysql_database():
    """创建 MySQL 数据库（如果不存在）"""
    import pymysql
    
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_PORT = int(os.getenv('MYSQL_PORT', '3306'))
    MYSQL_USER = os.getenv('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
    MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'cycling_stats')
    
    try:
        # 连接到 MySQL（不指定数据库）
        connection = pymysql.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD
        )
        cursor = connection.cursor()
        
        # 创建数据库
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {MYSQL_DATABASE} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        print(f"✓ MySQL 数据库 '{MYSQL_DATABASE}' 已创建/已存在")
        
        cursor.close()
        connection.close()
        return True
    except Exception as e:
        print(f"✗ 创建 MySQL 数据库失败: {e}")
        print("\n请确保：")
        print("1. MySQL 服务已启动")
        print("2. .env 文件中的 MySQL 配置正确")
        print("3. MySQL 用户有创建数据库的权限")
        return False

def create_tables():
    """创建 MySQL 表结构"""
    try:
        print("\n创建 MySQL 表结构...")
        Base.metadata.create_all(bind=mysql_engine)
        print("✓ MySQL 表结构创建成功")
        return True
    except Exception as e:
        print(f"✗ 创建表结构失败: {e}")
        return False

def migrate_data():
    """迁移 SQLite 数据到 MySQL"""
    # SQLite 数据库路径
    basedir = os.path.abspath(os.path.dirname(__file__))
    sqlite_path = os.path.join(basedir, 'cycling_stats.db')
    
    if not os.path.exists(sqlite_path):
        print(f"✗ SQLite 数据库不存在: {sqlite_path}")
        return False
    
    print(f"\n开始从 SQLite 迁移数据...")
    print(f"源数据库: {sqlite_path}")
    
    # 连接 SQLite
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    
    # 连接 MySQL
    mysql_session = SessionLocal()
    
    try:
        # 检查表是否存在数据
        existing_races = mysql_session.execute(text("SELECT COUNT(*) FROM races")).scalar()
        existing_teams = mysql_session.execute(text("SELECT COUNT(*) FROM teams")).scalar()
        
        if existing_races > 0 or existing_teams > 0:
            print(f"\n⚠ 警告: MySQL 数据库中已有数据")
            print(f"   Races: {existing_races} 条")
            print(f"   Teams: {existing_teams} 条")
            print("\n选择操作:")
            print("1. 清空并重新导入（推荐）")
            print("2. 跳过重复数据继续导入")
            print("3. 取消操作")
            
            choice = input("\n请输入选项 (1/2/3): ").strip()
            
            if choice == '1':
                # 清空表（按依赖关系倒序删除）
                print("\n清空现有数据...")
                mysql_session.execute(text("SET FOREIGN_KEY_CHECKS=0"))
                mysql_session.execute(text("TRUNCATE TABLE stage_results"))
                mysql_session.execute(text("TRUNCATE TABLE stages"))
                mysql_session.execute(text("TRUNCATE TABLE editions"))
                mysql_session.execute(text("TRUNCATE TABLE races"))
                mysql_session.execute(text("TRUNCATE TABLE riders"))
                mysql_session.execute(text("TRUNCATE TABLE teams"))
                mysql_session.execute(text("SET FOREIGN_KEY_CHECKS=1"))
                mysql_session.commit()
                print("✓ 已清空现有数据")
            elif choice == '2':
                print("\n将跳过重复数据继续导入...")
            else:
                print("取消迁移")
                return False
        
        # 1. 迁移 races 表
        print("\n[1/6] 迁移 races 表...")
        cursor = sqlite_conn.execute("SELECT * FROM races")
        races_data = [dict(row) for row in cursor.fetchall()]
        if races_data:
            mysql_session.bulk_insert_mappings(Race, races_data)
            mysql_session.commit()
            print(f"✓ 已迁移 {len(races_data)} 条赛事记录")
        
        # 2. 迁移 teams 表
        print("\n[2/6] 迁移 teams 表...")
        cursor = sqlite_conn.execute("SELECT * FROM teams ORDER BY team_id")
        teams_data = [dict(row) for row in cursor.fetchall()]
        team_id_mapping = {}  # SQLite ID -> MySQL ID 映射
        
        if teams_data:
            inserted_count = 0
            skipped_count = 0
            for team in teams_data:
                try:
                    result = mysql_session.execute(
                        text("INSERT INTO teams (team_id, team_name) VALUES (:team_id, :team_name)"),
                        team
                    )
                    mysql_session.commit()
                    team_id_mapping[team['team_id']] = team['team_id']
                    inserted_count += 1
                except Exception as e:
                    if '1062' in str(e):  # 重复键错误，查找已存在的 ID
                        existing = mysql_session.execute(
                            text("SELECT team_id FROM teams WHERE team_name = :team_name"),
                            {'team_name': team['team_name']}
                        ).fetchone()
                        if existing:
                            team_id_mapping[team['team_id']] = existing[0]
                        skipped_count += 1
                    else:
                        raise
            print(f"✓ 已迁移 {inserted_count} 条车队记录 (跳过 {skipped_count} 条重复)")
        
        # 3. 迁移 riders 表
        print("\n[3/6] 迁移 riders 表...")
        cursor = sqlite_conn.execute("SELECT * FROM riders ORDER BY rider_id")
        riders_data = [dict(row) for row in cursor.fetchall()]
        rider_id_mapping = {}  # SQLite ID -> MySQL ID 映射
        
        if riders_data:
            inserted_count = 0
            skipped_count = 0
            for rider in riders_data:
                try:
                    mysql_session.execute(
                        text("INSERT INTO riders (rider_id, rider_name) VALUES (:rider_id, :rider_name)"),
                        rider
                    )
                    mysql_session.commit()
                    rider_id_mapping[rider['rider_id']] = rider['rider_id']
                    inserted_count += 1
                except Exception as e:
                    if '1062' in str(e):  # 重复键错误
                        existing = mysql_session.execute(
                            text("SELECT rider_id FROM riders WHERE rider_name = :rider_name"),
                            {'rider_name': rider['rider_name']}
                        ).fetchone()
                        if existing:
                            rider_id_mapping[rider['rider_id']] = existing[0]
                        skipped_count += 1
                    else:
                        raise
            print(f"✓ 已迁移 {inserted_count} 条车手记录 (跳过 {skipped_count} 条重复)")
        
        # 4. 迁移 editions 表
        print("\n[4/6] 迁移 editions 表...")
        cursor = sqlite_conn.execute("SELECT * FROM editions")
        editions_data = [dict(row) for row in cursor.fetchall()]
        if editions_data:
            mysql_session.bulk_insert_mappings(Edition, editions_data)
            mysql_session.commit()
            print(f"✓ 已迁移 {len(editions_data)} 条赛事届数记录")
        
        # 5. 迁移 stages 表
        print("\n[5/6] 迁移 stages 表...")
        cursor = sqlite_conn.execute("SELECT * FROM stages")
        stages_data = [dict(row) for row in cursor.fetchall()]
        if stages_data:
            mysql_session.bulk_insert_mappings(Stage, stages_data)
            mysql_session.commit()
            print(f"✓ 已迁移 {len(stages_data)} 条赛段记录")
        
        # 6. 迁移 stage_results 表（分批处理，使用 ID 映射）
        print("\n[6/6] 迁移 stage_results 表（大表，分批处理）...")
        cursor = sqlite_conn.execute("SELECT COUNT(*) FROM stage_results")
        total_results = cursor.fetchone()[0]
        print(f"共有 {total_results} 条成绩记录需要迁移")
        
        # 获取所有有效的 team_id 和 rider_id
        valid_teams = set(mysql_session.execute(text("SELECT team_id FROM teams")).scalars())
        valid_riders = set(mysql_session.execute(text("SELECT rider_id FROM riders")).scalars())
        
        batch_size = 5000
        offset = 0
        migrated_count = 0
        skipped_count = 0
        
        while True:
            cursor = sqlite_conn.execute(
                f"SELECT * FROM stage_results LIMIT {batch_size} OFFSET {offset}"
            )
            batch_data = [dict(row) for row in cursor.fetchall()]
            
            if not batch_data:
                break
            
            # 过滤出有效的记录（team_id 和 rider_id 存在）
            valid_batch = []
            for record in batch_data:
                # 使用映射后的 ID
                mapped_team_id = team_id_mapping.get(record['team_id'], record['team_id'])
                mapped_rider_id = rider_id_mapping.get(record['rider_id'], record['rider_id'])
                
                if mapped_team_id in valid_teams and mapped_rider_id in valid_riders:
                    record['team_id'] = mapped_team_id
                    record['rider_id'] = mapped_rider_id
                    valid_batch.append(record)
                else:
                    skipped_count += 1
            
            if valid_batch:
                mysql_session.bulk_insert_mappings(StageResult, valid_batch)
                mysql_session.commit()
            
            migrated_count += len(valid_batch)
            offset += batch_size
            progress = (offset / total_results) * 100
            print(f"  进度: {offset}/{total_results} ({progress:.1f}%) - 已导入: {migrated_count}, 跳过: {skipped_count}")
        
        print(f"✓ 已迁移 {migrated_count} 条成绩记录 (跳过 {skipped_count} 条无效记录)")
        
        print("\n" + "="*60)
        print("✓✓✓ 数据迁移完成！✓✓✓")
        print("="*60)
        
        # 验证迁移结果
        print("\n验证迁移结果:")
        print(f"  Races: {mysql_session.query(Race).count()}")
        print(f"  Teams: {mysql_session.query(Team).count()}")
        print(f"  Riders: {mysql_session.query(Rider).count()}")
        print(f"  Editions: {mysql_session.query(Edition).count()}")
        print(f"  Stages: {mysql_session.query(Stage).count()}")
        print(f"  Stage Results: {mysql_session.query(StageResult).count()}")
        
        return True
        
    except Exception as e:
        mysql_session.rollback()
        print(f"\n✗ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        sqlite_conn.close()
        mysql_session.close()

def main():
    """主函数"""
    print("="*60)
    print("SQLite → MySQL 数据迁移工具")
    print("="*60)
    
    # 步骤 1: 创建数据库
    if not create_mysql_database():
        sys.exit(1)
    
    # 步骤 2: 创建表结构
    if not create_tables():
        sys.exit(1)
    
    # 步骤 3: 迁移数据
    if not migrate_data():
        sys.exit(1)
    
    print("\n迁移完成！你现在可以：")
    print("1. 启动 FastAPI 服务: cd backend && uvicorn app:app --reload")
    print("2. 访问 API 文档: http://localhost:8000/docs")
    print("3. 测试缓存统计: http://localhost:8000/api/cache/stats")

if __name__ == "__main__":
    main()
