// Lightweight zero-dependency IndexedDB helper for resilient mobile petition capture

const DB_NAME = 'gdp_mobile_capture_db';
const DB_VERSION = 1;
const STORE_NAME = 'drafts';

function openDb() {
  return new Promise((resolve, reject) => {
    if (typeof window === 'undefined' || !window.indexedDB) {
      return reject(new Error('IndexedDB not supported in this environment'));
    }
    const req = window.indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = (e) => {
      const db = e.target.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: 'sessionId' });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

/**
 * Save draft file & metadata to IndexedDB for camera reload resilience
 */
export async function saveMobileDraft(sessionId, files, meta, customFileName = '') {
  const fileList = (Array.isArray(files) ? files : [files]).filter(Boolean);
  if (!sessionId || fileList.length === 0) return;
  try {
    const db = await openDb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readwrite');
      const store = tx.objectStore(STORE_NAME);
      const record = {
        sessionId,
        fileBlobs: fileList.map((file) => ({
          blob: file,
          name: file.name || meta?.name || 'petition.jpg',
          type: file.type || meta?.type || 'image/jpeg'
        })),
        // Keep the old fields so a draft saved by an earlier app version still restores.
        fileBlob: fileList[0],
        fileName: fileList[0].name || meta?.name || 'petition.jpg',
        fileType: fileList[0].type || meta?.type || 'image/jpeg',
        meta: meta || {},
        customFileName: customFileName || '',
        updatedAt: Date.now()
      };
      const req = store.put(record);
      req.onsuccess = () => resolve(true);
      req.onerror = () => reject(req.error);
    });
  } catch (err) {
    console.warn('IndexedDB save draft notice:', err);
  }
}

/**
 * Load draft file & metadata from IndexedDB
 */
export async function loadMobileDraft(sessionId) {
  if (!sessionId) return null;
  try {
    const db = await openDb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readonly');
      const store = tx.objectStore(STORE_NAME);
      const req = store.get(sessionId);
      req.onsuccess = () => {
        const res = req.result;
        if (!res || (!res.fileBlob && !res.fileBlobs?.length)) return resolve(null);
        const fileBlobs = res.fileBlobs?.length ? res.fileBlobs : [{
          blob: res.fileBlob,
          name: res.fileName || 'petition.jpg',
          type: res.fileType || res.fileBlob?.type || 'image/jpeg'
        }];
        const files = fileBlobs.map((entry, index) => new File([entry.blob], entry.name || `petition_page_${index + 1}.jpg`, {
          type: entry.type || entry.blob?.type || 'image/jpeg'
        }));
        resolve({
          file: files[0],
          files,
          meta: res.meta || {},
          customFileName: res.customFileName || res.fileName || ''
        });
      };
      req.onerror = () => reject(req.error);
    });
  } catch (err) {
    console.warn('IndexedDB load draft notice:', err);
    return null;
  }
}

/**
 * Delete draft from IndexedDB
 */
export async function deleteMobileDraft(sessionId) {
  if (!sessionId) return;
  try {
    const db = await openDb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readwrite');
      const store = tx.objectStore(STORE_NAME);
      const req = store.delete(sessionId);
      req.onsuccess = () => resolve(true);
      req.onerror = () => reject(req.error);
    });
  } catch (err) {
    console.warn('IndexedDB delete draft notice:', err);
  }
}

/**
 * Safe client-side image downscaler for giant camera photos
 * Limits long edge to max 2400px with high JPEG quality (0.92) for optimal Tamil OCR.
 */
export async function downscaleMobilePhotoIfHuge(file, maxDimension = 2400, quality = 0.92) {
  if (!file || !file.type || !file.type.startsWith('image/')) {
    return file; // Return PDFs or non-images as-is
  }

  return new Promise((resolve) => {
    try {
      const img = new Image();
      const url = URL.createObjectURL(file);

      img.onload = () => {
        URL.revokeObjectURL(url);
        let { width, height } = img;

        if (width <= maxDimension && height <= maxDimension) {
          return resolve(file);
        }

        if (width > height) {
          if (width > maxDimension) {
            height = Math.round((height * maxDimension) / width);
            width = maxDimension;
          }
        } else {
          if (height > maxDimension) {
            width = Math.round((width * maxDimension) / height);
            height = maxDimension;
          }
        }

        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext('2d');
        if (!ctx) return resolve(file);

        ctx.drawImage(img, 0, 0, width, height);

        canvas.toBlob((blob) => {
          if (!blob) return resolve(file);
          const scaledFile = new File([blob], file.name, {
            type: 'image/jpeg',
            lastModified: Date.now()
          });
          resolve(scaledFile);
        }, 'image/jpeg', quality);
      };

      img.onerror = () => {
        URL.revokeObjectURL(url);
        resolve(file);
      };

      img.src = url;
    } catch {
      resolve(file);
    }
  });
}
