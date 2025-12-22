"""
异步 Redis + 缓存预热性能测试
验证改进后的性能提升
"""
import time
import requests
import statistics

BASE_URL = "http://localhost:8000"

def test_prewarmed_cache():
    """测试预热后的缓存命中率"""
    print("\n" + "="*70)
    print("🔥 缓存预热效果测试")
    print("="*70)
    
    # 测试预热的端点
    test_cases = [
        ("/api/async/races", "赛事列表（已预热）"),
        ("/api/async/riders?page=1&limit=16", "车手列表第1页（已预热）"),
        ("/api/async/riders?page=2&limit=16", "车手列表第2页（已预热）"),
        ("/api/async/riders?page=10&limit=16", "车手列表第10页（未预热）"),
        ("/api/async/races/1/editions", "环法届数（已预热）"),
    ]
    
    results = []
    
    for endpoint, description in test_cases:
        print(f"\n📊 测试: {description}")
        print(f"   URL: {endpoint}")
        
        times = []
        for i in range(3):
            start = time.time()
            response = requests.get(f"{BASE_URL}{endpoint}")
            elapsed = (time.time() - start) * 1000
            times.append(elapsed)
            
            if response.status_code == 200:
                print(f"   第 {i+1} 次: {elapsed:.2f}ms")
            else:
                print(f"   第 {i+1} 次: 失败 ({response.status_code})")
        
        avg_time = statistics.mean(times)
        results.append({
            "description": description,
            "avg_time": avg_time,
            "min_time": min(times),
            "max_time": max(times)
        })
        print(f"   平均: {avg_time:.2f}ms")
    
    # 汇总结果
    print("\n" + "="*70)
    print("📈 测试结果汇总")
    print("="*70)
    
    prewarmed = [r for r in results if "已预热" in r["description"]]
    not_prewarmed = [r for r in results if "未预热" in r["description"]]
    
    if prewarmed:
        avg_prewarmed = statistics.mean([r["avg_time"] for r in prewarmed])
        print(f"\n✅ 预热端点平均响应: {avg_prewarmed:.2f}ms")
        for r in prewarmed:
            print(f"   - {r['description']}: {r['avg_time']:.2f}ms")
    
    if not_prewarmed:
        avg_not_prewarmed = statistics.mean([r["avg_time"] for r in not_prewarmed])
        print(f"\n⚠️  未预热端点平均响应: {avg_not_prewarmed:.2f}ms")
        for r in not_prewarmed:
            print(f"   - {r['description']}: {r['avg_time']:.2f}ms")
    
    if prewarmed and not_prewarmed:
        improvement = ((avg_not_prewarmed - avg_prewarmed) / avg_not_prewarmed) * 100
        print(f"\n🚀 预热效果: 提升 {improvement:.1f}%")


def test_async_redis_performance():
    """测试异步 Redis 读写性能"""
    print("\n" + "="*70)
    print("⚡ 异步 Redis 性能测试")
    print("="*70)
    
    endpoint = "/api/async/riders?page=5&limit=16"
    
    # 清除特定缓存（如果有管理接口）
    # requests.post(f"{BASE_URL}/api/cache/clear", json={"pattern": "riders_async:*"})
    
    print(f"\n🔍 测试端点: {endpoint}")
    print("-" * 70)
    
    # 第一次请求（可能缓存未命中）
    print("\n第 1 次请求 (可能 MISS):")
    times_first = []
    for i in range(5):
        start = time.time()
        response = requests.get(f"{BASE_URL}{endpoint}")
        elapsed = (time.time() - start) * 1000
        times_first.append(elapsed)
        print(f"  第 {i+1} 次: {elapsed:.2f}ms")
    
    time.sleep(0.2)  # 等待异步写入完成
    
    # 后续请求（应该缓存命中）
    print("\n第 2-5 次请求 (应该 HIT):")
    times_cached = []
    for i in range(5):
        start = time.time()
        response = requests.get(f"{BASE_URL}{endpoint}")
        elapsed = (time.time() - start) * 1000
        times_cached.append(elapsed)
        print(f"  第 {i+1} 次: {elapsed:.2f}ms")
    
    # 统计
    avg_first = statistics.mean(times_first)
    avg_cached = statistics.mean(times_cached)
    improvement = ((avg_first - avg_cached) / avg_first) * 100
    
    print(f"\n📊 统计结果:")
    print(f"   首次平均:   {avg_first:.2f}ms")
    print(f"   缓存命中:   {avg_cached:.2f}ms")
    print(f"   性能提升:   {improvement:.1f}%")
    print(f"   加速倍数:   {avg_first/avg_cached:.2f}x")


def test_concurrent_with_async_redis():
    """测试异步 Redis 下的并发性能"""
    import concurrent.futures
    
    print("\n" + "="*70)
    print("🔄 并发测试 (异步 Redis)")
    print("="*70)
    
    endpoint = "/api/async/races"
    num_requests = 20
    
    def make_request(n):
        start = time.time()
        response = requests.get(f"{BASE_URL}{endpoint}")
        elapsed = (time.time() - start) * 1000
        return elapsed, response.status_code
    
    print(f"\n🔍 并发 {num_requests} 个请求...")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_requests) as executor:
        futures = [executor.submit(make_request, i) for i in range(num_requests)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    
    times = [r[0] for r in results]
    successes = sum(1 for r in results if r[1] == 200)
    
    print(f"\n📊 结果:")
    print(f"   总请求数:   {num_requests}")
    print(f"   成功数:     {successes}")
    print(f"   平均响应:   {statistics.mean(times):.2f}ms")
    print(f"   最快:       {min(times):.2f}ms")
    print(f"   最慢:       {max(times):.2f}ms")
    print(f"   标准差:     {statistics.stdev(times):.2f}ms")
    
    # 分析响应时间分布
    fast = sum(1 for t in times if t < 10)
    medium = sum(1 for t in times if 10 <= t < 50)
    slow = sum(1 for t in times if t >= 50)
    
    print(f"\n⏱️  响应时间分布:")
    print(f"   < 10ms:     {fast} 个 ({fast/num_requests*100:.1f}%)")
    print(f"   10-50ms:    {medium} 个 ({medium/num_requests*100:.1f}%)")
    print(f"   >= 50ms:    {slow} 个 ({slow/num_requests*100:.1f}%)")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("🚀 异步 Redis + 缓存预热 综合性能测试")
    print("="*70)
    print(f"📍 服务器: {BASE_URL}")
    
    try:
        response = requests.get(f"{BASE_URL}/")
        print("✅ 服务器可用")
        print("\n💡 提示: 请确保服务器已重启以启用缓存预热功能")
    except Exception as e:
        print(f"❌ 服务器无法连接: {str(e)}")
        print("请先启动服务器: uvicorn app:app --reload\n")
        exit(1)
    
    # 运行测试
    test_prewarmed_cache()
    test_async_redis_performance()
    test_concurrent_with_async_redis()
    
    print("\n" + "="*70)
    print("✅ 所有测试完成!")
    print("="*70)
    print("\n🎯 关键改进:")
    print("   1. ✅ 使用异步 Redis 客户端（redis.asyncio）")
    print("   2. ✅ 消除同步阻塞操作")
    print("   3. ✅ 启动时预热热点数据")
    print("   4. ✅ 后台异步写入缓存")
    print("\n📈 预期效果:")
    print("   - 预热数据首次访问: 接近缓存命中速度（2-5ms）")
    print("   - 未预热数据首次访问: 略有提升（省略同步阻塞）")
    print("   - 高并发场景: 显著提升（20-30%）")
    print()
