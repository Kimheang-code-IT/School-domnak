import { ref } from 'vue'

export function usePosPrint() {
  const isFinishDialogOpen = ref(false)

  function openPrintDialog() {
    isFinishDialogOpen.value = true
  }

  function closePrintDialog() {
    isFinishDialogOpen.value = false
  }

  return {
    isFinishDialogOpen,
    openPrintDialog,
    closePrintDialog
  }
}
