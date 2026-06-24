/**
 * 格式化工具函数
 */
export function formatFileSize(bytes) {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let i = 0
  let size = bytes
  while (size >= 1024 && i < units.length - 1) {
    size /= 1024
    i++
  }
  return `${size.toFixed(i === 0 ? 0 : 1)} ${units[i]}`
}

export function formatDateTime(dateStr) {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  return d.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

export function formatDuration(seconds) {
  if (!seconds) return '0秒'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = seconds % 60
  const parts = []
  if (h > 0) parts.push(`${h}小时`)
  if (m > 0) parts.push(`${m}分钟`)
  if (s > 0 || parts.length === 0) parts.push(`${s}秒`)
  return parts.join('')
}

/**
 * 格式化磁盘 IO 速率
 * @param {number} mbPerSec — 速率，单位 MB/s
 */
export function formatSpeed(mbPerSec) {
  if (mbPerSec === null || mbPerSec === undefined) return '-'
  if (mbPerSec >= 1000) {
    return `${(mbPerSec / 1000).toFixed(1)} GB/s`
  }
  if (mbPerSec >= 1) {
    return `${mbPerSec.toFixed(1)} MB/s`
  }
  if (mbPerSec >= 0.001) {
    return `${(mbPerSec * 1000).toFixed(0)} KB/s`
  }
  return '0 MB/s'
}
