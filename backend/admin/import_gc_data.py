"""
导入环法总成绩(GC)数据脚本

CSV 文件格式: Year,Stage,Rank,Rider,Team,Time
- Stage 字段忽略（已经是每年最后赛段的总成绩）
- 直接按年份分组导入
"""
import csv
import re
from pathlib import Path

# Adjust imports to work when run as a script or module
try:
    from models.models import Base, Race, Edition, Team, Rider, GeneralClassification
    from models.database import engine, SessionLocal
except ImportError:
    # Fallback for running directly
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from models.models import Base, Race, Edition, Team, Rider, GeneralClassification
    from models.database import engine, SessionLocal

# 新的 CSV 文件：已提取好的每年总成绩数据
CSV_FILENAME = Path(__file__).resolve().parent / 'tdf_gc_1903-2025.csv'


def parse_time_to_seconds(time_str):
    """解析时间字符串为秒数，格式如 '76h 00' 32'''"""
    if not time_str:
        return 0
    hours, minutes, seconds = 0, 0, 0
    h_match = re.search(r'(\d+)h', time_str)
    m_match = re.search(r"(\d+)'", time_str)
    s_match = re.search(r"(\d+)''", time_str)
    if h_match: hours = int(h_match.group(1))
    if m_match: minutes = int(m_match.group(1))
    if s_match: seconds = int(s_match.group(1))
    return (hours * 3600) + (minutes * 60) + seconds


def run_import_gc():
    print("=" * 50)
    print("开始导入环法总成绩(GC)数据...")
    print("=" * 50)
    session = SessionLocal()
    
    try:
        if not CSV_FILENAME.exists():
            print(f"错误: 文件 {CSV_FILENAME} 不存在")
            return

        # 1. 读取并按年份分组
        print(f"读取文件: {CSV_FILENAME}")
        rows_by_year = {}
        total_rows = 0
        
        with open(CSV_FILENAME, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                year_str = row.get('Year')
                if not year_str:
                    continue
                try:
                    year = int(year_str)
                except ValueError:
                    continue  # 跳过无效年份（如标题行）
                    
                if year not in rows_by_year:
                    rows_by_year[year] = []
                rows_by_year[year].append(row)
                total_rows += 1
        
        print(f"读取完成: {total_rows} 条记录, 覆盖 {len(rows_by_year)} 个年份")
        
        # 2. 获取或创建 Tour de France 赛事
        race = session.query(Race).filter(Race.race_name == 'Tour de France').first()
        if not race:
            race = Race(race_name='Tour de France')
            session.add(race)
            session.flush()
            print("创建赛事: Tour de France")

        # 3. 预加载车手和车队缓存（提高性能）
        riders_cache = {r.rider_name.upper(): r for r in session.query(Rider).all()}
        teams_cache = {t.team_name.upper(): t for t in session.query(Team).all()}
        print(f"已加载缓存: {len(riders_cache)} 位车手, {len(teams_cache)} 支车队")

        # 4. 按年份处理
        imported_count = 0
        for year in sorted(rows_by_year.keys()):
            gc_rows = rows_by_year[year]
            
            # 获取或创建 Edition
            edition = session.query(Edition).filter(
                Edition.year == year, 
                Edition.race_id == race.race_id
            ).first()
            if not edition:
                edition = Edition(year=year, race_id=race.race_id)
                session.add(edition)
                session.flush()
            
            # 按排名排序
            try:
                gc_rows.sort(key=lambda x: int(x.get('Rank', 9999)))
            except ValueError:
                pass
            
            # 获取冠军时间用于计算 gap
            winner_time = 0
            year_imported = 0
            year_skipped = 0
            
            for row in gc_rows:
                try:
                    rank_str = row.get('Rank', '')
                    if not rank_str or not rank_str.isdigit():
                        continue
                    rank = int(rank_str)
                    
                    rider_name = row.get('Rider', '').strip().upper()
                    team_name = row.get('Team', '').strip().upper()
                    time_str = row.get('Time', '')
                    time_sec = parse_time_to_seconds(time_str)
                    
                    if not rider_name or not team_name:
                        continue
                    
                    # 计算与冠军的时间差
                    if rank == 1:
                        winner_time = time_sec
                        gap = 0
                    else:
                        gap = time_sec - winner_time if time_sec > 0 and winner_time > 0 else 0
                    
                    # 查找或创建车手（先从缓存查，再从数据库查，最后创建）
                    rider = riders_cache.get(rider_name)
                    if not rider:
                        # 尝试从数据库查找（可能之前未加载到缓存）
                        rider = session.query(Rider).filter(Rider.rider_name == rider_name).first()
                        if not rider:
                            rider = Rider(rider_name=rider_name)
                            session.add(rider)
                            session.flush()
                        riders_cache[rider_name] = rider
                    
                    # 查找或创建车队
                    team = teams_cache.get(team_name)
                    if not team:
                        team = session.query(Team).filter(Team.team_name == team_name).first()
                        if not team:
                            team = Team(team_name=team_name)
                            session.add(team)
                            session.flush()
                        teams_cache[team_name] = team
                    
                    # 检查是否已存在该记录
                    gc_record = session.query(GeneralClassification).filter(
                        GeneralClassification.edition_id == edition.edition_id,
                        GeneralClassification.rider_id == rider.rider_id
                    ).first()
                    
                    if not gc_record:
                        gc_record = GeneralClassification(
                            edition_id=edition.edition_id,
                            rider_id=rider.rider_id,
                            team_id=team.team_id,
                            rank=rank,
                            time_in_seconds=time_sec,
                            gap_in_seconds=gap
                        )
                        session.add(gc_record)
                    else:
                        # 更新已存在的记录
                        gc_record.rank = rank
                        gc_record.time_in_seconds = time_sec
                        gc_record.gap_in_seconds = gap
                        gc_record.team_id = team.team_id
                    
                    year_imported += 1
                    imported_count += 1
                    
                except Exception as row_error:
                    session.rollback()  # 回滚当前事务
                    year_skipped += 1
                    # 静默跳过错误，减少输出
                    continue
            
            session.commit()
            skip_msg = f" (跳过 {year_skipped} 条)" if year_skipped > 0 else ""
            print(f"  {year} 年: 导入 {year_imported} 条总成绩记录{skip_msg}")

        print("=" * 50)
        print(f"导入完成! 共处理 {imported_count} 条总成绩记录")
        print("=" * 50)

    except Exception as e:
        print(f"发生错误: {e}")
        session.rollback()
        import traceback
        traceback.print_exc()
    finally:
        session.close()


if __name__ == "__main__":
    run_import_gc()
