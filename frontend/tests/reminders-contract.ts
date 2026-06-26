import {
  archiveReminderApi,
  completeReminderApi,
  createReminderApi,
  dismissReminderApi,
  fetchReminderDetailApi,
  listRemindersApi,
  reopenReminderApi,
  updateReminderApi,
  type ReminderCreateRequest,
  type ReminderDetail,
  type ReminderFilters,
  type ReminderListResponse,
  type ReminderUpdateRequest
} from '../src/api/reminders'
import { useReminderStore } from '../src/stores/reminders'

function expectType<T>(_value: T): void {}

async function assertReminderApiContract() {
  const filters: ReminderFilters = {
    status: 'pending',
    source_type: 'manual',
    item_id: 1,
    loan_id: null,
    overdue: false,
    upcoming_days: 7,
    include_archived: false,
    search: 'passport',
    sort: 'due_asc',
    page: 1,
    page_size: 20
  }

  const createPayload: ReminderCreateRequest = {
    title: 'Check passport',
    description: '',
    item_id: 1,
    due_date: '2026-06-21',
    remind_at: '2026-06-20',
    priority: 'high'
  }

  const updatePayload: ReminderUpdateRequest = {
    title: 'Check passport folder',
    description: null,
    item_id: null,
    due_date: null,
    remind_at: null,
    priority: 'normal'
  }

  expectType<ReminderListResponse>(await listRemindersApi(filters))
  expectType<ReminderDetail>(await createReminderApi(createPayload))
  expectType<ReminderDetail>(await fetchReminderDetailApi(1))
  expectType<ReminderDetail>(await updateReminderApi(1, updatePayload))
  expectType<ReminderDetail>(await completeReminderApi(1))
  expectType<ReminderDetail>(await dismissReminderApi(1))
  expectType<ReminderDetail>(await reopenReminderApi(1))
  expectType<ReminderDetail>(await archiveReminderApi(1))
}

async function assertReminderStoreContract() {
  const reminders = useReminderStore()

  expectType<ReminderFilters>(reminders.filters)
  expectType<ReminderDetail | null>(reminders.selectedReminder)

  await reminders.loadReminders({ overdue: true })
  await reminders.openDetail(1)
  reminders.applyFilters({ status: 'pending' })
  reminders.setPage(2)
  reminders.setPageSize(50)
  reminders.resetFilters()
  reminders.closeDetail()

  expectType<ReminderDetail>(await reminders.createReminder({ title: 'Check passport' }))
  expectType<ReminderDetail>(await reminders.updateReminder(1, { priority: 'low' }))
  expectType<ReminderDetail>(await reminders.completeReminder(1))
  expectType<ReminderDetail>(await reminders.dismissReminder(1))
  expectType<ReminderDetail>(await reminders.reopenReminder(1))
  expectType<ReminderDetail>(await reminders.archiveReminder(1))
  expectType<ReminderDetail>(await reminders.saveAndRefresh(() => fetchReminderDetailApi(1)))
}

void assertReminderApiContract
void assertReminderStoreContract
