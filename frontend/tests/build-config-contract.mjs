import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const testDir = dirname(fileURLToPath(import.meta.url))
const root = resolve(testDir, '..')
const viteConfig = readFileSync(resolve(root, 'vite.config.ts'), 'utf8')

assert.match(
  viteConfig,
  /manualChunks/,
  'Vite build should split stable vendor dependencies into named chunks'
)
assert.match(
  viteConfig,
  /vendor-element-plus/,
  'Element Plus should be isolated from the main application chunk'
)
assert.match(
  viteConfig,
  /vendor-vue/,
  'Vue runtime libraries should be isolated from the main application chunk'
)
assert.match(
  viteConfig,
  /chunkSizeWarningLimit:\s*1000/,
  'Chunk size warning limit should reflect the intentionally full Element Plus dependency'
)
assert.match(
  viteConfig,
  /warning\.code\s*===\s*'INVALID_ANNOTATION'/,
  'Build should handle Rollup invalid annotation warnings explicitly'
)
assert.match(
  viteConfig,
  /@vueuse\/core/,
  'Only the known @vueuse/core annotation warning should be filtered'
)
assert.match(
  viteConfig,
  /warn\(warning\)/,
  'Unrelated Rollup warnings should still be reported'
)
