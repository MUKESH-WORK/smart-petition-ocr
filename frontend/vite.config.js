import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import crypto from 'crypto'
import os from 'os'
import net from 'net'

// System-independent backend detection
const backendHost = process.env.BACKEND_HOST || '127.0.0.1'
let activeBackendPort = Number(process.env.BACKEND_PORT || process.env.VITE_BACKEND_PORT || 8000)
const explicitBackendUrl = process.env.VITE_BACKEND_URL || process.env.BACKEND_URL || null

function checkBackendPort(port, host = backendHost) {
  return new Promise((resolve) => {
    const socket = net.createConnection({ port, host, timeout: 500 }, () => {
      socket.destroy()
      resolve(true)
    })
    socket.on('error', () => resolve(false))
    socket.on('timeout', () => { socket.destroy(); resolve(false) })
  })
}

async function updateActiveBackendPort() {
  if (explicitBackendUrl || process.env.BACKEND_PORT) {
    if (process.env.BACKEND_PORT) activeBackendPort = Number(process.env.BACKEND_PORT)
    return
  }
  const is8000 = await checkBackendPort(8000, backendHost)
  if (is8000) {
    activeBackendPort = 8000
    return
  }
  const is8001 = await checkBackendPort(8001, backendHost)
  if (is8001) {
    activeBackendPort = 8001
  }
}

updateActiveBackendPort()
if (!explicitBackendUrl) {
  setInterval(updateActiveBackendPort, 5000)
}

// In-memory store for upload sessions during dev server execution
const sessions = new Map()

// Helper to get local network IP address (cross-platform: Linux, macOS, Windows, Docker)
function getLocalIpAddress() {
  if (process.env.VITE_PUBLIC_URL || process.env.PUBLIC_URL) {
    return null
  }
  try {
    const interfaces = os.networkInterfaces()
    const candidates = []
    
    for (const [name, ifaceList] of Object.entries(interfaces)) {
      if (!ifaceList) continue
      for (const iface of ifaceList) {
        if (iface.family === 'IPv4' && !iface.internal && iface.address !== '127.0.0.1') {
          candidates.push({ name: name.toLowerCase(), address: iface.address })
        }
      }
    }

    if (candidates.length === 0) return null

    // 1. Prefer physical Wi-Fi / Ethernet / ens / eth adapters
    const primary = candidates.find(c => 
      c.name.includes('wi-fi') || c.name.includes('wlan') || 
      c.name.includes('eth') || c.name.includes('en')
    )
    if (primary) return primary.address

    // 2. Default to first detected IPv4 address
    return candidates[0].address
  } catch {
    // Ignore network interface discovery errors
    return null
  }
}

// Cleanup sessions older than 15 minutes
setInterval(() => {
  const now = Date.now()
  for (const [id, session] of sessions.entries()) {
    if (now - session.createdAt > 15 * 60 * 1000) {
      sessions.delete(id)
    }
  }
}, 60 * 1000)

function qrUploadApiPlugin() {
  return {
    name: 'qr-petition-upload-api',
    configureServer(server) {
      server.middlewares.use(async (req, res, next) => {
        const url = new URL(req.url, `http://${req.headers.host}`)
        const pathname = url.pathname

        // Enable CORS for mobile browsers on same Wi-Fi
        res.setHeader('Access-Control-Allow-Origin', '*')
        res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        res.setHeader('Access-Control-Allow-Headers', 'Content-Type')

        if (req.method === 'OPTIONS') {
          res.statusCode = 204
          return res.end()
        }

        // 1. POST /api/upload/session -> Create a unique session ID and provide network IP
        if (req.method === 'POST' && pathname === '/api/upload/session') {
          const sessionId = crypto.randomBytes(4).toString('hex') // e.g. "8f42c7a1"
          sessions.set(sessionId, {
            sessionId,
            createdAt: Date.now(),
            uploaded: false,
            file: null
          })

          const localIp = getLocalIpAddress()
          const hostHeader = req.headers.host || 'localhost:5174'
          const port = hostHeader.includes(':') ? hostHeader.split(':')[1] : '5174'
          const publicDomain = process.env.VITE_PUBLIC_URL || process.env.PUBLIC_URL || null
          const networkHost = publicDomain || (localIp ? `http://${localIp}:${port}` : null)

          res.setHeader('Content-Type', 'application/json')
          res.statusCode = 200
          return res.end(JSON.stringify({ 
            sessionId,
            networkHost
          }))
        }

        // 2. GET /api/upload/status/:sessionId -> Check upload status
        if (req.method === 'GET' && pathname.startsWith('/api/upload/status/')) {
          const sessionId = pathname.replace('/api/upload/status/', '').trim()
          const session = sessions.get(sessionId)

          res.setHeader('Content-Type', 'application/json')
          if (!session) {
            res.statusCode = 200
            return res.end(JSON.stringify({ uploaded: false, error: 'Session not found' }))
          }

          if (session.uploaded && session.file) {
            res.statusCode = 200
            return res.end(JSON.stringify({
              uploaded: true,
              sessionId,
              fileName: session.file.fileName,
              fileSize: session.file.fileSize,
              fileType: session.file.fileType,
              dataUrl: session.file.dataUrl
            }))
          }

          res.statusCode = 200
          return res.end(JSON.stringify({ uploaded: false, sessionId }))
        }

        // 3. POST /api/upload/petition -> Upload captured petition image
        if (req.method === 'POST' && pathname === '/api/upload/petition') {
          const chunks = []
          req.on('data', chunk => chunks.push(chunk))
          req.on('end', () => {
            try {
              const bodyBuffer = Buffer.concat(chunks)
              const contentType = req.headers['content-type'] || ''

              let sessionId = ''
              let fileName = `petition_${Date.now()}.jpg`
              let fileType = 'image/jpeg'
              let fileBuffer = null

              if (contentType.includes('multipart/form-data')) {
                const boundaryMatch = contentType.match(/boundary=(?:"([^"]+)"|([^;]+))/i)
                const boundary = boundaryMatch ? (boundaryMatch[1] || boundaryMatch[2]) : null

                if (boundary) {
                  const parts = bodyBuffer.toString('binary').split(`--${boundary}`)
                  for (const part of parts) {
                    if (part.includes('name="sessionId"')) {
                      const match = part.match(/\r\n\r\n([\s\S]*?)\r\n/)
                      if (match) sessionId = match[1].trim()
                    }
                    if (part.includes('name="petition"') || part.includes('filename="')) {
                      const filenameMatch = part.match(/filename="([^"]+)"/)
                      if (filenameMatch) fileName = filenameMatch[1]

                      const typeMatch = part.match(/Content-Type:\s*([^\r\n]+)/i)
                      if (typeMatch) fileType = typeMatch[1].trim()

                      const headerEnd = part.indexOf('\r\n\r\n')
                      if (headerEnd !== -1) {
                        const rawData = part.substring(headerEnd + 4, part.length - 2)
                        fileBuffer = Buffer.from(rawData, 'binary')
                      }
                    }
                  }
                }
              } else if (contentType.includes('application/json')) {
                const parsed = JSON.parse(bodyBuffer.toString('utf-8'))
                sessionId = parsed.sessionId
                fileName = parsed.fileName || fileName
                fileType = parsed.fileType || fileType
                if (parsed.dataUrl) {
                  const base64Data = parsed.dataUrl.replace(/^data:[^;]+;base64,/, '')
                  fileBuffer = Buffer.from(base64Data, 'base64')
                }
              }

              if (!sessionId) {
                res.statusCode = 400
                res.setHeader('Content-Type', 'application/json')
                return res.end(JSON.stringify({ error: 'Missing sessionId' }))
              }

              let session = sessions.get(sessionId)
              if (!session) {
                session = {
                  sessionId,
                  createdAt: Date.now(),
                  uploaded: false,
                  file: null
                }
                sessions.set(sessionId, session)
              }

              const isPdf = fileType === 'application/pdf' || (fileName && fileName.toLowerCase().endsWith('.pdf'))
              if (isPdf) {
                fileType = 'application/pdf'
              }

              const dataUrl = fileBuffer 
                ? `data:${fileType};base64,${fileBuffer.toString('base64')}` 
                : null

              const sizeFormatted = fileBuffer 
                ? (fileBuffer.length > 1024 * 1024 
                    ? `${(fileBuffer.length / (1024 * 1024)).toFixed(1)} MB` 
                    : `${Math.max(1, Math.round(fileBuffer.length / 1024))} KB`)
                : '1.2 MB'

              session.uploaded = true
              session.file = {
                fileName: fileName || (isPdf ? `petition_${sessionId}.pdf` : `petition_${sessionId}.jpg`),
                fileSize: sizeFormatted,
                fileType: fileType || (isPdf ? 'application/pdf' : 'image/jpeg'),
                dataUrl: dataUrl,
                buffer: fileBuffer
              }

              res.statusCode = 200
              res.setHeader('Content-Type', 'application/json')
              return res.end(JSON.stringify({ 
                success: true, 
                message: 'Petition uploaded successfully',
                sessionId 
              }))
            } catch (err) {
              console.error('Error handling petition upload:', err)
              res.statusCode = 500
              res.setHeader('Content-Type', 'application/json')
              return res.end(JSON.stringify({ error: 'Internal Server Error' }))
            }
          })
          return
        }

        next()
      })
    }
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), qrUploadApiPlugin()],
  server: {
    host: true, // Listen on all network interfaces
    port: Number(process.env.PORT || process.env.VITE_PORT || 5174),
    proxy: {
      '/api/v1': {
        target: explicitBackendUrl || `http://${backendHost}:${activeBackendPort}`,
        changeOrigin: true,
        router: () => explicitBackendUrl || `http://${backendHost}:${activeBackendPort}`,
        configure: (proxy) => {
          proxy.on('error', (err, req, res) => {
            updateActiveBackendPort()
            if (err.code === 'ECONNREFUSED') {
              const targetDesc = explicitBackendUrl || `${backendHost}:${activeBackendPort}`
              console.warn(`[vite proxy] Backend (${targetDesc}) offline/restarting (${req.url})`)
              if (res && !res.headersSent) {
                res.writeHead(503, { 'Content-Type': 'application/json' })
                res.end(JSON.stringify({ error: `Backend server (${targetDesc}) is starting up. Please retry in a few seconds.` }))
              }
            }
          })
        }
      }
    }
  }
})
