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
  try {
    const res = await fetch('/api/upload/session', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
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
    console.warn('Backend session API unavailable, using local fallback sessionId:', err);
  }

  // Fallback if backend is unreachable
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
 * Upload captured petition image from mobile phone
 * @param {string} sessionId
 * @param {File|Blob} file
 * @param {string} [customFileName]
 */
export async function uploadPetitionImage(sessionId, file, customFileName) {
  if (!sessionId || !file) {
    throw new Error('Session ID and file are required.');
  }

  const effectiveFileName = customFileName || file.name || `petition_${sessionId}.jpg`;

  const sizeFormatted = file.size > 1024 * 1024 
    ? `${(file.size / (1024 * 1024)).toFixed(1)} MB` 
    : `${Math.max(1, Math.round(file.size / 1024))} KB`;

  const dataUrl = await new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => resolve(null);
    reader.readAsDataURL(file);
  });

  const payload = {
    sessionId,
    fileName: effectiveFileName,
    fileSize: sizeFormatted,
    fileType: file.type || 'image/jpeg',
    dataUrl: dataUrl,
    uploadedAt: new Date().toISOString()
  };

  // 1. Broadcast locally
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

  // 2. Send to backend REST API via multipart/form-data
  try {
    const formData = new FormData();
    formData.append('sessionId', sessionId);
    formData.append('fileName', effectiveFileName);
    formData.append('petition', file, effectiveFileName);

    const res = await fetch('/api/upload/petition', {
      method: 'POST',
      body: formData
    });

    if (res.ok) {
      return { success: true, ...payload };
    }
  } catch (err) {
    console.warn('Backend upload API error, fallback to client state:', err);
  }

  return { success: true, ...payload };
}

/**
 * Check upload status for a given session
 * @param {string} sessionId
 */
export async function checkUploadStatus(sessionId) {
  if (!sessionId) return { uploaded: false };

  // 1. Check local storage first
  try {
    const localRecord = localStorage.getItem(`qr_upload_${sessionId}`);
    if (localRecord) {
      const parsed = JSON.parse(localRecord);
      return { uploaded: true, ...parsed };
    }
  } catch {
    // Ignore storage errors
  }

  // 2. Poll backend REST API
  try {
    const res = await fetch(`/api/upload/status/${sessionId}`, {
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
