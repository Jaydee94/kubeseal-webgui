import { onBeforeUnmount, onMounted } from 'vue'
import { carriesFiles } from '@/utils/dragDrop'

/**
 * Stops the browser from opening a file that is dropped next to the drop
 * target, which would leave the page and lose the form. Drops on `target`
 * (a CSS selector) are not affected; they are handled by the target itself.
 */
export function useFileDropGuard(target) {
  function onDragOver(event) {
    if (!carriesFiles(event)) return
    event.preventDefault()
    // Elsewhere nothing is accepted, which the cursor shows.
    if (!event.target.closest?.(target)) event.dataTransfer.dropEffect = 'none'
  }

  function onDrop(event) {
    if (carriesFiles(event)) event.preventDefault()
  }

  onMounted(() => {
    window.addEventListener('dragover', onDragOver)
    window.addEventListener('drop', onDrop)
  })
  onBeforeUnmount(() => {
    window.removeEventListener('dragover', onDragOver)
    window.removeEventListener('drop', onDrop)
  })
}
