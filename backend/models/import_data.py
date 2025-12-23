import csv
import re
import time
from decimal import Decimal
from pathlib import Path

# ??????????
from .models import Base, Race, Edition, Team, Rider, Stage, StageResult
from .database import engine, SessionLocal

# --- 导入配置 (适配脚本运行) ---
DEFAULT_RACE_NAME = 'Tour de France'
# 修改 CSV 文件路径为包含 1903-2025 数据的完整文件
CSV_FILENAME = Path(__file__).resolve().parent / 'tour_de_france_ite_1903-2025.csv'
BATCH_SIZE = 5000

# --- 辅助函数 (保持不变) ---
def parse_stage_info(stage_full_desc):
    try:
        parts = stage_full_desc.split(' : ', 1)
        stage_desc = parts[0].strip()
        stage_route = parts[1].strip() if len(parts) > 1 else ''
        stage_number = Decimal('0.0')
        if 'Prologue' in stage_desc:
            stage_number = Decimal('0.0')
        else:
            match = re.search(r'[\d\.]+$', stage_desc)
            if match:
                stage_number = Decimal(match.group(0))
        return stage_number, stage_route
    except Exception as e:
        # print(f"[警告] 解析赛段失败: '{stage_full_desc}'. 错误: {e}")
        return None, None

def parse_time_to_seconds(time_str):
    hours, minutes, seconds = 0, 0, 0
    h_match = re.search(r'(\d+)h', time_str)
    m_match = re.search(r"(\d+)'", time_str)
    s_match = re.search(r"(\d+)''", time_str)
    if h_match: hours = int(h_match.group(1))
    if m_match: minutes = int(m_match.group(1))
    if s_match: seconds = int(s_match.group(1))
    return (hours * 3600) + (minutes * 60) + seconds

# --- 主导入函数 (修改逻辑) ---
def run_import():
    start_time = time.time()
    
    # 创建会话
    session = SessionLocal()
    
    try:
        print("开始导入 1903-1999 年的数据 (断点续传模式)...")
        
        # === 0. 清理 1903-1999 年的旧数据 (防止重跑时重复) ===
        # print("正在清理 2000 年以前的旧数据 (如果有)...")
        # editions_to_delete = session.query(Edition).filter(Edition.year < 2000).all()
        # if editions_to_delete:
        #     print(f"发现 {len(editions_to_delete)} 届旧赛事数据，正在删除...")
        #     for e in editions_to_delete:
        #         session.delete(e)
        #     session.commit()
        #     print("清理完成。")
        
        # === 断点续传清理: 删除 1985 年的数据 (因为上次可能中断在这里) ===
        print("正在清理 1985 年的数据 (断点续传)...")
        editions_1985 = session.query(Edition).filter(Edition.year == 1985).all()
        for e in editions_1985:
            session.delete(e)
        session.commit()

        # 1. 获取或创建赛事
        race = session.query(Race).filter_by(race_name=DEFAULT_RACE_NAME).first()
        if not race:
            print(f"创建赛事: {DEFAULT_RACE_NAME}")
            race = Race(race_name=DEFAULT_RACE_NAME)
            session.add(race)
            session.commit()

        # 2. 预加载现有数据到内存缓存，避免重复查询和唯一键冲突
        print("正在加载现有车手和车队数据...")
        # 使用字典映射：name.upper() -> object (解决大小写不一致导致的重复插入问题)
        existing_riders = {r.rider_name.upper(): r for r in session.query(Rider).all()}
        existing_teams = {t.team_name.upper(): t for t in session.query(Team).all()}
        
        # Editions 和 Stages 
        editions_cache = {e.year: e for e in session.query(Edition).filter_by(race_id=race.race_id).all()}
        
        # Stages 缓存 key: (year, stage_number)
        # 既然我们已经清理了 < 2000 的数据，这里只需要加载 >= 2000 的 stage (如果有重叠逻辑的话)
        # 但为了简单，我们只在运行时维护 cache，因为我们确信 < 2000 是空的。
        stages_cache = {} 
        
        riders_cache = existing_riders
        teams_cache = existing_teams
        
        print(f"已加载 {len(riders_cache)} 位车手, {len(teams_cache)} 支车队, {len(editions_cache)} 届赛事。")
        print(f"读取 CSV 文件: {CSV_FILENAME} ...")
        
        count = 0
        imported_count = 0
        skipped_count = 0
        
        if not CSV_FILENAME.exists():
            print(f"错误: 文件 {CSV_FILENAME} 不存在")
            return

        with open(CSV_FILENAME, mode='r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            
            # 读取并跳过标题行（如果有）
            # 简单的做法是尝试解析第一行，如果失败则认为是标题
            
            for row in reader:
                count += 1
                try:
                    if len(row) < 6:
                        continue
                    year_str, stage_full_desc, rank_str, rider_name, team_name, time_str = row
                    
                    # 尝试解析年份，如果失败说明是标题行
                    try:
                        year = int(year_str)
                    except ValueError:
                        continue

                    # === 关键过滤：只导入 2000 年以前的数据 ===
                    # 断点续传：只导入 <= 1985 的数据 (1999-1986 已导入)
                    if year > 1985:
                        skipped_count += 1
                        continue

                    rank = int(rank_str)
                    rider_name = rider_name.strip().upper()
                    team_name = team_name.strip().upper()
                    
                    if not rider_name or not team_name:
                        continue
                        
                    stage_number, stage_route = parse_stage_info(stage_full_desc)
                    time_in_seconds = parse_time_to_seconds(time_str)
                    
                    if stage_number is None:
                        continue
                        
                except Exception as e:
                    # print(f"跳过行 {count}: {e}")
                    continue

                # Get-or-Create Edition
                edition = editions_cache.get(year)
                if not edition:
                    edition = Edition(race=race, year=year)
                    session.add(edition)
                    editions_cache[year] = edition
                    # 新创建的 edition 需要 flush 才能有 ID (如果后续依赖 ID)
                    # 但这里 SQLAlchemy 的对象引用关系会自动处理
                
                # Get-or-Create Rider
                rider = riders_cache.get(rider_name)
                if not rider:
                    rider = Rider(rider_name=rider_name)
                    session.add(rider)
                    riders_cache[rider_name] = rider
                    
                # Get-or-Create Team
                team = teams_cache.get(team_name)
                if not team:
                    team = Team(team_name=team_name)
                    session.add(team)
                    teams_cache[team_name] = team
                    
                # Get-or-Create Stage
                # 注意：这里需要确保 edition 已经关联
                # 我们可以用一个复合键来缓存 stage: (year, stage_number)
                stage_key = (year, stage_number)
                stage = stages_cache.get(stage_key)
                
                # 如果缓存没找到，可能数据库里有（虽然我们假设没有），或者需要新建
                if not stage:
                    # 检查 session.new 或者数据库 (为了性能，这里主要依赖缓存，假设是新数据)
                    # 如果是追加模式，最好不要假设。
                    # 但由于我们按年份过滤，且 < 2000 是新数据，直接创建是安全的。
                    stage = Stage(edition=edition, stage_number=stage_number, stage_route=stage_route)
                    session.add(stage)
                    stages_cache[stage_key] = stage

                # Create Result
                result = StageResult(
                    stage=stage,
                    rider=rider,
                    team=team,
                    rank=rank,
                    time_in_seconds=time_in_seconds
                )
                session.add(result)
                imported_count += 1
                
                if imported_count % BATCH_SIZE == 0:
                    print(f"    ... 已处理 {imported_count} 条新记录 (跳过 {skipped_count} 条) ...")
                    session.commit() # 提交以防止内存过大，并持久化

        print("正在提交剩余数据...")
        session.commit()
        
    except Exception as e:
        print(f"发生错误: {e}。正在回滚...")
        session.rollback()
        import traceback
        traceback.print_exc()
    finally:
        session.close()
        end_time = time.time()
        print("\n--- 导入完成 ---")
        print(f"扫描 CSV 行数: {count}")
        print(f"成功导入记录: {imported_count}")
        print(f"跳过现有记录 (>=2000): {skipped_count}")
        print(f"耗时: {end_time - start_time:.2f} 秒")


# --- ?????? (??) ---
if __name__ == '__main__':
    # ??????????? Flask ??????
    run_import()