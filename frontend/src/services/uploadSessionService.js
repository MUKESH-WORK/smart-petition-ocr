// Upload Session Service for Mobile QR Petition Capture

const BROADCAST_CHANNEL_NAME = 'petition_qr_sync_channel';

let broadcastChannel = null;
try {
  if (typeof window !== 'undefined' && 'BroadcastChannel' in window) {
    broadcastChannel = new BroadcastChannel(BROADCAST_CHANNEL_NAME);
  }
} catch {
  broadcastChannel = null;
}

/**
 * Generate a random 8-character hexadecimal session ID
 */
export function generateLocalSessionId() {
  const chars = '0123456789abcdef';
  let result = '';
  for (let i = 0; i < 8; i++) {
    result += chars[Math.floor(Math.random() * 16)];
  }
  return result;
}

/**
 * Create a new upload session via backend API
 */
export async function createUploadSession() {
  const tunnelHeaders = {
    'Content-Type': 'application/json',
    'bypass-tunnel-reminder': 'true',
    'Bypass-Tunnel-Reminder': '1',
    'ngrok-skip-browser-warning': 'true'
  };

  const clientOrigin = typeof window !== 'undefined' ? window.location.origin : null;
  const clientHostname = typeof window !== 'undefined' ? window.location.hostname : null;
  const token = typeof localStorage !== 'undefined' ? (localStorage.getItem('auth_token') || localStorage.getItem('token') || '') : '';
  const officerId = typeof localStorage !== 'undefined' ? (localStorage.getItem('officer_id') || '') : '';

  const headers = { ...tunnelHeaders };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  if (officerId) headers['X-Officer-Id'] = officerId;

  try {
    // 1. Primary: FastAPI backend route
    const backendRes = await fetch('/api/v1/grievance/mobile-session', {
      method: 'POST',
      headers: headers,
      body: JSON.stringify({ 
        clientOrigin, 
        clientHostname,
        clientLanIp: (clientHostname && clientHostname !== 'localhost' && clientHostname !== '127.0.0.1') ? clientHostname : null
      })
    });
    if (backendRes.ok) {
      const data = await backendRes.json();
      if (data.sessionId || data.session_id) {
        return {
          sessionId: data.sessionId || data.session_id,
          networkHost: data.networkHost || null,
          availableHosts: data.availableHosts || []
        };
      }
    }
  } catch (err) {
    console.warn('FastAPI mobile-session check:', err);
  }

  try {
    // 2. Fallback during dev server testing
    const res = await fetch('/api/upload/session', {
      method: 'POST',
      headers: tunnelHeaders
    });

    if (res.ok) {
      const data = await res.json();
      if (data.sessionId) {
        return {
          sessionId: data.sessionId,
          networkHost: data.networkHost || null
        };
      }
    }
  } catch (err) {
    console.warn('Dev session API fallback notice:', err);
  }

  // 3. Fallback if offline
  const localId = generateLocalSessionId();
  try {
    sessionStorage.setItem(`session_init_${localId}`, Date.now().toString());
  } catch (e) {
    console.warn(e);
  }
  return {
    sessionId: localId,
    networkHost: null
  };
}

/**
 * Upload captured petition (PDF document or image) from mobile phone
 * @param {string} sessionId
 * @param {File|Blob} file
 * @param {string} [customFileName]
 */
export async function uploadPetitionImage(sessionId, file, customFileName) {
  if (!sessionId || !file) {
    throw new Error('Session ID and file are required.');
  }

  const isPdf = Boolean(
    (file.type && file.type === 'application/pdf') ||
    (file.name && file.name.toLowerCase().endsWith('.pdf')) ||
    (customFileName && customFileName.toLowerCase().endsWith('.pdf'))
  );

  const defaultExt = isPdf ? '.pdf' : '.jpg';
  const effectiveFileName = customFileName || file.name || `petition_${sessionId}${defaultExt}`;

  const sizeFormatted = file.size > 1024 * 1024 
    ? `${(file.size / (1024 * 1024)).toFixed(1)} MB` 
    : `${Math.max(1, Math.round(file.size / 1024))} KB`;

  // Keep large multi-page PDFs on the multipart path; base64 would inflate them
  // in memory and can exceed browser localStorage quotas.
  const dataUrl = file.size <= 2 * 1024 * 1024 ? await new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => resolve(null);
    reader.readAsDataURL(file);
  }) : null;

  const resolvedFileType = file.type || (isPdf ? 'application/pdf' : 'image/jpeg');

  const payload = {
    sessionId,
    fileName: effectiveFileName,
    fileSize: sizeFormatted,
    fileType: resolvedFileType,
    isPdf,
    dataUrl: dataUrl,
    uploadedAt: new Date().toISOString()
  };

  // 1. Broadcast locally (if running in same browser/tab or connected client)
  try {
    localStorage.setItem(`qr_upload_${sessionId}`, JSON.stringify(payload));
    if (broadcastChannel) {
      broadcastChannel.postMessage({
        type: 'PETITION_UPLOADED',
        ...payload
      });
    }
  } catch (err) {
    console.warn('Local broadcast sync notice:', err);
  }

  let serverAcknowledged = false;
  let lastError = null;

  const tunnelHeaders = {
    'bypass-tunnel-reminder': 'true',
    'Bypass-Tunnel-Reminder': '1',
    'ngrok-skip-browser-warning': 'true'
  };

  // 2A. Primary: FastAPI multipart/form-data upload to /api/v1/petitions/mobile-upload
  let uploadTimeoutId;
  try {
    const formData = new FormData();
    formData.append('sessionId', sessionId);
    formData.append('fileName', effectiveFileName);
    formData.append('file', file, effectiveFileName);

    const controller = new AbortController();
    uploadTimeoutId = setTimeout(() => controller.abort(), 120000); // Allow large multi-page scans over Wi-Fi/tunnels.

    const fastApiRes = await fetch('/api/v1/grievance/mobile-upload', {
      method: 'POST',
      headers: tunnelHeaders,
      body: formData,
      signal: controller.signal
    });
    clearTimeout(uploadTimeoutId);
    uploadTimeoutId = null;

    if (fastApiRes.ok) {
      serverAcknowledged = true;
    } else {
      const errBody = await fastApiRes.json().catch(() => null);
      lastError = errBody?.detail || `Upload failed with status ${fastApiRes.status}`;
    }
  } catch (err) {
    if (uploadTimeoutId) clearTimeout(uploadTimeoutId);
    console.warn('FastAPI multipart upload notice:', err);
    lastError = err.message;
  }

  // 2B. Secondary: FastAPI JSON Base64 upload if multipart was blocked/proxied
  if (!serverAcknowledged && dataUrl) {
    try {
      const fastApiJsonRes = await fetch('/api/v1/grievance/mobile-upload', {
        method: 'POST',
        headers: {
          ...tunnelHeaders,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          sessionId,
          fileName: effectiveFileName,
          fileType: resolvedFileType,
          fileSize: sizeFormatted,
          dataUrl
        })
      });

      if (fastApiJsonRes.ok) {
        serverAcknowledged = true;
      }
    } catch (err) {
      console.warn('FastAPI JSON fallback notice:', err);
    }
  }

  // 2C. Fallback to Vite dev middleware if in local development
  if (!serverAcknowledged) {
    try {
      const devFormData = new FormData();
      devFormData.append('sessionId', sessionId);
      devFormData.append('fileName', effectiveFileName);
      devFormData.append('petition', file, effectiveFileName);

      const devRes = await fetch('/api/upload/petition', {
        method: 'POST',
        headers: tunnelHeaders,
        body: devFormData
      });

      if (devRes.ok) {
        serverAcknowledged = true;
      }
    } catch (devErr) {
      console.warn('Dev server upload notice:', devErr);
    }
  }

  if (!serverAcknowledged) {
    throw new Error(lastError || 'Could not transfer document to workstation. Please verify Wi-Fi connection and tap Upload again.');
  }

  return { success: true, ...payload };
}

/**
 * Check upload status for a given session
 * @param {string} sessionId
 */
export async function checkUploadStatus(sessionId) {
  if (!sessionId) return { uploaded: false };

  const tunnelHeaders = {
    'bypass-tunnel-reminder': 'true',
    'Bypass-Tunnel-Reminder': '1',
    'ngrok-skip-browser-warning': 'true',
    'Cache-Control': 'no-cache'
  };

  // 1. Check local storage first (instant if same browser)
  try {
    const localRecord = localStorage.getItem(`qr_upload_${sessionId}`);
    if (localRecord) {
      const parsed = JSON.parse(localRecord);
      return { uploaded: true, ...parsed };
    }
  } catch {
    // Ignore storage errors
  }

  // 2. Poll FastAPI backend route: /api/v1/grievance/mobile-status/{sessionId}
  try {
    const res = await fetch(`/api/v1/grievance/mobile-status/${sessionId}`, {
      headers: tunnelHeaders,
      cache: 'no-store'
    });
    if (res.ok) {
      const data = await res.json();
      if (data.uploaded) {
        return {
          uploaded: true,
          sessionId,
          source_id: data.source_id,
          fileName: data.fileName || data.file_name,
          fileSize: data.fileSize || data.file_size,
          fileType: data.fileType || data.file_type,
          dataUrl: data.dataUrl,
          status: data.status,
          page_count: data.page_count,
          duplicate_detected: data.duplicate_detected,
          duplicate_source_id: data.duplicate_source_id,
          duplicate_petitioner_name: data.duplicate_petitioner_name,
          duplicate_file_name: data.duplicate_file_name,
          duplicate_summary: data.duplicate_summary,
          duplicate_created_at: data.duplicate_created_at
        };
      }
    }
  } catch {
    // Backend polling retry
  }

  // 3. Poll Vite dev REST API fallback
  try {
    const res = await fetch(`/api/upload/status/${sessionId}`, {
      headers: tunnelHeaders,
      cache: 'no-store'
    });
    if (res.ok) {
      const data = await res.json();
      if (data.uploaded) {
        return {
          uploaded: true,
          sessionId,
          fileName: data.fileName,
          fileSize: data.fileSize,
          fileType: data.fileType,
          dataUrl: data.dataUrl
        };
      }
    }
  } catch {
    // Polling retry
  }

  return { uploaded: false, sessionId };
}

/**
 * Listen for upload completion using BroadcastChannel, storage events, and polling
 * @param {string} sessionId
 * @param {Function} onUploaded - Callback when petition is uploaded
 * @returns {Function} unsubscribe cleanup function
 */
export function subscribeToUpload(sessionId, onUploaded) {
  let isDone = false;

  const handleSuccess = (data) => {
    if (isDone) return;
    isDone = true;
    clearInterval(pollInterval);
    if (broadcastChannel) {
      broadcastChannel.removeEventListener('message', handleBroadcast);
    }
    window.removeEventListener('storage', handleStorage);
    onUploaded(data);
  };

  const handleBroadcast = (event) => {
    if (event.data && event.data.type === 'PETITION_UPLOADED' && (event.data.sessionId === sessionId || event.data.session_id === sessionId)) {
      handleSuccess(event.data);
    }
  };

  if (broadcastChannel) {
    broadcastChannel.addEventListener('message', handleBroadcast);
  }

  const handleStorage = (e) => {
    if (e.key === `qr_upload_${sessionId}` && e.newValue) {
      try {
        const data = JSON.parse(e.newValue);
        handleSuccess(data);
      } catch (err) {
        console.warn('Storage parse error', err);
      }
    }
  };
  window.addEventListener('storage', handleStorage);

  const pollInterval = setInterval(async () => {
    if (isDone) return;
    const status = await checkUploadStatus(sessionId);
    if (status && status.uploaded) {
      handleSuccess(status);
    }
  }, 1200);

  checkUploadStatus(sessionId).then((status) => {
    if (status && status.uploaded) {
      handleSuccess(status);
    }
  });

  return () => {
    isDone = true;
    clearInterval(pollInterval);
    if (broadcastChannel) {
      broadcastChannel.removeEventListener('message', handleBroadcast);
    }
    window.removeEventListener('storage', handleStorage);
  };
}

/**
 * Cleanup session data
 */
export function cleanupUploadSession(sessionId) {
  if (!sessionId) return;
  try {
    localStorage.removeItem(`qr_upload_${sessionId}`);
    sessionStorage.removeItem(`session_init_${sessionId}`);
  } catch {
    // Ignore cleanup errors
  }
}
