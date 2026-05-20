import { useCrudTable } from './useCrudTable'
import { studentService } from '~/services/studentService'
import type { TableQuery } from '~/types/api'
import type { StudentPayload, StudentRow, StudentUpdatePayload } from '~/types/student'

export function useStudents(initialQuery: TableQuery = {}) {
  return useCrudTable<StudentRow, StudentPayload, StudentUpdatePayload>(studentService, initialQuery)
}
