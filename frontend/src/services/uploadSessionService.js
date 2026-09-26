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
 * Create a new upload session via backend API (with fallback)
 */
export async function createUploadSession() {
  const tunnelHeaders = {
    'Content-Type': 'application/json',
    'bypass-tunnel-reminder': 'true',
    'Bypass-Tunnel-Reminder': '1',
    'ngrok-skip-browser-warning': 'true'
  };

  try {
    // 1. Try FastAPI backend route first
    const backendRes = await fetch('/api/v1/petitions/mobile-session', {
      method: 'POST',
      headers: tunnelHeaders,
      body: JSON.stringify({})
    });
    if (backendRes.ok) {
      const data = await backendRes.json();
      if (data.sessionId) {
        return {
          sessionId: data.sessionId,
          networkHost: data.networkHost || null
        };
      }
    }
  } catch (err) {
    console.warn('FastAPI mobile-session check:', err);
  }

  try {
    // 2. Fallback to Vite dev middleware route
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
    console.warn('Vite session API fallback warning:', err);
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

  const dataUrl = await new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => resolve(null);
    reader.readAsDataURL(file);
  });

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

  // 1. Broadcast locally (if running in same browser/tab)
  try {
    localStorage.setItem(`qr_upload_${sessionId}`, JSON.stringify(payload));
    if (broadcastChannel) {
      broadcastChannel.postMessage({
        type: 'PETITION_UPLOADED',
        ...payload
      });
    }
  } catch (err) {
    console.warn('Local broadcast sync warning:', err);
  }

  // 2. Send to server endpoints (FastAPI backend + Vite server with bypass headers)
  let serverAcknowledged = false;

  const tunnelHeaders = {
    'bypass-tunnel-reminder': 'true',
    'Bypass-Tunnel-Reminder': '1',
    'ngrok-skip-browser-warning': 'true'
  };

  // 2A. Try FastAPI JSON endpoint (clean, universal, high reliability)
  if (dataUrl) {
    try {
      const fastApiRes = await fetch('/api/v1/petitions/mobile-upload', {
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

      if (fastApiRes.ok) {
        serverAcknowledged = true;
      }
    } catch (err) {
      console.warn('FastAPI mobile-upload route check:', err);
    }
  }

  // 2B. Also forward to Vite middleware via multipart/form-data with timeout
  try {
    const formData = new FormData();
    formData.append('sessionId', sessionId);
    formData.append('fileName', effectiveFileName);
    formData.append('petition', file, effectiveFileName);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 25000); // 25s timeout

    const res = await fetch('/api/upload/petition', {
      method: 'POST',
      headers: tunnelHeaders,
      body: formData,
      signal: controller.signal
    });
    clearTimeout(timeoutId);

    if (res.ok) {
      serverAcknowledged = true;
    }
  } catch (err) {
    console.warn('Vite multipart upload check:', err);
  }

  // 2C. Fallback to Vite JSON base64 route
  if (!serverAcknowledged && dataUrl) {
    try {
      const jsonRes = await fetch('/api/upload/petition', {
        method: 'POST',
        headers: {
          ...tunnelHeaders,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          sessionId,
          fileName: effectiveFileName,
          fileType: resolvedFileType,
          dataUrl
        })
      });

      if (jsonRes.ok) {
        serverAcknowledged = true;
      }
    } catch (jsonErr) {
      console.error('Vite JSON fallback error:', jsonErr);
    }
  }

  if (!serverAcknowledged) {
    throw new Error('Could not transfer document to workstation. Please check your network connection and tap Upload again.');
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

  // 2. Poll FastAPI backend route
  try {
    const res = await fetch(`/api/v1/petitions/mobile-status/${sessionId}`, {
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
    // Backend polling retry
  }

  // 3. Poll Vite dev REST API
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
    // Network errors during polling are ignored
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
    if (event.data && event.data.type === 'PETITION_UPLOADED' && event.data.sessionId === sessionId) {
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
