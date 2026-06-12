import { useCrudTable } from './useCrudTable'
import { classService } from '~/services/classService'
import type { TableQuery } from '~/types/api'
import type { ClassPayload, ClassRow, ClassUpdatePayload } from '~/types/class'

export function useClasses(initialQuery: TableQuery = {}) {
  return useCrudTable<ClassRow, ClassPayload, ClassUpdatePayload>(classService, initialQuery)
}
