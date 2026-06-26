import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const testDir = dirname(fileURLToPath(import.meta.url))
const root = resolve(testDir, '..')

function readSource(relativePath) {
  return readFileSync(resolve(root, relativePath), 'utf8')
}

const reminderDetailModal = readSource('src/components/reminders/ReminderDetailModal.vue')
const reminderCenterPage = readSource('src/pages/ReminderCenterPage.vue')
const itemsPage = readSource('src/pages/ItemsPage.vue')

assert.match(
  reminderDetailModal,
  /'open-item': \[itemId: number\]/,
  'ReminderDetailModal should expose an open-item event with the linked item id'
)
assert.match(
  reminderDetailModal,
  /emit\('open-item', reminder\.item_id\)/,
  'ReminderDetailModal should emit open-item when the linked item action is clicked'
)
assert.match(
  reminderCenterPage,
  /@open-item="openLinkedItem"/,
  'ReminderCenterPage should wire the reminder detail linked-item action'
)
assert.match(
  reminderCenterPage,
  /router\.push\(\{\s*name: 'items'[\s\S]*item_id: String\(itemId\)/,
  'ReminderCenterPage should navigate to the item workbench with the linked item id'
)
assert.match(
  reminderCenterPage,
  /if \(action === 'archive'\) closeDetail\(\)/,
  'ReminderCenterPage should close the detail modal after a successful archive'
)
assert.match(
  itemsPage,
  /const route = useRoute\(\)/,
  'ItemsPage should read the current route so linked reminder navigation can open item detail'
)
assert.match(
  itemsPage,
  /route\.query\.item_id/,
  'ItemsPage should consume the item_id query parameter'
)
assert.match(
  itemsPage,
  /watch\(\s*\(\) => route\.query\.item_id/,
  'ItemsPage should respond when item_id changes while the page stays mounted'
)
