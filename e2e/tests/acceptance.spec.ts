import { expect, type Page, test } from '@playwright/test'

async function loginAsAdmin(page: Page) {
  await page.goto('/')
  await page.getByPlaceholder('账号').fill('admin')
  await page.getByPlaceholder('密码').fill('ChangeMe123!')
  await page.getByRole('button', { name: '登录' }).click()
  await expect(page.getByRole('heading', { name: '仪表盘' })).toBeVisible()
  await page.getByText('登录成功').waitFor({ state: 'hidden', timeout: 5000 }).catch(() => {})
}

async function openNav(page: Page, name: string) {
  await page.getByText(name, { exact: true }).click()
}

test.describe.serial('HomeVault browser acceptance baseline', () => {
  test('admin can reach configuration, inventory import/export, and bulk surfaces', async ({ page }) => {
    await loginAsAdmin(page)

    await openNav(page, '后台管理')
    await expect(page.getByRole('heading', { name: '核心配置' })).toBeVisible()
    await expect(page.getByText('住宅与位置')).toBeVisible()
    await expect(page.getByText('分类字段')).toBeVisible()
    await page.getByText('状态与字典').click()
    await expect(page.getByRole('heading', { name: '字典' })).toBeVisible()
    await expect(page.getByText('重要程度')).toBeVisible()

    await openNav(page, '物品')
    await expect(page.getByRole('heading', { name: '物品' })).toBeVisible()
    await expect(page.getByText('E2E Passport Folder')).toBeVisible()

    await page.getByText('表格').click()
    await expect(page.locator('.el-table__row').filter({ hasText: 'E2E Passport Folder' })).toBeVisible()
    await page.locator('.el-table__body-wrapper .el-checkbox').first().click()
    await page.getByRole('button', { name: /批量/ }).click()
    await expect(page.getByText('批量移动')).toBeVisible()
    await expect(page.getByText('批量改状态')).toBeVisible()
    await page.keyboard.press('Escape')

    await page.getByRole('button', { name: '导出' }).click()
    await expect(page.getByText('导出当前筛选')).toBeVisible()
    await expect(page.getByText('导出已选')).toBeVisible()
    await page.keyboard.press('Escape')

    await page.getByRole('button', { name: '导入' }).click()
    const importDialog = page.getByRole('dialog', { name: '导入物品' })
    await expect(importDialog).toBeVisible()
    await expect(importDialog.getByRole('button', { name: /下载模板/ })).toBeVisible()
    await expect(importDialog.locator('button').filter({ hasText: '选择 CSV' })).toBeVisible()
    await page.getByRole('button', { name: '取消' }).click()
  })

  test('admin can create a reminder and inspect audit logs', async ({ page }) => {
    await loginAsAdmin(page)

    await openNav(page, '提醒')
    await expect(page.getByRole('heading', { name: '提醒中心' })).toBeVisible()
    await page.getByRole('button', { name: '新增提醒' }).click()

    const title = `E2E Manual Reminder ${Date.now()}`
    const dialog = page.getByRole('dialog', { name: '新增提醒' })
    await expect(dialog).toBeVisible()
    await dialog.locator('input').first().fill(title)
    await dialog.getByRole('button', { name: '保存' }).click()

    await expect(page.getByText('提醒已保存')).toBeVisible()
    await expect(page.getByRole('heading', { name: title })).toBeVisible()
    await page.keyboard.press('Escape')

    await openNav(page, '操作日志')
    await expect(page.getByRole('heading', { name: '操作日志' })).toBeVisible()
    await expect(page.getByText('auth.login').first()).toBeVisible()
    await expect(page.getByText('admin').first()).toBeVisible()
  })
})
