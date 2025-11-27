<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

const navigateToRaces = () => {
  router.push('/races')
}

const navigateToRiders = () => {
  router.push('/riders')
}
</script>

<template>
  <div class="landing-container">
    <div class="hero-section">
      <h1 class="hero-title">环法自行车赛交流站</h1>
      <p class="hero-subtitle">探索百年赛事历史，追踪传奇车手足迹</p>
    </div>

    <div class="cards-container">
      <!-- 赛事入口卡片 -->
      <div class="entry-card race-card" @click="navigateToRaces">
        <div class="card-icon">🏆</div>
        <h2 class="card-title">赛事数据</h2>
        <p class="card-description">浏览历届环法赛事，查看每个赛段的详细成绩与排名</p>
        <div class="card-arrow">→</div>
      </div>

      <!-- 车手入口卡片 -->
      <div class="entry-card rider-card" @click="navigateToRiders">
        <div class="card-icon">🚴</div>
        <h2 class="card-title">车手信息</h2>
        <p class="card-description">搜索车手资料，查看参赛记录、冠军数量与效力车队</p>
        <div class="card-arrow">→</div>
      </div>

      <div class="entry-card rider-card" @click="navigateToRiders">
        <div class="card-icon">🗣️</div>
        <h2 class="card-title">论坛</h2>
        <p class="card-description">参与讨论，分享观点，连接环法自行车赛爱好者社区</p>
        <div class="card-arrow">→</div>
      </div>
    </div>

    <footer class="landing-footer">
      <p>Tour de France Database © 2025</p>
    </footer>
  </div>
</template>

<style scoped>
.landing-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  font-family:
    'Inter',
    -apple-system,
    BlinkMacSystemFont,
    'Segoe UI',
    Roboto,
    sans-serif;
  position: relative;
  overflow: hidden;
}

/* 背景层：三个倾斜的颜色区域 */
.landing-container::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: linear-gradient(
    135deg,
    #ff286e 0%,
    #ff286e 30%,
    #ffed00 30%,
    #ffed00 55%,
    #da291c 55%,
    #da291c 100%
  );
  z-index: 0;
  clip-path: polygon(20% 0%, 80% 0%, 60% 100%, 0% 100%);
}

/* 中间黄色区域（环法 - 加宽视觉中心） */
.landing-container::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background:
    linear-gradient(
      45deg,
      rgba(255, 255, 255, 0.05) 25%,
      transparent 25%,
      transparent 50%,
      rgba(255, 255, 255, 0.05) 50%,
      rgba(255, 255, 255, 0.05) 75%,
      transparent 75%,
      transparent
    ),
    linear-gradient(
      45deg,
      rgba(255, 255, 255, 0.05) 25%,
      transparent 25%,
      transparent 50%,
      rgba(255, 255, 255, 0.05) 50%,
      rgba(255, 255, 255, 0.05) 75%,
      transparent 75%,
      transparent
    );
  background-size: 60px 60px;
  background-position:
    0 0,
    30px 30px;
  clip-path: polygon(20% 0%, 80% 0%, 100% 100%, 0% 100%);
  z-index: 1;
}

/* 纹理覆盖层 - 沥青路面效果 */
.landing-container {
  background: repeating-linear-gradient(
    90deg,
    rgba(0, 0, 0, 0.187) 0px,
    rgba(0, 0, 0, 0.432) 2px,
    transparent 2px,
    transparent 4px
  );
  background-attachment: fixed;
}

.hero-section {
  text-align: center;
  margin-bottom: 4rem;
  animation: fadeInDown 0.8s ease-out;
  position: relative;
  z-index: 10;
  text-shadow: 2px 2px 8px rgba(0, 0, 0, 0.3);
}

.hero-title {
  font-size: 3.5rem;
  font-weight: 800;
  color: white;
  margin-bottom: 1rem;
  text-shadow: 3px 3px 12px rgba(0, 0, 0, 0.4);
  letter-spacing: -0.02em;
}

.hero-subtitle {
  font-size: 1.25rem;
  color: rgba(52, 51, 51, 0.95);
  font-weight: 300;
  text-shadow: 2px 2px 6px rgba(0, 0, 0, 0.3);
}

.cards-container {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 2rem;
  max-width: 1200px;
  width: 100%;
  animation: fadeInUp 1s ease-out;
  position: relative;
  z-index: 10;
}

.entry-card {
  background: rgba(255, 255, 255, 0.98);
  backdrop-filter: blur(10px);
  border-radius: 1rem;
  padding: 2.5rem 2rem;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
  position: relative;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.5);
}

.entry-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, #fbbf24, #f59e0b);
  transform: scaleX(0);
  transition: transform 0.3s ease;
}

.entry-card:hover::before {
  transform: scaleX(1);
}

.entry-card:hover {
  transform: translateY(-8px) rotateX(5deg);
  box-shadow: 0 15px 40px rgba(0, 0, 0, 0.3);
}

.card-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
  filter: grayscale(0.3);
  transition: all 0.3s ease;
}

.entry-card:hover .card-icon {
  filter: grayscale(0);
  transform: scale(1.1) rotateY(10deg);
}

.card-title {
  font-size: 1.75rem;
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 0.75rem;
}

.card-description {
  font-size: 1rem;
  color: #64748b;
  line-height: 1.6;
  margin-bottom: 1.5rem;
}

.card-arrow {
  font-size: 1.5rem;
  color: #f59e0b;
  font-weight: 700;
  text-align: right;
  transition: transform 0.3s ease;
}

.entry-card:hover .card-arrow {
  transform: translateX(8px);
}

.landing-footer {
  margin-top: 4rem;
  color: rgba(255, 255, 255, 0.9);
  font-size: 0.875rem;
  position: relative;
  z-index: 10;
  font-weight: 500;
  text-shadow: 1px 1px 4px rgba(0, 0, 0, 0.3);
}

@keyframes fadeInDown {
  from {
    opacity: 0;
    transform: translateY(-30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 768px) {
  .hero-title {
    font-size: 2.5rem;
  }

  .cards-container {
    grid-template-columns: 1fr;
    max-width: 400px;
  }
}
</style>
