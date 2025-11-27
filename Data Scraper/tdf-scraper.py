import requests
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
import re

# --- 全局变量 ---
MAIN_PAGE_URL = "https://www.letour.fr/en/history"
BASE_URL = "https://www.letour.fr"
# 模拟浏览器请求
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
}
# 注意：全局的 ALL_RESULTS 列表已被移除

def get_year_urls(session):
    """
    步骤1：从主页隐藏的 <select> 标签中获取所有年份的名称和对应的 AJAX 路径。
    """
    print(f"正在访问主页: {MAIN_PAGE_URL}")
    try:
        response = session.get(MAIN_PAGE_URL, headers=HEADERS)
        response.raise_for_status()
        
        # *** 使用 'lxml' 解析器 ***
        soup = BeautifulSoup(response.text, 'lxml')
        
        # 找到隐藏的年份选择框
        select_year = soup.find("select", id="history-year")
        if not select_year:
            print("错误：在主页上未找到 'history-year' 下拉菜单。")
            return []
            
        year_options = []
        # 遍历所有 <option>
        for option in select_year.find_all("option"):
            # 使用 data-tabs-target 获取年份数字 (如 "2025", "2024", ...)
            year_text = option.get("data-tabs-target")
            year_path = option.get("value")
            
            if year_text and year_path:
                year_options.append((year_text, year_path))
                
        print(f"成功找到 {len(year_options)} 个年份 (从 {year_options[-1][0]} 到 {year_options[0][0]})。")
        return year_options
        
    except requests.exceptions.RequestException as e:
        print(f"访问主页失败: {e}")
        return []

def get_year_ajax_data(session, year_path):
    """
    步骤2：访问特定年份的 AJAX 路径，获取该年份的 HTML 内容片段。
    从这个片段中提取 "Ranking" 和 "Stages" 的 URL。
    """
    year_url = urljoin(BASE_URL, year_path)
    try:
        response = session.get(year_url, headers=HEADERS)
        response.raise_for_status()
        # *** 使用 'lxml' 解析器 ***
        soup = BeautifulSoup(response.text, 'lxml')
        
        # 寻找 "Ranking" 按钮并获取其 AJAX 路径
        ranking_button = soup.find("button", {"data-tabs-target": "ranking"})
        if not ranking_button:
            if soup.find("table", class_="rankingTable"):
                print("    ... (特殊年份：未找到 Ranking 标签，但找到了排名表)")
                return year_path, None 
            else:
                raise Exception("未找到 'Ranking' 按钮")
                
        ranking_path = ranking_button.get("data-tabs-ajax")
        
        # 寻找 "Stages" 按钮并获取其 AJAX 路径
        stages_button = soup.find("button", {"data-tabs-target": "stages"})
        stages_path = stages_button.get("data-tabs-ajax") if stages_button else None

        return ranking_path, stages_path
        
    except Exception as e:
        print(f"    ... 获取年份 {year_url} 的 AJAX 数据失败: {e}")
        return None, None

def get_stage_options(session, ranking_base_path):
    """
    步骤3：访问 "Ranking" 路径，获取该年份所有赛段的下拉列表。
    """
    if not ranking_base_path:
        return []
        
    ranking_url = urljoin(BASE_URL, ranking_base_path)
    try:
        response = session.get(ranking_url, headers=HEADERS)
        response.raise_for_status()
        # *** 使用 'lxml' 解析器 ***
        soup = BeautifulSoup(response.text, 'lxml')
        
        select_stage = soup.find("select", id="stageSelect")
        if not select_stage:
            return []
            
        stage_options = []
        for option in select_stage.find_all("option"):
            stage_name = option.text.strip()
            stage_name = re.sub(r'\s+', ' ', stage_name)
            stage_value = option.get("value")
            
            if stage_name and stage_value:
                stage_options.append((stage_name, stage_value))
                
        return stage_options
        
    except Exception as e:
        print(f"    ... 获取赛段列表 {ranking_url} 失败: {e}")
        return []

def parse_and_store_table(session, url, year_text, stage_text, results_list):
    """
    步骤4：访问最终的赛段排名 URL，解析表格并存储数据到传入的列表中。
    """
    try:
        response = session.get(url, headers=HEADERS)
        response.raise_for_status()
        
        # *** 使用 'lxml' 解析器 ***
        soup = BeautifulSoup(response.content, 'lxml')
        table = soup.find("table", class_="rankingTable")
        if not table:
            print(f"    ... 在 {stage_text} 未找到 'rankingTable'。")
            return 0

        rows = table.find("tbody").find_all("tr")
        scraped_count = 0
        
        for row in rows:
            cells = row.find_all("td")
            if len(cells) >= 4:
                rank = cells[0].text.strip()
                rider = cells[1].text.strip()
                team = cells[2].text.strip()
                time_result = cells[3].text.strip()
                
                if rank: # 过滤掉空的排位行
                    # *** 修改：追加到传入的临时列表 ***
                    results_list.append({
                        "Year": year_text,
                        "Stage": stage_text,
                        "Rank": rank,
                        "Rider": rider,
                        "Team": team,
                        "Time": time_result
                    })
                    scraped_count += 1
        return scraped_count
        
    except Exception as e:
        print(f"    ... 解析表格 {url} 失败: {e}")
        return 0

def main():
    """主爬虫逻辑"""
    
    # --- 步骤 0: 定义输出文件并在开始时写入表头 ---
    output_file = "tour_de_france_ite_1903-2025.csv"
    header_df = pd.DataFrame(columns=["Year", "Stage", "Rank", "Rider", "Team", "Time"])
    
    try:
        # 'w' 模式会覆盖旧文件
        header_df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"数据文件已创建/重置: {output_file}")
    except PermissionError:
        print(f"\n[错误] 文件被占用！请关闭 {output_file} 后再运行。")
        return
    except Exception as e:
        print(f"\n[错误] 创建文件失败: {e}")
        return

    session = requests.Session()
    
    try:
        year_options = get_year_urls(session)
        if not year_options:
            return

        # --- 遍历所有年份 ---
        for year_text, year_path in year_options:
            
            # (可选) 仅测试最近几年
            if int(year_text) < 2000: continue
            
            print(f"--- 正在处理年份: {year_text} ---")
            year_results = [] # 存储当年的所有数据
            
            ranking_base_path, _ = get_year_ajax_data(session, year_path)
            if not ranking_base_path:
                print(f"    ... 无法找到 {year_text} 年的 'Ranking' 路径，跳过。")
                continue
                
            stage_options = get_stage_options(session, ranking_base_path)
            
            if not stage_options:
                print(f"  ... 未找到 {year_text} 年的赛段列表。爬取总排名...")
                final_url = urljoin(BASE_URL, ranking_base_path) + "?type=ite"
                # *** 修改：传入 year_results 列表 ***
                count = parse_and_store_table(session, final_url, year_text, "Final Results", year_results)
                print(f"    ... 已爬取 {year_text} 总排名 ( {count} 条记录 )")
            else:
                # --- 遍历所有赛段 ---
                print(f"  找到 {len(stage_options)} 个赛段。开始遍历赛段...")
                for stage_name, stage_value in stage_options:
                    rank_type = "ite" # 'ite' = 个人赛段排名
                    final_url = urljoin(BASE_URL, ranking_base_path) + f"?stage={stage_value}&type={rank_type}"
                    
                    # *** 修改：传入 year_results 列表 ***
                    count = parse_and_store_table(session, final_url, year_text, stage_name, year_results)
                    print(f"    ... 已爬取 {stage_name} ( {count} 条记录 )")
                    time.sleep(0.1) # 友好爬取，暂停0.1秒

            # --- 步骤 5: 将当年的数据追加到 CSV 文件 ---
            if year_results:
                print(f"  ... 正在将 {year_text} 年的 {len(year_results)} 条记录追加到 CSV...")
                year_df = pd.DataFrame(year_results)
                try:
                    # 模式 'a' = append (追加)
                    # header=False 因为表头已经写过了
                    year_df.to_csv(output_file, mode='a', header=False, index=False, encoding='utf-8-sig')
                except PermissionError:
                    print(f"\n[错误] 文件被占用！请关闭 {output_file} 后再运行。")
                    return
            
            print(f"--- {year_text} 年处理完毕 ---\n")

    except Exception as e:
        print(f"\n--- 爬虫意外终止 ---")
        print(f"错误详情: {e}")
    
    finally:
        print("\n--- 爬取结束 ---")
        session.close()
        print(f"所有已爬取的数据均已保存到: {output_file}")


if __name__ == "__main__":
    main()