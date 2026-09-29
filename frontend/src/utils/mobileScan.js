import { jsPDF } from 'jspdf';

function loadImage(file) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const image = new Image();
    image.onload = () => {
      URL.revokeObjectURL(url);
      resolve(image);
    };
    image.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error(`Could not read ${file.name || 'a captured page'}. Retake or choose a JPG/PNG image.`));
    };
    image.src = url;
  });
}

function imageAsJpeg(image) {
  const canvas = document.createElement('canvas');
  canvas.width = image.naturalWidth || image.width;
  canvas.height = image.naturalHeight || image.height;
  const context = canvas.getContext('2d');
  if (!context) throw new Error('This browser cannot prepare scanned pages as a PDF.');
  context.fillStyle = '#ffffff';
  context.fillRect(0, 0, canvas.width, canvas.height);
  context.drawImage(image, 0, 0, canvas.width, canvas.height);
  return canvas.toDataURL('image/jpeg', 0.92);
}

/** Combine sequential mobile camera/gallery images into one multi-page PDF. */
export async function createScannedPdf(files, fileName = 'petition_scan.pdf') {
  if (!Array.isArray(files) || files.length === 0) {
    throw new Error('Capture or select at least one page first.');
  }

  const firstImage = await loadImage(files[0]);
  const firstOrientation = firstImage.naturalWidth > firstImage.naturalHeight ? 'landscape' : 'portrait';
  const pdf = new jsPDF({ orientation: firstOrientation, unit: 'mm', format: 'a4', compress: true });

  for (let index = 0; index < files.length; index += 1) {
    const image = index === 0 ? firstImage : await loadImage(files[index]);
    const orientation = image.naturalWidth > image.naturalHeight ? 'landscape' : 'portrait';
    if (index > 0) pdf.addPage('a4', orientation);

    const pageWidth = pdf.internal.pageSize.getWidth();
    const pageHeight = pdf.internal.pageSize.getHeight();
    const margin = 5;
    const scale = Math.min(
      (pageWidth - margin * 2) / image.naturalWidth,
      (pageHeight - margin * 2) / image.naturalHeight
    );
    const width = image.naturalWidth * scale;
    const height = image.naturalHeight * scale;
    pdf.addImage(imageAsJpeg(image), 'JPEG', (pageWidth - width) / 2, (pageHeight - height) / 2, width, height, undefined, 'FAST');
  }

  const safeName = fileName.toLowerCase().endsWith('.pdf') ? fileName : `${fileName}.pdf`;
  const output = pdf.output('arraybuffer');
  if (output.byteLength > 48 * 1024 * 1024) {
    throw new Error('The combined scan is over 48 MB. Upload fewer pages at a time or choose an existing PDF.');
  }
  return new File([output], safeName, { type: 'application/pdf', lastModified: Date.now() });
}
