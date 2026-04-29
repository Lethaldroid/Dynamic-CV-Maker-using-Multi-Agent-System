const API_BASE = (import.meta.env.VITE_API_BASE || '').replace(/\/$/, '')

function buildUrl(path) {
  if (API_BASE) {
    return `${API_BASE}${path}`
  }

  if (import.meta.env.DEV) {
    return path
  }

  throw new Error(
    'Backend URL is not configured. Rebuild and redeploy the frontend with VITE_API_BASE set to your backend URL.',
  )
}

async function request(path, options = {}) {
  const response = await fetch(buildUrl(path), {
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
    ...options,
  })

  const contentType = response.headers.get('content-type') || ''
  const payload = contentType.includes('application/json') ? await response.json() : await response.text()

  if (!response.ok) {
    const message = typeof payload === 'string' ? payload : payload?.detail || 'Request failed'
    throw new Error(message)
  }

  return payload
}

export async function submitJob({ title, cvText, jdText, cvFile }) {
  if (cvFile) {
    const formData = new FormData()
    formData.append('title', title || '')
    formData.append('jd_text', jdText)
    formData.append('cv_file', cvFile)

    const response = await fetch(buildUrl('/api/jobs/upload'), {
      method: 'POST',
      body: formData,
    })

    const contentType = response.headers.get('content-type') || ''
    const payload = contentType.includes('application/json') ? await response.json() : await response.text()

    if (!response.ok) {
      const message = typeof payload === 'string' ? payload : payload?.detail || 'Request failed'
      throw new Error(message)
    }

    return payload
  }

  return request('/api/jobs', {
    method: 'POST',
    body: JSON.stringify({ title, cv_text: cvText, jd_text: jdText }),
  })
}

export async function parseCvFile(cvFile) {
  const formData = new FormData()
  formData.append('cv_file', cvFile)

  const response = await fetch(buildUrl('/api/cv/parse'), {
    method: 'POST',
    body: formData,
  })

  const contentType = response.headers.get('content-type') || ''
  const payload = contentType.includes('application/json') ? await response.json() : await response.text()

  if (!response.ok) {
    const message = typeof payload === 'string' ? payload : payload?.detail || 'Request failed'
    throw new Error(message)
  }

  return payload
}

export async function fetchJob(jobId) {
  return request(`/api/jobs/${jobId}`)
}

export function downloadUrl(jobId) {
  return buildUrl(`/api/jobs/${jobId}/download`)
}
