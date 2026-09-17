import test from 'node:test';
import assert from 'node:assert/strict';
import { createBackup, emptyAdminState, filterUsers, loadAdminState, restoreBackup, userRecord, validateUser, withActivity } from './adminModel.js';

const form = () => ({ name: 'Test Officer', mobile: '+91 90000 00000', email: 'officer@example.test', department: 'Revenue', role: 'Department User', status: 'Active', password: 'sample-password', confirmPassword: 'sample-password' });

test('add/edit validation handles duplicate emails and optional password changes', () => {
  const first = userRecord(form());
  assert.equal(validateUser(form(), []), '');
  assert.match(validateUser({ ...form(), email: ' OFFICER@EXAMPLE.TEST ' }, [first]), /already in use/);
  assert.equal(validateUser({ ...first, password: '', confirmPassword: '' }, [first]), '');
  assert.match(validateUser({ ...first, password: 'new-password', confirmPassword: '' }, [first]), /do not match/);
  assert.match(validateUser({ ...form(), mobile: 'abc1234567890' }, []), /mobile number/);
  assert.match(validateUser({ ...form(), department: '   ' }, []), /section/);
});

test('credential fields and unrecognized properties never enter a user record or backup', () => {
  const record = userRecord({ ...form(), currentPassword: 'secret', unexpected: 'value' });
  const state = { ...emptyAdminState(), users: [record] };
  const json = JSON.stringify(createBackup(state));
  assert.equal(record.email, 'officer@example.test');
  assert.doesNotMatch(json, /password|secret|unexpected/i);
  assert.equal(record.lastLogin, null);
});

test('search and filters combine rather than overriding each other', () => {
  const users = [userRecord(form()), userRecord({ ...form(), name: 'Second Officer', department: 'Health', status: 'Inactive', email: 'second@example.test' })];
  assert.equal(filterUsers(users, { search: 'OFFICER', department: 'Revenue', role: 'Department User', status: 'Active' }).length, 1);
  assert.equal(filterUsers(users, { search: 'second', department: 'Revenue', role: '', status: '' }).length, 0);
});

test('backup snapshots are independent and restore preserves catalogue and activity', () => {
  const state = { ...emptyAdminState(), users: [userRecord(form())] };
  const backup = createBackup(state);
  state.users[0].name = 'Changed';
  assert.equal(backup.snapshot.users[0].name, 'Test Officer');
  const current = withActivity({ ...state, backups: [backup] }, 'UPDATE', 'Changed name');
  const restored = restoreBackup(current, backup);
  assert.equal(restored.users[0].name, 'Test Officer');
  assert.equal(restored.backups.length, 1);
  assert.equal(restored.activity.length, 2);
  restored.users[0].name = 'Changed again';
  assert.equal(backup.snapshot.users[0].name, 'Test Officer');
});

test('no fabricated records on a fresh session and unreadable data is not silently discarded', () => {
  assert.deepEqual(loadAdminState({ getItem: () => null }), emptyAdminState());
  assert.throws(() => loadAdminState({ getItem: () => '{broken' }));
  assert.throws(() => loadAdminState({ getItem: () => '{"users":[]}' }));
});

test('preview activity stays bounded', () => {
  let state = emptyAdminState();
  for (let index = 0; index < 60; index++) state = withActivity(state, 'UPDATE', String(index));
  assert.equal(state.activity.length, 50);
  assert.equal(state.activity[0].detail, '59');
});
