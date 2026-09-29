import test from 'node:test';
import assert from 'node:assert/strict';
import { buildWorkstationUrl, readWorkstationRoute } from './workstationRoute.js';

test('parses assistant petition and audit routes for users and admins', () => {
  assert.deepEqual(readWorkstationRoute({ search: '?view=assistant&petition=source-123' }, false), { module: 'gdp', sourceId: 'source-123' });
  assert.deepEqual(readWorkstationRoute({ search: '?view=audit' }, true), { module: 'audit', sourceId: null });
  assert.deepEqual(readWorkstationRoute({ search: '' }, true), { module: 'dashboard', sourceId: null });
});

test('builds reloadable routes and removes stale petition ids when leaving assistant', () => {
  assert.equal(buildWorkstationUrl('http://localhost/?view=audit', 'gdp', 'source-123'), '/?view=assistant&petition=source-123');
  assert.equal(buildWorkstationUrl('http://localhost/?view=assistant&petition=source-123', 'audit'), '/?view=audit');
});
