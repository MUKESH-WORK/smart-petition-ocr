import test from 'node:test';
import assert from 'node:assert/strict';
import { fetchPetitionBySourceId } from './apiService.js';

const originalFetch = globalThis.fetch;
const originalLocalStorage = globalThis.localStorage;

function setBrowserMocks(fetchImpl) {
  globalThis.localStorage = { getItem: () => null };
  globalThis.fetch = fetchImpl;
}

test('history fetch keeps the source ID and actual page count for the Assistant viewer', async () => {
  const sourceId = 'source-3-pages';
  const requested = [];
  setBrowserMocks(async (url, options) => {
    requested.push({ url: String(url), headers: options?.headers });
    if (String(url).endsWith('/draft')) return new Response(JSON.stringify({ dro_grievance_id: 'PET-123' }), { status: 200 });
    if (String(url).endsWith('/status')) return new Response(JSON.stringify({ file_name: 'petition.pdf', page_count: 3 }), { status: 200 });
    return new Response('{}', { status: 404 });
  });

  try {
    const petition = await fetchPetitionBySourceId(sourceId, { fileName: 'history.pdf', totalPages: 2 });
    assert.equal(petition.source_id, sourceId);
    assert.equal(petition.totalPages, 3);
    assert.equal(petition.fileName, 'history.pdf');
    assert.equal(requested.length, 4);
    assert.ok(requested.every((request) => request.url.includes(encodeURIComponent(sourceId))));
    assert.ok(requested.every((request) => request.headers.Authorization || request.headers['X-Officer-Id']));
  } finally {
    globalThis.fetch = originalFetch;
    globalThis.localStorage = originalLocalStorage;
  }
});

test('missing historical source returns null instead of opening a fabricated petition', async () => {
  setBrowserMocks(async () => new Response('{}', { status: 404 }));
  try {
    assert.equal(await fetchPetitionBySourceId('missing-source'), null);
  } finally {
    globalThis.fetch = originalFetch;
    globalThis.localStorage = originalLocalStorage;
  }
});
