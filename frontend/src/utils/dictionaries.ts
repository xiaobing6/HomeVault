import type { ConfigBootstrap, DictionaryOption } from '../api/configuration'

export function dictionaryOptions(
  data: ConfigBootstrap | null | undefined,
  groupCode: string,
  includeInactive = false
): DictionaryOption[] {
  const group = data?.dictionary_groups.find((item) => item.code === groupCode)
  return (group?.options ?? [])
    .filter((option) => includeInactive || option.is_active)
    .slice()
    .sort((first, second) => first.sort_order - second.sort_order || first.id - second.id)
}

export function dictionaryLabel(
  data: ConfigBootstrap | null | undefined,
  groupCode: string,
  value: string | null | undefined
): string {
  if (!value) return '-'
  return dictionaryOptions(data, groupCode, true).find((option) => option.value === value)?.label ?? value
}
