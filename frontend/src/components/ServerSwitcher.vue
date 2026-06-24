<template>
  <div class="server-switcher">
    <el-select
      v-model="server.selectedId"
      placeholder="选择服务器"
      size="default"
      style="width: 220px"
      @change="handleSelect"
      :loading="loading"
    >
      <el-option
        v-for="s in servers"
        :key="s.id"
        :label="`${s.name} (${s.host})`"
        :value="s.id"
      >
        <span style="float: left">{{ s.name }}</span>
        <span style="float: right; color: #909399; font-size: 13px">
          <el-icon v-if="s.is_connected" style="color: #67c23a"><CircleCheckFilled /></el-icon>
          <el-icon v-else style="color: #c0c4cc"><CircleCheck /></el-icon>
          {{ s.host }}
        </span>
      </el-option>
    </el-select>
    <el-button v-if="!server.selectedId" @click="$router.push('/servers/add')" type="primary" size="small">
      <el-icon><Plus /></el-icon> 添加服务器
    </el-button>
    <el-button v-else @click="$router.push('/servers')" size="small">
      <el-icon><Setting /></el-icon>
    </el-button>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useServerStore } from '@/stores/server'
import { serversApi } from '@/api/servers'
import { ElMessage } from 'element-plus'

const server = useServerStore()
const servers = ref([])
const loading = ref(false)

async function loadServers() {
  loading.value = true
  try {
    const res = await serversApi.list()
    servers.value = res.data
    // 若已选服务器不在列表中则清空
    if (server.selectedId && !servers.value.find(s => s.id === server.selectedId)) {
      server.clear()
    }
  } catch {
    // interceptor handles
  } finally {
    loading.value = false
  }
}

function handleSelect(id) {
  const s = servers.value.find(s => s.id === id)
  if (s) {
    server.selectServer(id, s.name)
    ElMessage.success(`已连接到 ${s.name}`)
  }
}

onMounted(loadServers)

// 当路由变化时（如添加/删除服务器），刷新列表
watch(() => servers.value.length, loadServers)
</script>

<style scoped>
.server-switcher {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
