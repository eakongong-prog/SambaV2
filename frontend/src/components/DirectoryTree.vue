<template>
  <el-tree
    :data="treeData"
    :props="treeProps"
    node-key="path"
    :load="loadChildren"
    lazy
    highlight-current
    @node-click="handleNodeClick"
  />
</template>

<script setup>
import { ref } from 'vue'
import { permissionsApi } from '@/api/permissions'

const emit = defineEmits(['node-click'])

const props = defineProps({
  share: { type: String, default: '' },
})

const treeProps = { label: 'name', children: 'children', isLeaf: 'isLeaf' }

async function loadChildren(node, resolve) {
  const path = node.data?.path || ''
  try {
    const res = await permissionsApi.tree(props.share, path)
    const items = res.data.map(item => ({
      name: item.name,
      path: item.path,
      isLeaf: !item.is_dir,
    }))
    resolve(items)
  } catch {
    resolve([])
  }
}

function handleNodeClick(data) {
  emit('node-click', data)
}
</script>
