import { useCrudTable } from './useCrudTable'
import { courseService } from '~/services/courseService'
import type { CoursePayload, CourseRow, TableQuery } from '~/types/api'

export function useCoursesApiTable(initialQuery: TableQuery = {}) {
  return useCrudTable<CourseRow, CoursePayload>(courseService, initialQuery)
}
