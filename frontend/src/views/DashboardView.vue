<template>
  <div class="page-container">
    <div class="dash-header">
      <h2 style="margin:0">仪表盘</h2>
      <div class="dash-actions">
        <span class="last-refresh">上次刷新: {{ lastRefreshTime }}</span>
        <el-select v-model="refreshInterval" size="small" style="width:110px" @change="onRefreshIntervalChange">
          <el-option label="关闭自动刷新" :value="0" />
          <el-option label="每 10 秒" :value="10" />
          <el-option label="每 30 秒" :value="30" />
          <el-option label="每 60 秒" :value="60" />
        </el-select>
        <el-button size="small" @click="refreshAll" :loading="loading">
          <el-icon><Refresh /></el-icon> 刷新
        </el-button>
        <el-button size="small" :type="editing ? 'warning' : 'default'" @click="editing = !editing">
          <el-icon><EditPen v-if="!editing" /><Check v-else /></el-icon>
          {{ editing ? '完成排版' : '编辑布局' }}
        </el-button>
        <el-button size="small" @click="resetLayout"><el-icon><Refresh /></el-icon> 重置</el-button>
      </div>
    </div>

    <el-alert v-if="!server.selectedId" type="warning" title="请先在顶部选择 Samba 服务器" :closable="false" show-icon style="margin-bottom:20px" />

    <template v-if="server.selectedId">
      <!-- 全局错误提示 -->
      <el-alert v-if="loadError" type="error" :title="loadError" :closable="false" show-icon style="margin-bottom:12px">
        <template #default><el-button size="small" @click="refreshAll">重试</el-button></template>
      </el-alert>

      <!-- 系统告警 -->
      <div v-if="o.alerts && o.alerts.length" style="margin-bottom:20px">
        <el-alert v-for="(a,i) in o.alerts" :key="i" :type="a.type" :title="a.message" show-icon :closable="false" style="margin-bottom:8px" />
      </div>

      <!-- 编辑控制栏 -->
      <div v-if="editing" class="edit-toolbar">
        <span>点击卡片选择，用下方滑块调整大小</span>
        <span class="edit-hint">拖拽卡片标题可移动位置</span>
      </div>

      <!-- 网格容器 -->
      <div class="grid-container" ref="gridRef">
        <div v-for="c in cards" :key="c.id"
          class="grid-card"
          :class="{ editing, selected: selected === c.id, 'card-loading': loading && c.id === 'chart' }"
          :style="cardStyle(c)"
          @click.stop="editing && selectCard(c.id)"
        >
          <!-- 编辑态控件 -->
          <div v-if="editing" class="card-drag-handle" @mousedown.prevent.stop="startDrag($event, c)">
            <el-icon size="14"><Rank /></el-icon>
          </div>
          <div v-if="editing" class="card-close" @click="toggleCard(c.id)">
            <el-icon size="14"><Close /></el-icon>
          </div>

          <!-- SMB 服务 -->
          <el-card v-if="c.id==='smb'" shadow="hover" class="fill-card" v-loading="cardLoading.smb">
            <div class="stat-card">
              <div class="stat-icon" :style="sbg(o.smbd_running,'smb')">
                <el-icon :size="28" :color="o.smbd_running?'#67c23a':'#f56c6c'"><Monitor /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ o.smbd_running?'运行中':'已停止' }}</div>
                <div class="stat-label">SMB 服务</div>
              </div>
            </div>
          </el-card>

          <!-- NMB 服务 -->
          <el-card v-else-if="c.id==='nmb'" shadow="hover" class="fill-card" v-loading="cardLoading.nmb">
            <div class="stat-card">
              <div class="stat-icon" :style="sbg(o.nmbd_running,'nmb')">
                <el-icon :size="28" :color="o.nmbd_running?'#67c23a':'#f56c6c'"><Monitor /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ o.nmbd_running?'运行中':'已停止' }}</div>
                <div class="stat-label">NMB 服务</div>
              </div>
            </div>
          </el-card>

          <!-- 在线用户 -->
          <el-card v-else-if="c.id==='sessions'" shadow="hover" class="fill-card" v-loading="cardLoading.sessions">
            <div class="stat-card">
              <div class="stat-icon" style="background:#fef0e8">
                <el-icon :size="28" color="#e6a23c"><Avatar /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ o.active_sessions }}</div>
                <div class="stat-label">在线用户</div>
              </div>
            </div>
          </el-card>

          <!-- 共享目录 -->
          <el-card v-else-if="c.id==='shares'" shadow="hover" class="fill-card" v-loading="cardLoading.shares">
            <div class="stat-card">
              <div class="stat-icon" style="background:#f0e6fe">
                <el-icon :size="28" color="#9b59b6"><FolderOpened /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ o.share_count }}</div>
                <div class="stat-label">共享目录</div>
              </div>
            </div>
          </el-card>

          <!-- 在线用户曲线 -->
          <el-card v-else-if="c.id==='chart'" shadow="hover" class="fill-card">
            <template #header>
              <div class="card-header-row">
                <span>在线用户变化</span>
                <el-radio-group v-model="chartHours" size="small" @change="loadChart">
                  <el-radio-button :value="1">1h</el-radio-button>
                  <el-radio-button :value="6">6h</el-radio-button>
                  <el-radio-button :value="24">24h</el-radio-button>
                  <el-radio-button :value="168">7d</el-radio-button>
                </el-radio-group>
              </div>
            </template>
            <div class="chart-container" style="height:calc(100% - 10px)"></div>
          </el-card>

          <!-- 磁盘 IO -->
          <el-card v-else-if="c.id==='diskio'" shadow="hover" class="fill-card">
            <template #header><span>磁盘 IO 实时</span></template>
            <div v-if="o.disk_io && o.disk_io.length" class="diskio-list">
              <div v-for="dio in o.disk_io" :key="dio.name" class="diskio-device">
                <div class="diskio-name">{{ dio.name }}</div>
                <div class="diskio-metrics">
                  <div class="diskio-metric">
                    <el-icon :size="14" color="#409eff"><Download /></el-icon>
                    <span class="diskio-label">读</span>
                    <span class="diskio-val read">{{ formatSpeed(dio.read_mb_s) }}</span>
                  </div>
                  <div class="diskio-metric">
                    <el-icon :size="14" color="#67c23a"><Upload /></el-icon>
                    <span class="diskio-label">写</span>
                    <span class="diskio-val write">{{ formatSpeed(dio.write_mb_s) }}</span>
                  </div>
                  <div class="diskio-metric">
                    <span class="diskio-label">IOPS</span>
                    <span class="diskio-val">{{ dio.iops }}/s</span>
                  </div>
                  <div class="diskio-metric">
                    <span class="diskio-label">延迟</span>
                    <span class="diskio-val" :style="{color: dio.avg_latency_ms > 10 ? '#f56c6c' : dio.avg_latency_ms > 5 ? '#e6a23c' : '#303133'}">{{ dio.avg_latency_ms.toFixed(1) }}ms</span>
                  </div>
                </div>
              </div>
            </div>
            <el-empty v-else description="暂无 IO 数据" :image-size="40" />
          </el-card>

          <!-- 热门共享 -->
          <el-card v-else-if="c.id==='top'" shadow="hover" class="fill-card">
            <template #header><span>热门共享</span></template>
            <div v-if="topShares.length">
              <div v-for="(t,i) in topShares" :key="t.share" class="top-item">
                <span class="top-rank">#{{ i+1 }}</span>
                <span class="top-name">{{ t.share }}</span>
                <span class="top-size">{{ t.size }}</span>
                <span class="top-count">{{ t.connections }}连接</span>
              </div>
            </div>
            <el-empty v-else description="暂无" :image-size="40" />
          </el-card>

          <!-- 操作记录 -->
          <el-card v-else-if="c.id==='audit'" shadow="hover" class="fill-card">
            <template #header><span>最近操作记录</span></template>
            <div v-if="auditError" class="card-error">
              <el-icon color="#f56c6c"><WarningFilled /></el-icon>
              <span>{{ auditError }}</span>
              <el-button size="small" @click="loadAudit">重试</el-button>
            </div>
            <el-table v-else :data="auditLogs" size="small" stripe height="calc(100% - 10px)">
              <el-table-column prop="created_at" label="时间" width="150">
                <template #default="{row}">{{ formatDateTime(row.created_at) }}</template>
              </el-table-column>
              <el-table-column prop="action" label="操作" width="130">
                <template #default="{row}">
                  <el-tag :type="row.result==='success'?'success':'danger'" size="small">{{ row.action }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="target" label="目标" show-overflow-tooltip />
            </el-table>
          </el-card>

          <!-- 磁盘使用 -->
          <el-card v-else-if="c.id==='disk'" shadow="hover" class="fill-card">
            <template #header><span>磁盘使用</span></template>
            <div v-if="o.disks && o.disks.length">
              <div v-for="d in o.disks" :key="d.share" style="margin-bottom:14px">
                <div style="display:flex;justify-content:space-between;margin-bottom:4px">
                  <span style="font-size:13px;font-weight:500" :title="d.share">{{ d.share.split('/').filter(Boolean).slice(-2).join('/') }}</span>
                  <span style="color:#909399;font-size:13px">{{ d.used }}/{{ d.total }}</span>
                </div>
                <el-progress
                  :percentage="d.percent"
                  :color="d.percent>80?'#f56c6c':d.percent>60?'#e6a23c':'#409eff'"
                  :stroke-width="14"
                />
              </div>
            </div>
            <el-empty v-else description="暂无" :image-size="40" />
          </el-card>

          <!-- 快捷操作 -->
          <el-card v-else-if="c.id==='shortcuts'" shadow="hover" class="fill-card">
            <template #header><span>快捷操作</span></template>
            <div class="short-grid">
              <el-button @click="$router.push('/services')"><el-icon><DataAnalysis/></el-icon> 服务控制</el-button>
              <el-button type="success" @click="$router.push('/users/add')"><el-icon><UserFilled/></el-icon> 新增用户</el-button>
              <el-button @click="$router.push('/shares/add')"><el-icon><FolderOpened/></el-icon> 新增共享</el-button>
              <el-button type="warning" @click="$router.push('/logs')"><el-icon><Tickets/></el-icon> 查看日志</el-button>
            </div>
          </el-card>
        </div>
      </div>

      <!-- 大小选择器 -->
      <div v-if="editing && selected" class="size-panel">
        <span class="size-label">宽度：</span>
        <el-slider v-model="sizeW" :min="1" :max="4" :step="1" show-stops :marks="{1:'窄',2:'中',3:'宽',4:'超宽'}" style="width:260px;margin-right:24px" @change="applySize" />
        <span class="size-label">高度：</span>
        <el-slider v-model="sizeH" :min="1" :max="4" :step="1" show-stops :marks="{1:'小',2:'中',3:'大',4:'超大'}" style="width:260px" @change="applySize" />
        <el-button size="small" style="margin-left:16px" @click="toggleCard(selected)">隐藏此卡片</el-button>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount, nextTick, computed } from 'vue'
import { useServerStore } from '@/stores/server'
import { dashboardApi } from '@/api/dashboard'
import { formatDateTime, formatSpeed } from '@/utils/formatter'
import * as echarts from 'echarts'

const KEY = 'sambav2_grid'
const server = useServerStore()

const o = reactive({
  smbd_running: false, nmbd_running: false, active_sessions: 0, share_count: 0,
  disks: [], disk_io: [], alerts: [],
})
const auditLogs = ref([])
const topShares = ref([])
const loading = ref(false)
const loadError = ref('')
const auditError = ref('')
const chartHours = ref(24)
const lastRefreshTime = ref('--:--:--')

// 各卡片独立 loading 状态
const cardLoading = reactive({
  smb: false, nmb: false, sessions: false, shares: false,
})

const editing = ref(false)
const selected = ref(null)
const sizeW = ref(2)
const sizeH = ref(2)
const chartRef = computed({
  get: () => document.querySelector('.chart-container'),
  set: () => {},
})
let chartInstance = null
let chartLoadAttempted = false

// 用 computed 替代 ref 解决 v-for 中 ref 不工作的问题

// 自动刷新
const refreshInterval = ref(60)
let refreshTimer = null

// 默认 10 张卡片
const allCards = [
  { id:'smb', label:'SMB服务', defaultW:1, defaultH:1 },
  { id:'nmb', label:'NMB服务', defaultW:1, defaultH:1 },
  { id:'sessions', label:'在线用户', defaultW:1, defaultH:1 },
  { id:'shares', label:'共享目录', defaultW:1, defaultH:1 },
  { id:'chart', label:'在线曲线', defaultW:2, defaultH:2 },
  { id:'diskio', label:'磁盘IO', defaultW:2, defaultH:2 },
  { id:'top', label:'热门共享', defaultW:2, defaultH:2 },
  { id:'disk', label:'磁盘使用', defaultW:2, defaultH:2 },
  { id:'audit', label:'操作记录', defaultW:2, defaultH:2 },
  { id:'shortcuts', label:'快捷操作', defaultW:1, defaultH:1 },
]

// ---- 布局逻辑 ----
function loadCards() {
  try {
    const saved = localStorage.getItem(KEY)
    if (saved) {
      const p = JSON.parse(saved)
      // 兼容旧格式 (x/y/w/h/i) 和新格式 (id/w/h/hidden)
      if (Array.isArray(p) && p.length && p[0].id) {
        // 新格式：确保所有 card 都有必需字段
        return p.map(c => ({ id: c.id, w: c.w || 1, h: c.h || 1, hidden: !!c.hidden, order: c.order || 0 }))
      }
    }
  } catch {}
  return allCards.map(c => ({ ...c, w: c.defaultW, h: c.defaultH, hidden: false, order: 0 }))
}
const cards = ref(loadCards())

function save() {
  localStorage.setItem(KEY, JSON.stringify(cards.value.map(c => ({ id:c.id, w:c.w, h:c.h, hidden:c.hidden, order:c.order }))))
}

function cardStyle(c) {
  if (c.hidden && !editing.value) return { display: 'none' }
  const h = editing.value ? c.h * 140 + (c.h - 1) * 16 : c.h * 120 + (c.h - 1) * 16
  return {
    gridColumn: `span ${c.w}`,
    minHeight: `${h}px`,
    opacity: c.hidden ? 0.3 : 1,
    order: c.order || 0,
  }
}

function toggleCard(id) {
  const c = cards.value.find(x => x.id === id)
  if (c) c.hidden = !c.hidden
  save()
}

function applySize() {
  if (!selected.value) return
  const c = cards.value.find(x => x.id === selected.value)
  if (c) { c.w = sizeW.value; c.h = sizeH.value }
  save()
  nextTick(() => { if (selected.value === 'chart') renderChart() })
}

function sbg(r, id) {
  if (id === 'smb' || id === 'nmb') return `background:${r?'#e8f8e8':'#fde8e8'}`
  return ''
}

function selectCard(id) {
  selected.value = id
  const c = cards.value.find(x => x.id === id)
  if (c) { sizeW.value = c.w; sizeH.value = c.h }
}

// ---- 拖拽 ----
let dragTarget = null
let dragStartX = 0, dragStartY = 0

function startDrag(ev, card) {
  dragTarget = card
  dragStartX = ev.clientX
  dragStartY = ev.clientY
  document.addEventListener('mousemove', onDrag)
  document.addEventListener('mouseup', stopDrag)
}

function onDrag(ev) {
  if (!dragTarget) return
  const dx = ev.clientX - dragStartX
  if (Math.abs(dx) > 30) {
    const dir = dx > 0 ? 1 : -1
    const siblings = cards.value.filter(c => !c.hidden && c.id !== dragTarget.id)
    const curOrder = dragTarget.order || 0
    const targetOrder = curOrder + dir
    const swap = siblings.find(c => (c.order || 0) === targetOrder)
    if (swap) {
      swap.order = curOrder
      dragTarget.order = targetOrder
    }
    dragStartX = ev.clientX
    save()
  }
}

function stopDrag() {
  dragTarget = null
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
}

// ---- 数据加载 ----
async function loadOverview() {
  cardLoading.smb = true
  cardLoading.nmb = true
  cardLoading.sessions = true
  cardLoading.shares = true
  try {
    const res = await dashboardApi.overview()
    Object.assign(o, res.data)
    loadError.value = ''
  } catch (e) {
    if (e?.response?.status !== 404) {
      loadError.value = '加载概览数据失败，请检查服务器连接'
    }
  } finally {
    cardLoading.smb = false
    cardLoading.nmb = false
    cardLoading.sessions = false
    cardLoading.shares = false
  }
}

async function loadAudit() {
  auditError.value = ''
  try {
    const res = await dashboardApi.auditLogs(20)
    auditLogs.value = res.data.logs || []
  } catch {
    auditError.value = '加载操作记录失败'
  }
}

async function loadTopShares() {
  try {
    const res = await dashboardApi.topShares()
    topShares.value = res.data.top || []
  } catch {
    // non-critical, silently degrade
  }
}

function initChart() {
  if (chartInstance && chartInstance.isDisposed?.()) chartInstance = null
  if (chartInstance) return true
  if (!chartRef.value || chartRef.value.offsetWidth === 0) return false
  try {
    chartInstance = echarts.init(chartRef.value)
    return true
  } catch (e) {
    console.warn('chart init error:', e)
    return false
  }
}

async function loadChart(retries = 5) {
  if (!chartRef.value) return
  if (!initChart()) {
    if (retries > 0 && !chartLoadAttempted) {
      chartLoadAttempted = true
      setTimeout(() => { chartLoadAttempted = false; loadChart(retries - 1) }, 800)
    }
    return
  }
  try {
    const res = await dashboardApi.sessionHistory(chartHours.value)
    const sessions = res.data.sessions || []
    chartInstance.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: 50, right: 20, top: 30, bottom: 30 },
      xAxis: {
        type: 'category',
        data: sessions.map(s => s.time),
        axisLabel: { fontSize: 10, rotate: sessions.length > 30 ? 45 : 0 },
      },
      yAxis: { type: 'value', minInterval: 1 },
      series: [{
        type: 'line',
        data: sessions.map(s => s.count),
        smooth: true,
        lineStyle: { color: '#409eff', width: 2 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(64,158,255,0.3)' },
            { offset: 1, color: 'rgba(64,158,255,0.02)' },
          ]),
        },
        itemStyle: { color: '#409eff' },
      }],
    })
    chartInstance.resize()
  } catch {
    // chart silently degrades
  }
}

function renderChart() {
  chartLoadAttempted = false
  loadChart(5)
}

async function refreshAll() {
  if (!server.selectedId) return
  loading.value = true
  loadError.value = ''
  auditError.value = ''
  try {
    await Promise.all([loadOverview(), loadAudit(), loadTopShares()])
    renderChart()
    lastRefreshTime.value = new Date().toLocaleTimeString('zh-CN', { hour12: false })
  } catch {
    // global interceptor handles
  } finally {
    loading.value = false
  }
}

// ---- 自动刷新 ----
function onRefreshIntervalChange(val) {
  if (refreshTimer) { clearInterval(refreshTimer); refreshTimer = null }
  if (val > 0) {
    refreshTimer = setInterval(() => {
      if (server.selectedId) refreshAll()
    }, val * 1000)
  }
}

function startAutoRefresh() {
  if (refreshInterval.value > 0) {
    refreshTimer = setInterval(() => {
      if (server.selectedId) refreshAll()
    }, refreshInterval.value * 1000)
  }
}

function resetLayout() {
  cards.value = allCards.map(c => ({ ...c, w: c.defaultW, h: c.defaultH, hidden: false, order: 0 }))
  localStorage.removeItem(KEY)
  selected.value = null
  nextTick(() => renderChart())
}

function resize() { chartInstance?.resize() }

onMounted(async () => {
  if (!server.selectedId) return
  loading.value = true
  try {
    await Promise.all([loadOverview(), loadAudit(), loadTopShares()])
    lastRefreshTime.value = new Date().toLocaleTimeString('zh-CN', { hour12: false })
  } catch {} finally {
    loading.value = false
  }
  await nextTick()
  // chartRef 是 computed，会自动获取 .chart-container
  // 延迟等 DOM 渲染完成
  setTimeout(() => loadChart(5), 1000)
  startAutoRefresh()
  window.addEventListener('resize', resize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  chartInstance?.dispose()
  if (refreshTimer) clearInterval(refreshTimer)
})
</script>

<style scoped>
.dash-header { display:flex; align-items:center; justify-content:space-between; margin-bottom:20px; flex-wrap:wrap; gap:8px; }
.dash-actions { display:flex; align-items:center; gap:8px; flex-wrap:wrap; }
.last-refresh { font-size:12px; color:#909399; white-space:nowrap; }

.edit-toolbar { display:flex; align-items:center; gap:16px; margin-bottom:12px; padding:8px 16px; background:#fdf6ec; border-radius:6px; font-size:13px; color:#e6a23c; }
.edit-hint { margin-left:auto; }

/* 响应式网格 */
.grid-container {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
  min-height: 400px;
}

/* 宽卡片占 2 列 */
.grid-card { position:relative; transition: all 0.2s; }
.grid-card.editing { cursor:pointer; border-radius:8px; min-height:100px; }
.grid-card.editing:hover { box-shadow:0 0 0 2px #409eff; }
.grid-card.selected { box-shadow:0 0 0 3px #409eff, 0 4px 12px rgba(64,158,255,0.3); }
.grid-card.card-loading { opacity:0.7; }
.grid-card :deep(.el-card__body) { overflow-y:auto; }

.card-drag-handle { position:absolute; top:4px; right:4px; z-index:10; width:28px; height:28px; display:flex; align-items:center; justify-content:center; background:rgba(64,158,255,0.15); border-radius:4px; cursor:grab; }
.card-close { position:absolute; top:4px; left:4px; z-index:10; width:24px; height:24px; display:flex; align-items:center; justify-content:center; background:rgba(245,108,108,0.15); border-radius:4px; cursor:pointer; }

.fill-card { height:100%; width:100%; }

/* 统计卡片 */
.stat-card { display:flex; align-items:center; gap:16px; height:100%; }
.stat-icon { width:52px; height:52px; border-radius:8px; display:flex; align-items:center; justify-content:center; }
.stat-value { font-size:22px; font-weight:600; color:#303133; }
.stat-label { font-size:13px; color:#909399; margin-top:2px; }

/* 卡片头部 */
.card-header-row { display:flex; align-items:center; justify-content:space-between; width:100%; }

/* 磁盘 IO 卡片 */
.diskio-list { display:flex; flex-direction:column; gap:12px; }
.diskio-device { border-bottom:1px solid #ebeef5; padding-bottom:8px; }
.diskio-device:last-child { border-bottom:none; padding-bottom:0; }
.diskio-name { font-weight:600; font-size:14px; margin-bottom:6px; color:#303133; }
.diskio-metrics { display:grid; grid-template-columns:1fr 1fr; gap:6px; }
.diskio-metric { display:flex; align-items:center; gap:4px; font-size:13px; }
.diskio-label { color:#909399; width:22px; }
.diskio-val { font-weight:600; color:#303133; }
.diskio-val.read { color:#409eff; }
.diskio-val.write { color:#67c23a; }

/* 热门共享 */
.top-item { display:flex; align-items:center; gap:12px; padding:6px 8px; border-radius:6px; border:1px solid #ebeef5; margin-bottom:4px; }
.top-rank { font-size:16px; font-weight:700; color:#409eff; width:32px; }
.top-name { flex:1; font-weight:500; }
.top-size { color:#909399; font-size:13px; }
.top-count { color:#67c23a; font-weight:600; }

/* 快捷操作 */
.short-grid { display:grid; grid-template-columns:1fr 1fr; gap:8px; }
.short-grid .el-button { width:100%; }

/* 尺寸面板 */
.size-panel { display:flex; align-items:center; margin-top:16px; padding:12px 16px; background:#f5f7fa; border-radius:8px; flex-wrap:wrap; gap:8px; }
.size-label { font-size:13px; color:#606266; white-space:nowrap; }

/* 错误状态 */
.card-error { display:flex; flex-direction:column; align-items:center; justify-content:center; gap:8px; padding:20px; color:#909399; }

/* 响应式 */
@media (max-width: 768px) {
  .grid-container { grid-template-columns: 1fr; }
  .dash-header { flex-direction:column; align-items:flex-start; }
  .dash-actions { width:100%; }
}
</style>
