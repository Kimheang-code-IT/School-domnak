import { ref } from 'vue'

export function useInvoicePrinter() {
  const invoicePrintRef = ref<HTMLElement | null>(null)
  const cachedHeadAssets = ref('')

  async function waitForImagesToLoad(doc: Document, timeoutMs = 1500) {
    const images = Array.from(doc.images || [])
    if (!images.length) return

    await Promise.all(
      images.map((img) => {
        if (img.complete) return Promise.resolve()
        return new Promise<void>((resolve) => {
          const done = () => resolve()
          img.addEventListener('load', done, { once: true })
          img.addEventListener('error', done, { once: true })
          setTimeout(done, timeoutMs)
        })
      })
    )
  }

  async function printInvoice() {
    if (typeof window === 'undefined') return
    const target = invoicePrintRef.value
    if (!target) return
    const htmlClass = document.documentElement.className || ''
    const htmlLang = document.documentElement.lang || 'en'
    const htmlDir = document.documentElement.dir || 'ltr'
    if (!cachedHeadAssets.value) {
      cachedHeadAssets.value = Array.from(
        document.head.querySelectorAll('link[rel="stylesheet"], style')
      )
        .map((node) => node.outerHTML)
        .join('\n')
    }

    const iframe = document.createElement('iframe')
    iframe.style.position = 'fixed'
    iframe.style.width = '0'
    iframe.style.height = '0'
    iframe.style.border = '0'
    iframe.style.visibility = 'hidden'
    iframe.setAttribute('aria-hidden', 'true')
    document.body.appendChild(iframe)

    const frameWindow = iframe.contentWindow
    const frameDoc = iframe.contentDocument
    if (!frameWindow || !frameDoc) {
      iframe.remove()
      return
    }

    const printableNode = target.cloneNode(true) as HTMLElement
    printableNode.querySelectorAll<HTMLElement>(
      '.origin-top-left,.scale-\\[0\\.65\\],.scale-\\[0\\.75\\],.sm\\:scale-100,.w-\\[153\\.846\\%\\],.w-\\[133\\.333\\%\\]'
    ).forEach((node) => {
      node.classList.remove(
        'origin-top-left',
        'scale-[0.65]',
        'scale-[0.75]',
        'sm:scale-100',
        'w-[153.846%]',
        'w-[133.333%]'
      )
    })

    const html = `
      <html class="${htmlClass}" lang="${htmlLang}" dir="${htmlDir}">
        <head>
          <title>Invoice</title>
          ${cachedHeadAssets.value}
          <style>
            * { box-sizing: border-box; }
            html, body {
              margin: 0;
              padding: 0;
              background: #fff;
              width: auto;
              height: auto;
              overflow: visible;
            }
            @page { margin: 0; size: A5 portrait; }
            .print-root {
              width: 100%;
            }
            .invoice-print-target {
              width: 100%;
            }
            .invoice-print-target .max-w-2xl {
              max-width: none !important;
            }
            .invoice-print-target .mx-auto {
              margin-left: 0 !important;
              margin-right: 0 !important;
            }
            .invoice-print-target [class*="w-[153.846%]"],
            .invoice-print-target [class*="w-[133.333%]"] {
              width: 100% !important;
            }
            .invoice-print-target [class*="scale-[0.65]"],
            .invoice-print-target [class*="scale-[0.75]"],
            .invoice-print-target [class*="origin-top-left"] {
              transform: none !important;
              transform-origin: top left !important;
            }
            .invoice-print-target {
              max-height: none !important;
              overflow: visible !important;
            }
            .invoice-print-target .h-full,
            .invoice-print-target .min-h-0 {
              height: auto !important;
              min-height: auto !important;
            }
            .invoice-print-target .overflow-y-auto {
              overflow: visible !important;
            }
            .print-invoice-page {
              width: 148mm !important;
              min-height: 210mm !important;
              break-after: page;
              page-break-after: always;
            }
            .print-invoice-page:last-child {
              break-after: auto;
              page-break-after: auto;
            }
            .invoice-print-target table,
            .invoice-print-target table thead th,
            .invoice-print-target table tbody td,
            .invoice-print-target table tr {
              border-width: 0.1px !important;
              border-color: #cbd5e1 !important;
            }
            .invoice-print-target table thead th {
              font-size: 10px !important;
              line-height: 1.15 !important;
              padding-top: 3px !important;
              padding-bottom: 3px !important;
            }
            .invoice-print-target table tbody td {
              font-size: 10px !important;
              padding-top: 4px !important;
              padding-bottom: 4px !important;
              line-height: 1.15 !important;
            }
            .invoice-print-target [lang="km"],
            .invoice-print-target :lang(km) {
              font-size: 10px !important;
              line-height: 1 !important;
            }
          </style>
        </head>
        <body>
          <div class="print-root">${printableNode.outerHTML}</div>
        </body>
      </html>
    `

    frameDoc.open()
    frameDoc.write(html)
    frameDoc.close()

    await waitForImagesToLoad(frameDoc)
    await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()))
    await new Promise<void>((resolve) => setTimeout(resolve, 40))

    frameWindow.focus()
    frameWindow.print()

    setTimeout(() => {
      iframe.remove()
    }, 500)
  }

  return {
    invoicePrintRef,
    printInvoice
  }
}
