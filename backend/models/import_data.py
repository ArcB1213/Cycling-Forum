import csv
import re
import time
from decimal import Decimal
from pathlib import Path

# 导入 create_app 函数，db 实例，以及所有模型
from app import create_app
from .extensions import db
from .models import Race, Edition, Team, Rider, Stage, StageResult

# --- 全局配置 (保持不变) ---
DEFAULT_RACE_NAME = 'Tour de France'
# 使 CSV 路径相对于当前文件目录，避免用工作目录导致找不到文件
CSV_FILENAME = Path(__file__).resolve().parent / 'ite_2000-2025.csv'
BATCH_SIZE = 5000

# --- 辅助解析函数 (保持不变) ---
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
        print(f"[解析错误] 无法解析赛段描述: '{stage_full_desc}'. 错误: {e}")
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

# --- 主导入函数 (保持不变) ---
def run_import():
    start_time = time.time()
    
    print("正在清空并重建数据库表...")
    db.drop_all()
    db.create_all()

    race = Race.query.filter_by(race_name=DEFAULT_RACE_NAME).first()
    if not race:
        print(f"创建新赛事: {DEFAULT_RACE_NAME}")
        race = Race(race_name=DEFAULT_RACE_NAME) # 已移除 country
        db.session.add(race)
        db.session.commit()

    editions_cache = {}
    teams_cache = {}
    riders_cache = {}
    stages_cache = {}
    
    print(f"开始从 {CSV_FILENAME} 导入数据...")
    
    count = 0
    imported_count = 0
    
    try:
        with open(CSV_FILENAME, mode='r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            
            for row in reader:
                count += 1
                try:
                    year_str, stage_full_desc, rank_str, rider_name, team_name, time_str = row
                    year = int(year_str)
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
                    print(f"错误: 解析行 {count} ({row}) 时失败: {e}")
                    continue

                # Get-or-Create 逻辑 (保持不变)
                edition = editions_cache.get(year)
                if not edition:
                    edition = Edition(race=race, year=year)
                    db.session.add(edition)
                    editions_cache[year] = edition
                
                rider = riders_cache.get(rider_name)
                if not rider:
                    rider = Rider(rider_name= rider_name)
                    db.session.add(rider)
                    riders_cache[rider_name] = rider
                    
                team = teams_cache.get(team_name)
                if not team:
                    team = Team(team_name=team_name)
                    db.session.add(team)
                    teams_cache[team_name] = team
                    
                stage_key = (year, stage_number)
                stage = stages_cache.get(stage_key)
                if not stage:
                    stage = Stage(edition=edition, stage_number=stage_number, stage_route=stage_route)
                    db.session.add(stage)
                    stages_cache[stage_key] = stage

                result = StageResult(
                    stage=stage,
                    rider=rider,
                    team=team,
                    rank=rank,
                    time_in_seconds=time_in_seconds
                )
                db.session.add(result)
                imported_count += 1
                
                if imported_count % BATCH_SIZE == 0:
                    print(f"    ... 正在提交 {imported_count} 条记录 ...")
                    db.session.commit()

        print("正在提交最后一批数据...")
        db.session.commit()
        
    except Exception as e:
        print(f"发生严重错误: {e}。正在回滚...")
        db.session.rollback()
    finally:
        end_time = time.time()
        print("\n--- 导入完成 ---")
        print(f"总共处理 CSV 行数: {count}")
        print(f"成功导入成绩条数: {imported_count}")
        print(f"总耗时: {end_time - start_time:.2f} 秒")


# --- 脚本执行入口 (修改) ---
if __name__ == '__main__':
    # 1. 创建 app 实例
    app = create_app()
    
    # 2. 在 app 上下文中运行导入函数
    # 这是必需的，因为 db.session 需要知道哪个 app 正在运行
    with app.app_context():
        run_import()