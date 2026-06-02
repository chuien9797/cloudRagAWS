const runtimeConfig = window.__APP_CONFIG__ || {}
const API_BASE_URL = (runtimeConfig.API_BASE_URL || import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "")

const TOKEN_KEY = "cloudrag_auth_token"
const USER_KEY = "cloudrag_auth_user"

function apiUrl(path) {
  return API_BASE_URL ? `${API_BASE_URL}${path}` : path
}

function readStoredJson(key) {
  const raw = window.localStorage.getItem(key)
  if (!raw) return null
  try {
    return JSON.parse(raw)
  } catch {
    return null
  }
}

export function getAuthToken() {
  return window.localStorage.getItem(TOKEN_KEY) || ""
}

export function getStoredUser() {
  return readStoredJson(USER_KEY)
}

export function clearAuth() {
  window.localStorage.removeItem(TOKEN_KEY)
  window.localStorage.removeItem(USER_KEY)
}

export function storeAuthSession(token, user) {
  window.localStorage.setItem(TOKEN_KEY, token)
  window.localStorage.setItem(USER_KEY, JSON.stringify(user))
}

function authHeaders(extra = {}) {
  const token = getAuthToken()
  return {
    ...extra,
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

function extractErrorMessage(data, fallback) {
  if (!data) return fallback
  if (typeof data === "string") return data

  const detail = data.detail
  if (typeof detail === "string" && detail.trim()) return detail

  if (Array.isArray(detail)) {
    const joined = detail
      .map((item) => {
        if (typeof item === "string") return item
        if (item && typeof item === "object") {
          const msg = item.msg || item.message
          if (typeof msg === "string") return msg
        }
        return ""
      })
      .filter(Boolean)
      .join("; ")
    if (joined) return joined
  }

  if (detail && typeof detail === "object") {
    const msg = detail.message || detail.error
    if (typeof msg === "string" && msg.trim()) return msg
    try {
      return JSON.stringify(detail)
    } catch {
      return fallback
    }
  }

  const msg = data.message || data.error
  if (typeof msg === "string" && msg.trim()) return msg

  try {
    return JSON.stringify(data)
  } catch {
    return fallback
  }
}

async function parseResponse(res) {
  const text = await res.text()
  if (!text) return null
  try {
    return JSON.parse(text)
  } catch {
    throw new Error(`Non-JSON response (${res.status}): ${text.slice(0, 100)}`)
  }
}

async function authedFetch(path, options = {}) {
  const res = await fetch(apiUrl(path), {
    ...options,
    headers: authHeaders(options.headers || {}),
  })
  if (res.status === 401) {
    clearAuth()
  }
  return res
}

export async function login(email, password) {
  const res = await fetch(apiUrl("/api/auth/login"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  })
  const data = await parseResponse(res)
  if (!res.ok) throw new Error(extractErrorMessage(data, "Login failed"))
  storeAuthSession(data.access_token, data.user)
  return data.user
}

export async function fetchCurrentUser() {
  const res = await authedFetch("/api/auth/me")
  const data = await parseResponse(res)
  if (!res.ok) throw new Error(extractErrorMessage(data, "Failed to fetch user"))
  if (data?.user) {
    storeAuthSession(getAuthToken(), data.user)
  }
  return data?.user ?? null
}

export async function logout() {
  try {
    await authedFetch("/api/auth/logout", { method: "POST" })
  } finally {
    clearAuth()
  }
}

export async function fetchDocuments() {
  const res = await authedFetch("/api/documents")
  const data = await parseResponse(res)
  if (!res.ok) throw new Error(extractErrorMessage(data, "Failed to fetch documents"))
  return data ?? []
}

export async function uploadDocument(file, isPublic = false) {
  const formData = new FormData()
  formData.append("file", file)
  formData.append("is_public", isPublic ? "true" : "false")
  const res = await authedFetch("/api/upload", {
    method: "POST",
    body: formData,
  })
  const data = await parseResponse(res)
  if (!res.ok) throw new Error(extractErrorMessage(data, "Upload failed"))
  return data
}

export async function deleteDocument(docId) {
  const res = await authedFetch(`/api/documents/${docId}`, { method: "DELETE" })
  const data = await parseResponse(res)
  if (!res.ok) throw new Error(extractErrorMessage(data, "Failed to delete document"))
  return data
}

export async function updateDocumentVisibility(docId, isPublic) {
  const res = await authedFetch(`/api/documents/${docId}/visibility`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ is_public: isPublic }),
  })
  const data = await parseResponse(res)
  if (!res.ok) throw new Error(extractErrorMessage(data, "Failed to update document visibility"))
  return data
}

export async function openDocumentFile(docId, pageNumber = null) {
  const res = await authedFetch(`/api/documents/${docId}/file`)
  if (!res.ok) {
    const data = await parseResponse(res)
    throw new Error(extractErrorMessage(data, "Failed to open source document"))
  }

  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const page = pageNumber ? `#page=${pageNumber}` : ""
  window.open(`${url}${page}`, "_blank", "noopener,noreferrer")
  setTimeout(() => URL.revokeObjectURL(url), 60000)
}

export async function askQuestion(question, docId, sessionId, options = {}) {
  const res = await authedFetch("/api/ask/with-sources", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    signal: options.signal,
    body: JSON.stringify({
      question,
      doc_id: docId || null,
      session_id: sessionId || null,
    }),
  })
  const data = await parseResponse(res)
  if (!res.ok) throw new Error(extractErrorMessage(data, "Ask failed"))
  return data
}

export async function fetchSessions() {
  const res = await authedFetch("/api/sessions")
  const data = await parseResponse(res)
  if (!res.ok) throw new Error(extractErrorMessage(data, "Failed to fetch sessions"))
  return data ?? []
}

export async function fetchSessionMessages(sessionId) {
  const res = await authedFetch(`/api/sessions/${sessionId}/messages`)
  const data = await parseResponse(res)
  if (!res.ok) throw new Error(extractErrorMessage(data, "Failed to fetch messages"))
  return data ?? []
}

export async function deleteSession(sessionId) {
  const res = await authedFetch(`/api/sessions/${sessionId}`, { method: "DELETE" })
  const data = await parseResponse(res)
  if (!res.ok) throw new Error(extractErrorMessage(data, "Failed to delete session"))
  return data
}
