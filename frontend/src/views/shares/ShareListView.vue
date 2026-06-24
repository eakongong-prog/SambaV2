<template>
  <div class="page-container">
    <div class="toolbar">
      <h2>共享管理</h2>
      <div class="spacer" />
      <el-button type="primary" @click="$router.push('/shares/add')">
        <el-icon><Plus /></el-icon> 新增共享
      </el-button>
    </div>
    <el-alert
      v-if="!serverStore.selectedId"
      type="warning"
      title="请先在顶部选择一台 Samba 服务器"
      :closable="false"
      show-icon
      style="margin-bottom: 16px"
    />
    <el-table :data="shares" v-loading="loading" stripe>
      <el-table-column prop="name" label="共享名" min-width="140" sortable>
        <template #default="{ row }">
          <strong>{{ row.name }}</strong>
        </template>
      </el-table-column>
      <el-table-column prop="path" label="路径" min-width="200">
        <template #default="{ row }">
          <el-tag type="info" size="small" effect="plain">{{ row.path }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="valid_users" label="授权群组" min-width="180">
        <template #default="{ row }">
          <el-tag
            v-for="v in (row.valid_users || '').replace(/@/g, '').split(/\s+/).filter(Boolean).filter(g => g !== 'smb_admin_group')"
            :key="v" size="small" style="margin: 2px">{{ v }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="admin_users" label="管理员" min-width="150">
        <template #default="{ row }">
          <el-tag
            v-for="v in (row.admin_users || '').split(/\s+/).filter(Boolean).filter(u => u !== 'sys_admin')"
            :key="v" size="small" type="warning" style="margin: 2px">{{ v }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="writable" label="权限" width="80" align="center">
        <template #default="{ row }">
          <el-tag :type="row.writable === 'yes' ? 'success' : 'warning'" size="small">
            {{ row.writable === 'yes' ? '读写' : '只读' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="browseable" label="可见" width="70" align="center">
        <template #default="{ row }">
          <el-tag :type="row.browseable === 'yes' ? 'success' : 'info'" size="small">{{ row.browseable === 'yes' ? '是' : '否' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click="$router.push(`/permissions?share=${row.name}`)">权限</el-button>
          <el-popconfirm title="确定删除此共享？" @confirm="handleDelete(row.name)">
            <template #reference>
              <el-button link type="danger" size="small">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-if="!loading && shares.length === 0 && serverStore.selectedId" description="暂无共享，请点击右上角新增" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useServerStore } from '@/stores/server'
import { sharesApi } from '@/api/shares'
import { ElMessage } from 'element-plus'

const serverStore = useServerStore()
const loading = ref(false)
const shares = ref([])

async function load() {
  if (!serverStore.selectedId) return
  loading.value = true
  try {
    const res = await sharesApi.list()
    shares.value = res.data.shares || []
  } catch { /* handled */ } finally {
    loading.value = false
  }
}

async function handleDelete(name) {
  try {
    await sharesApi.delete(name)
    ElMessage.success('已删除')
    load()
  } catch { /* handled */ }
}

onMounted(load)
</script>
