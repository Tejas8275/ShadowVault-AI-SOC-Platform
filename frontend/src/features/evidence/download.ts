export const MAX_DOWNLOAD_BYTES = 100 * 1024 * 1024

// Evidence filenames are untrusted. Save an inertly named copy without path/header parsing.
export function downloadFilename(id: string) {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id)
    ? `evidence-${id}.bin` : 'evidence-copy.bin'
}

export async function readDownload(response: Response, expectedSize: number, signal: AbortSignal,
  progress?: (received: number) => void): Promise<Blob> {
  const length = response.headers.get('Content-Length')
  if (!Number.isSafeInteger(expectedSize) || expectedSize < 0 || expectedSize > MAX_DOWNLOAD_BYTES ||
      length === null || !/^\d+$/.test(length) || Number(length) !== expectedSize ||
      response.headers.get('Content-Type') !== 'application/octet-stream' || !response.body) {
    await response.body?.cancel()
    throw new Error('Download response did not match the expected evidence size or format.')
  }
  const reader = response.body.getReader()
  const chunks: ArrayBuffer[] = []
  let received = 0
  const cancel = () => { void reader.cancel().catch(() => {}) }
  signal.addEventListener('abort', cancel, { once: true })
  try {
    signal.throwIfAborted()
    progress?.(0)
    while (true) {
      const { done, value } = await reader.read()
      signal.throwIfAborted()
      if (done) break
      received += value.byteLength
      if (received > expectedSize || received > MAX_DOWNLOAD_BYTES) throw new Error('Download exceeded the expected size.')
      chunks.push(value.slice().buffer)
      progress?.(received)
    }
    if (received !== expectedSize) throw new Error('Download was incomplete. No copy is ready to save.')
    return new Blob(chunks, { type: 'application/octet-stream' })
  } finally {
    signal.removeEventListener('abort', cancel)
    await reader.cancel().catch(() => {})
    reader.releaseLock()
  }
}
