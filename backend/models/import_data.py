import csv
import re
import time
from decimal import Decimal
from pathlib import Path

# ??????????
from .models import Base, Race, Edition, Team, Rider, Stage, StageResult
from .database import engine, SessionLocal

# --- ???? (????) ---
DEFAULT_RACE_NAME = 'Tour de France'
# ? CSV ??????????????????????????
CSV_FILENAME = Path(__file__).resolve().parent / 'ite_2000-2025.csv'
BATCH_SIZE = 5000

# --- ?????? (????) ---
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
        print(f"[????] ????????: '{stage_full_desc}'. ??: {e}")
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

# --- ????? (????) ---
def run_import():
    start_time = time.time()
    
    # ????
    session = SessionLocal()
    
    try:
        print("???????????...")
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)

        race = session.query(Race).filter_by(race_name=DEFAULT_RACE_NAME).first()
        if not race:
            print(f"?????: {DEFAULT_RACE_NAME}")
            race = Race(race_name=DEFAULT_RACE_NAME) # ??? country
            session.add(race)
            session.commit()

        editions_cache = {}
        teams_cache = {}
        riders_cache = {}
        stages_cache = {}
        
        print(f"??? {CSV_FILENAME} ????...")
        
        count = 0
        imported_count = 0
        
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
                    print(f"??: ??? {count} ({row}) ???: {e}")
                    continue

                # Get-or-Create ?? (????)
                edition = editions_cache.get(year)
                if not edition:
                    edition = Edition(race=race, year=year)
                    session.add(edition)
                    editions_cache[year] = edition
                
                rider = riders_cache.get(rider_name)
                if not rider:
                    rider = Rider(rider_name= rider_name)
                    session.add(rider)
                    riders_cache[rider_name] = rider
                    
                team = teams_cache.get(team_name)
                if not team:
                    team = Team(team_name=team_name)
                    session.add(team)
                    teams_cache[team_name] = team
                    
                stage_key = (year, stage_number)
                stage = stages_cache.get(stage_key)
                if not stage:
                    stage = Stage(edition=edition, stage_number=stage_number, stage_route=stage_route)
                    session.add(stage)
                    stages_cache[stage_key] = stage

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
                    print(f"    ... ???? {imported_count} ??? ...")
                    session.commit()

        print("??????????...")
        session.commit()
        
    except Exception as e:
        print(f"??????: {e}?????...")
        session.rollback()
    finally:
        session.close()
        end_time = time.time()
        print("\n--- ???? ---")
        print(f"???? CSV ??: {count}")
        print(f"????????: {imported_count}")
        print(f"???: {end_time - start_time:.2f} ?")

# --- ?????? (??) ---
if __name__ == '__main__':
    # ??????????? Flask ??????
    run_import()