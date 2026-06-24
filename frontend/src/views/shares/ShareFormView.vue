<template>
  <div class="page-container">
    <el-page-header @back="$router.push('/shares')">
      <template #content><h3>{{ isEdit ? '编辑共享' : '新增共享' }}</h3></template>
    </el-page-header>

    <el-card style="max-width: 640px; margin: 20px 0">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="110px">
        <el-form-item label="共享名" prop="name">
          <el-input v-model="form.name" :disabled="isEdit" placeholder="如: design_dept" />
        </el-form-item>
        <el-form-item label="备注" prop="comment">
          <el-input v-model="form.comment" placeholder="如: 设计部" />
        </el-form-item>
        <el-form-item label="路径" prop="path">
          <el-input v-model="form.path" placeholder="如: /data/samba/design_dept" />
        </el-form-item>
        <el-form-item label="授权群组" prop="valid_users">
          <el-input v-model="form.valid_users" placeholder="如: @smb_design, @smb_admin_group" />
        </el-form-item>
        <el-form-item label="管理员" prop="admin_users">
          <el-input v-model="form.admin_users" placeholder="如: zhangsan, sys_admin" />
        </el-form-item>
        <el-form-item label="权限模式">
          <el-radio-group v-model="form.writable">
            <el-radio label="yes">读写</el-radio>
            <el-radio label="no">只读</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="浏览权限">
          <el-radio-group v-model="form.browseable">
            <el-radio label="yes">可见</el-radio>
            <el-radio label="no">隐藏</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="saving" @click="handleSave">
            {{ isEdit ? '保存修改' : '创建共享' }}
          </el-button>
          <el-button @click="$router.push('/shares')">取消</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { sharesApi } from '@/api/shares'
import { ElMessage } from 'element-plus'
import { useServerStore } from '@/stores/server'

const router = useRouter()
const route = useRoute()
const serverStore = useServerStore()
const isEdit = route.name === 'ShareEdit'
const formRef = ref(null)
const saving = ref(false)

const form = reactive({
  name: '',
  comment: '',
  path: '',
  valid_users: '',
  admin_users: '',
  writable: 'yes',
  browseable: 'yes',
  create_mask: '0777',
  directory_mask: '0777',
})

const rules = {
  name: [{ required: true, message: '请输入共享名', trigger: 'blur' }],
  path: [{ required: true, message: '请输入路径', trigger: 'blur' }],
}

onMounted(async () => {
  if (!isEdit) return
  try {
    const res = await sharesApi.get(route.params.name)
    Object.assign(form, res.data)
  } catch { /* handled */ }
})

async function handleSave() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    if (isEdit) {
      await sharesApi.update(form.name, { ...form })
      ElMessage.success('修改已保存')
    } else {
      await sharesApi.create({ ...form })
      ElMessage.success('共享已创建')
    }
    router.push('/shares')
  } catch { /* handled */ } finally {
    saving.value = false
  }
}
</script>
