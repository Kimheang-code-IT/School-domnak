export function fileToDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result || ''))
    reader.onerror = () => reject(reader.error ?? new Error('read failed'))
    reader.readAsDataURL(file)
  })
}

export function resolveFirstUploadFile(value: unknown): File | null {
  if (!value) return null
  if (value instanceof File) return value
  if (Array.isArray(value) && value.length > 0) {
    const first = value[0] as { file?: File } | File
    if (first instanceof File) return first
    if (first && typeof first === 'object' && first.file instanceof File) return first.file
  }
  const record = value as { file?: File }
  if (record?.file instanceof File) return record.file
  return null
}
