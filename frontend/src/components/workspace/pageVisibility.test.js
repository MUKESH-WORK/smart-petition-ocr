import test from 'node:test';
import assert from 'node:assert/strict';
import { getMostVisiblePage } from './pageVisibility.js';

const viewport = { top: 100, bottom: 500 };

test('selects the page with the most visible area for 1, 2, and 3 page documents', () => {
  assert.equal(getMostVisiblePage([{ top: 100, bottom: 500 }], viewport), 1);
  assert.equal(getMostVisiblePage([{ top: -250, bottom: 150 }, { top: 150, bottom: 550 }], viewport), 2);
  assert.equal(getMostVisiblePage([
    { top: -300, bottom: 100 },
    { top: 100, bottom: 500 },
    { top: 500, bottom: 900 }
  ], viewport), 2);
});

test('handles upward and downward movement and fast scroll positions without off-by-one errors', () => {
  const pages = [0, 1, 2, 3, 4].map((index) => ({ top: index * 400, bottom: (index + 1) * 400 }));
  assert.equal(getMostVisiblePage(pages.map((page) => ({ top: page.top - 600, bottom: page.bottom - 600 })), viewport), 3);
  assert.equal(getMostVisiblePage(pages.map((page) => ({ top: page.top - 1450, bottom: page.bottom - 1450 })), viewport), 5);
  assert.equal(getMostVisiblePage(pages.map((page) => ({ top: page.top - 200, bottom: page.bottom - 200 })), viewport), 2);
});

test('chooses the closest page when the viewport is between page boundaries', () => {
  assert.equal(getMostVisiblePage([
    { top: 0, bottom: 100 },
    { top: 600, bottom: 700 }
  ], { top: 250, bottom: 450 }), 1);
});
