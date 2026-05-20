import { reactive, ref, shallowRef } from 'vue'
import type { CrudService, Id, TableQuery } from '~/types/api'

export function useCrudTable<TRow, TCreate, TUpdate = Partial<TCreate>>(
  service: CrudService<TRow, TCreate, TUpdate>,
  initialQuery: TableQuery = {}
) {
  const rows = shallowRef<TRow[]>([])
  const total = ref(0)
  const loading = ref(false)
  const error = ref<unknown>(null)
  const query = reactive<TableQuery>({
    page: 1,
    limit: 10,
    sortOrder: 'desc',
    ...initialQuery
  })

  async function fetchList(nextQuery: TableQuery = {}) {
    Object.assign(query, nextQuery)
    loading.value = true
    error.value = null

    try {
      const response = await service.list({ ...query })
      rows.value = response.data
      total.value = response.total
      return response
    } catch (caught) {
      error.value = caught
      throw caught
    } finally {
      loading.value = false
    }
  }

  async function create(payload: TCreate) {
    const row = await service.create(payload)
    await fetchList()
    return row
  }

  async function update(id: Id, payload: TUpdate) {
    const row = await service.update(id, payload)
    await fetchList()
    return row
  }

  async function remove(id: Id) {
    const response = await service.remove(id)
    await fetchList()
    return response
  }

  return {
    rows,
    total,
    loading,
    error,
    query,
    fetchList,
    create,
    update,
    remove
  }
}
