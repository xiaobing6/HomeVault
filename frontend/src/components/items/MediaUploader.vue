<script setup lang="ts">
import { Picture, Paperclip, Plus, UploadFilled } from '@element-plus/icons-vue'
import type { UploadFile } from 'element-plus'

import type { ItemAttachment, ItemImage } from '../../api/inventory'

const props = withDefaults(defineProps<{
  images?: ItemImage[]
  attachments?: ItemAttachment[]
  imageFiles: File[]
  attachmentFiles: File[]
  editable?: boolean
}>(), {
  images: () => [],
  attachments: () => [],
  editable: true
})

const emit = defineEmits<{
  'update:imageFiles': [value: File[]]
  'update:attachmentFiles': [value: File[]]
}>()

function addImageFile(uploadFile: UploadFile) {
  const rawFile = uploadFile.raw
  if (!rawFile) return
  emit('update:imageFiles', [...props.imageFiles, rawFile])
}

function addAttachmentFile(uploadFile: UploadFile) {
  const rawFile = uploadFile.raw
  if (!rawFile) return
  emit('update:attachmentFiles', [...props.attachmentFiles, rawFile])
}

function removeImageFile(index: number) {
  emit('update:imageFiles', props.imageFiles.filter((_file, fileIndex) => fileIndex !== index))
}

function removeAttachmentFile(index: number) {
  emit(
    'update:attachmentFiles',
    props.attachmentFiles.filter((_file, fileIndex) => fileIndex !== index)
  )
}

function formatSize(size: number): string {
  if (!Number.isFinite(size) || size <= 0) return ''
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / 1024 / 1024).toFixed(1)} MB`
}
</script>

<template>
  <div class="media-uploader">
    <section class="media-section">
      <div class="section-heading">
        <el-icon><Picture /></el-icon>
        <span>图片</span>
      </div>

      <div v-if="images.length > 0" class="image-grid">
        <a
          v-for="image in images"
          :key="image.id"
          class="image-preview"
          :href="image.url || undefined"
          target="_blank"
          rel="noreferrer"
        >
          <img v-if="image.url" :src="image.url" :alt="image.original_filename" />
          <el-icon v-else><Picture /></el-icon>
          <el-tag v-if="image.is_primary" size="small" type="success">主图</el-tag>
        </a>
      </div>
      <el-empty v-else description="暂无图片" :image-size="64" />

      <div v-if="editable" class="upload-row">
        <el-upload
          accept="image/*"
          :auto-upload="false"
          :show-file-list="false"
          multiple
          :on-change="addImageFile"
        >
          <el-button :icon="Plus">选择图片</el-button>
        </el-upload>
      </div>

      <div v-if="imageFiles.length > 0" class="pending-list">
        <el-tag
          v-for="(file, index) in imageFiles"
          :key="`${file.name}-${index}`"
          closable
          type="success"
          @close="removeImageFile(index)"
        >
          {{ file.name }}
        </el-tag>
      </div>
    </section>

    <section class="media-section">
      <div class="section-heading">
        <el-icon><Paperclip /></el-icon>
        <span>附件</span>
      </div>

      <div v-if="attachments.length > 0" class="attachment-list">
        <div v-for="attachment in attachments" :key="attachment.id" class="attachment-item">
          <el-icon><UploadFilled /></el-icon>
          <a
            v-if="attachment.download_url"
            :href="attachment.download_url"
            target="_blank"
            rel="noreferrer"
          >
            {{ attachment.original_filename }}
          </a>
          <span v-else>{{ attachment.original_filename }}</span>
          <small>{{ formatSize(attachment.byte_size) }}</small>
        </div>
      </div>
      <el-empty v-else description="暂无附件" :image-size="64" />

      <div v-if="editable" class="upload-row">
        <el-upload
          :auto-upload="false"
          :show-file-list="false"
          multiple
          :on-change="addAttachmentFile"
        >
          <el-button :icon="Plus">选择附件</el-button>
        </el-upload>
      </div>

      <div v-if="attachmentFiles.length > 0" class="pending-list">
        <el-tag
          v-for="(file, index) in attachmentFiles"
          :key="`${file.name}-${index}`"
          closable
          @close="removeAttachmentFile(index)"
        >
          {{ file.name }}
        </el-tag>
      </div>
    </section>
  </div>
</template>

<style scoped>
.media-uploader {
  display: grid;
  gap: 18px;
  min-width: 0;
}

.media-section {
  display: grid;
  gap: 10px;
  min-width: 0;
}

.section-heading {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #26342e;
  font-weight: 700;
}

.image-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(112px, 1fr));
  gap: 10px;
}

.image-preview {
  position: relative;
  display: grid;
  aspect-ratio: 1;
  place-items: center;
  overflow: hidden;
  color: #779182;
  background: #eef5ef;
  border: 1px solid #dce8de;
  border-radius: 8px;
}

.image-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.image-preview .el-tag {
  position: absolute;
  right: 6px;
  bottom: 6px;
}

.attachment-list,
.pending-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  min-width: 0;
}

.attachment-list {
  display: grid;
}

.attachment-item {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  padding: 8px 10px;
  background: #f7faf6;
  border: 1px solid #e2e8df;
  border-radius: 6px;
}

.attachment-item a,
.attachment-item span {
  min-width: 0;
  overflow: hidden;
  color: #25342d;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.attachment-item small {
  flex: 0 0 auto;
  color: #7c8a80;
}

.upload-row {
  display: flex;
}
</style>
