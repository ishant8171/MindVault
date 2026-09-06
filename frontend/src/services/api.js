const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

async function request(path, options = {}) {
  const url = `${API_BASE}${path}`
  const res = await fetch(url, options)
  if (!res.ok) {
    const text = await res.text()
    let message = text || res.statusText
    try {
      const parsed = JSON.parse(text)
      message = parsed.detail || message
    } catch (_) {}
    throw new Error(message)
  }
  if (res.status === 204) return null
  return res.json()
}

export async function post(path, body, token) {
  return request(path, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    },
    body: JSON.stringify(body)
  })
}

export async function get(path, token) {
  return request(path, {
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    }
  })
}

export async function patch(path, body, token) {
  return request(path, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    },
    body: JSON.stringify(body)
  })
}

export async function del(path, token) {
  return request(path, {
    method: 'DELETE',
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    }
  })
}

export async function upload(path, file, token) {
  const form = new FormData()
  form.append('file', file)
  return request(path, {
    method: 'POST',
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    },
    body: form
  })
}

export default { post, get, patch, del, upload }
