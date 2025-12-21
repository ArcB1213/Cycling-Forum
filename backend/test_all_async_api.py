"""
测试所有异步 API 端点
"""
import requests
import time
from typing import Dict, Any

BASE_URL = "http://localhost:8000"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_success(msg):
    print(f"{Colors.GREEN}✅ {msg}{Colors.END}")

def print_error(msg):
    print(f"{Colors.RED}❌ {msg}{Colors.END}")

def print_info(msg):
    print(f"{Colors.BLUE}ℹ️  {msg}{Colors.END}")

def test_endpoint(name: str, url: str, expected_keys: list = None) -> bool:
    """测试单个端点"""
    print(f"\n{'='*70}")
    print(f"测试: {name}")
    print(f"URL: {url}")
    print(f"{'='*70}")
    
    try:
        start = time.time()
        response = requests.get(url, timeout=10)
        elapsed = (time.time() - start) * 1000
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"成功 - 响应时间: {elapsed:.2f}ms")
            
            # 显示数据摘要
            if isinstance(data, list):
                print_info(f"返回列表，长度: {len(data)}")
                if data and expected_keys:
                    actual_keys = set(data[0].keys())
                    if set(expected_keys).issubset(actual_keys):
                        print_success(f"数据结构正确: {expected_keys}")
                    else:
                        print_error(f"数据结构不匹配，实际键: {list(actual_keys)}")
            elif isinstance(data, dict):
                print_info(f"返回字典，键: {list(data.keys())}")
                if expected_keys:
                    actual_keys = set(data.keys())
                    if set(expected_keys).issubset(actual_keys):
                        print_success(f"数据结构正确: {expected_keys}")
                    else:
                        print_error(f"数据结构不匹配，实际键: {list(actual_keys)}")
            
            return True
        else:
            print_error(f"失败 - HTTP {response.status_code}")
            print(f"错误: {response.text[:200]}")
            return False
            
    except requests.exceptions.ConnectionError:
        print_error("连接失败 - 请确保服务正在运行")
        return False
    except requests.exceptions.Timeout:
        print_error("超时 - 请求超过10秒")
        return False
    except Exception as e:
        print_error(f"异常: {str(e)}")
        return False


def main():
    print("""
╔══════════════════════════════════════════════════════════════════╗
║              🚀 异步 API 完整测试套件                            ║
╚══════════════════════════════════════════════════════════════════╝
""")
    
    results = {}
    
    # 测试赛事相关API
    print("\n" + "🏁"*35)
    print("测试分组 1: 赛事相关 API")
    print("🏁"*35)
    
    results['races'] = test_endpoint(
        "获取赛事列表（异步）",
        f"{BASE_URL}/api/async/races",
        expected_keys=['race_id', 'race_name']
    )
    
    results['editions'] = test_endpoint(
        "获取赛事届数（异步）",
        f"{BASE_URL}/api/async/races/1/editions",
        expected_keys=['race', 'editions']
    )
    
    results['stages'] = test_endpoint(
        "获取赛段列表（异步）",
        f"{BASE_URL}/api/async/editions/1/stages",
        expected_keys=['edition_year', 'race_name', 'stages']
    )
    
    results['stage_results'] = test_endpoint(
        "获取赛段结果（异步）",
        f"{BASE_URL}/api/async/stages/1/results",
        expected_keys=['stage_info', 'results']
    )
    
    # 测试骑手相关API
    print("\n" + "🚴"*35)
    print("测试分组 2: 骑手相关 API")
    print("🚴"*35)
    
    results['riders'] = test_endpoint(
        "获取骑手列表（异步）",
        f"{BASE_URL}/api/async/riders",
        expected_keys=['rider_id', 'rider_name']
    )
    
    results['rider_detail'] = test_endpoint(
        "获取骑手详情（异步）",
        f"{BASE_URL}/api/async/riders/1",
        expected_keys=['rider', 'stats']
    )
    
    results['rider_races'] = test_endpoint(
        "获取骑手参赛记录（异步）",
        f"{BASE_URL}/api/async/riders/1/races",
        expected_keys=['rider', 'race_records']
    )
    
    results['rider_wins'] = test_endpoint(
        "获取骑手冠军记录（异步）",
        f"{BASE_URL}/api/async/riders/1/wins",
        expected_keys=['rider', 'win_records']
    )
    
    # 显示测试总结
    print("\n" + "="*70)
    print("📊 测试总结")
    print("="*70)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    print(f"\n✅ 通过: {passed}/{total}")
    print(f"❌ 失败: {total - passed}/{total}")
    print(f"📈 成功率: {passed/total*100:.1f}%\n")
    
    if passed == total:
        print_success("🎉 所有异步 API 测试通过！")
        print_info("系统已准备好进行高并发压力测试")
    else:
        print_error("⚠️  部分测试失败，请检查日志")
        print("\n失败的端点:")
        for name, success in results.items():
            if not success:
                print(f"  - {name}")
    
    print("\n" + "="*70)
    print("💡 下一步:")
    print("  1. 使用 Locust 进行压力测试:")
    print("     locust -f locustfile.py --host=http://localhost:8000")
    print("  2. 访问 http://localhost:8089 查看压测结果")
    print("  3. 对比同步 vs 异步性能差异")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
