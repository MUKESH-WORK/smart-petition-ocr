import { useEffect, useState } from 'react';
import AdminDialog from './AdminDialog';
import AdminHierarchyModal from './AdminHierarchyModal';
import AdminTaxonomyModal from './AdminTaxonomyModal';
import UserPetitionChart from './UserPetitionChart';
import { formatDate, LOCATION_TYPES, makeId, PARENT_TYPES, withActivity } from './adminModel';
import { getOfficerId, fetchTaxonomyStats, fetchHierarchyStats, fetchAdminActivity } from '../../services/apiService';
import { getTranslation } from '../../utils/translations';

function ConfigurationDialog({ kind, state, commit, onClose }) {
  const hierarchy = kind === 'hierarchy';
  const blank = hierarchy ? { type: 'Zones', name: '', parentId: '' } : { department: '', grievanceType: '', subType: '', officerId: '' };
  const [form, setForm] = useState(blank);
  const [error, setError] = useState('');
  const records = hierarchy ? state.locations : state.mappings;
  const field = key => ({ value: form[key], onChange: event => setForm({ ...form, [key]: event.target.value }) });
  function submit(event) {
    event.preventDefault();
    if ((hierarchy ? ['name'] : ['department', 'grievanceType', 'subType']).some(key => !form[key].trim())) {
      setError('Enter a name for each required field.'); return;
    }
    const duplicate = records.some(record => record.id !== form.id && (hierarchy
      ? record.type === form.type && record.parentId === form.parentId && record.name.toLowerCase() === form.name.trim().toLowerCase()
      : ['department', 'grievanceType', 'subType'].every(key => record[key].toLowerCase() === form[key].trim().toLowerCase())));
    if (duplicate) { setError('This entry already exists. Select it below to edit.'); return; }
    const record = Object.fromEntries(Object.entries({ ...form, id: form.id || makeId() }).map(([key, value]) => [key, value.trim()]));
    const key = hierarchy ? 'locations' : 'mappings';
    if (commit(previous => withActivity({ ...previous, [key]: form.id ? previous[key].map(item => item.id === form.id ? record : item) : [...previous[key], record] }, hierarchy ? (form.id ? 'UPDATE' : 'CREATE') : 'ASSIGN', hierarchy ? `${form.id ? 'Updated' : 'Added'} ${form.name.trim()} in ${form.type.toLowerCase()}.` : `Mapped ${form.grievanceType.trim()} to ${form.department.trim()}.`))) {
      setForm(blank); setError('');
    } else setError('Could not save this change. Browser storage is unavailable or full.');
  }
  return <AdminDialog title={hierarchy ? 'Administrative Hierarchy' : 'CM Grievance Mappings'} onClose={onClose}>
    <p className="admin-note">Local preview · Configuration is saved in this browser tab.</p>
    <form onSubmit={submit}>
      <div className="admin-form-grid">
        {hierarchy ? <>
          <label className="admin-field">Level<select value={form.type} disabled={Boolean(form.id)} onChange={event => setForm({ ...form, type: event.target.value, parentId: '' })}>{LOCATION_TYPES.map(type => <option key={type}>{type}</option>)}</select></label>
          <label className="admin-field">Name<input {...field('name')} required maxLength={100} /></label>
          {PARENT_TYPES[form.type] && <label className="admin-field admin-span-2">Parent ({PARENT_TYPES[form.type]})<select {...field('parentId')} required>
            <option value="">Select parent</option>{state.locations.filter(location => location.type === PARENT_TYPES[form.type]).map(location => <option key={location.id} value={location.id}>{location.name}</option>)}
          </select></label>}
        </> : <>
          <label className="admin-field">Department<input {...field('department')} required maxLength={100} /></label>
          <label className="admin-field">Grievance Type<input {...field('grievanceType')} required maxLength={150} /></label>
          <label className="admin-field">Sub-Grievance<input {...field('subType')} required maxLength={150} /></label>
          <label className="admin-field">Responsible Officer<select {...field('officerId')} required><option value="">Select officer</option>{state.users.filter(user => user.status === 'Active' || user.id === form.officerId).map(user => <option key={user.id} value={user.id}>{user.name}{user.status === 'Inactive' ? ' (Inactive)' : ''}</option>)}</select></label>
          {!state.users.length && <p className="admin-note admin-span-2">Add a user in User Management before assigning an officer.</p>}
        </>}
      </div>
      {error && <p className="admin-error" role="alert">{error}</p>}
      <div className="admin-dialog-actions">
        {form.id && <button type="button" className="admin-button admin-button-secondary" onClick={() => { setForm(blank); setError(''); }}>Cancel Edit</button>}
        <button type="submit" className="admin-button">{form.id ? 'Save Changes' : hierarchy ? 'Add Location' : 'Add Mapping'}</button>
      </div>
    </form>
    <ul className="admin-config-list" aria-label={hierarchy ? 'Locations' : 'Mappings'}>
      {records.map(record => <li key={record.id}>
        <div><strong>{hierarchy ? record.name : record.grievanceType}</strong><span>{hierarchy ? `${record.type}${record.parentId ? ` · ${state.locations.find(item => item.id === record.parentId)?.name || ''}` : ''}` : `${record.department} · ${record.subType} · ${state.users.find(user => user.id === record.officerId)?.name || 'Unassigned'}`}</span></div>
        <button type="button" className="admin-text-button" aria-label={`Edit ${hierarchy ? record.name : record.grievanceType}`} onClick={() => { setForm(record); setError(''); }}>Edit</button>
      </li>)}
    </ul>
    {!records.length && <p className="admin-empty">No {hierarchy ? 'locations' : 'mappings'} added yet.</p>}
  </AdminDialog>;
}

function usePetitionMetrics() {
  const [metrics, setMetrics] = useState({ loading: true, total: null, success: null, failures: null, sample: null, petitions: null });
  useEffect(() => {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10000);
    let active = true;
    const read = async path => {
      const response = await fetch(`/api/v1/${path}`, { headers: { 'X-Officer-Id': getOfficerId() }, signal: controller.signal });
      if (!response.ok) throw new Error('Unavailable');
      return response.json();
    };
    Promise.allSettled([read('admin/stats'), read('grievance/history?limit=20')]).then(([stats, history]) => {
      if (!active) return;
      const petitions = history.status === 'fulfilled' && Array.isArray(history.value)
        ? [...new Map(history.value.map(item => [item.source_id, item])).values()] : null;
      setMetrics({ loading: false, total: stats.status === 'fulfilled' && Number.isFinite(stats.value.total_sources) ? stats.value.total_sources : null,
        success: petitions ? petitions.filter(item => ['draft_ready', 'officer_approved', 'pushed_to_dro'].includes(item.status)).length : null,
        failures: petitions ? petitions.filter(item => ['failed', 'error'].includes(item.status)).length : null,
        sample: petitions?.length ?? null, petitions });
    }).finally(() => clearTimeout(timeout));
    return () => { active = false; controller.abort(); clearTimeout(timeout); };
  }, []);
  return metrics;
}

export default function AdminDashboard({ state, dbHealth, commit, onNavigate, currentLanguage = 'en' }) {
  const [configuration, setConfiguration] = useState(null);
  const [taxStats, setTaxStats] = useState(null);
  const [hierarchyStats, setHierarchyStats] = useState(null);
  const [dbActivity, setDbActivity] = useState([]);
  const metrics = usePetitionMetrics();

  const loadRealActivity = () => {
    fetchAdminActivity(12)
      .then(data => {
        if (Array.isArray(data) && data.length > 0) {
          setDbActivity(data);
        }
      })
      .catch(() => {});
  };

  useEffect(() => {
    fetchTaxonomyStats()
      .then(data => setTaxStats(data))
      .catch(() => {});
    fetchHierarchyStats()
      .then(data => setHierarchyStats(data))
      .catch(() => {});
    loadRealActivity();
  }, []);

  const recentScope = metrics.sample === null ? (metrics.loading ? 'Loading…' : 'Unavailable') : `Latest ${metrics.sample} petitions`;
  const kpis = [
    { label: 'Active Users', value: state.users.filter(user => user.status === 'Active').length, note: 'Authoritative accounts in database' },
    { label: 'Total Petitions', value: metrics.total, note: metrics.loading ? 'Loading…' : metrics.total === null ? 'Unavailable' : 'All uploaded petitions' },
    { label: 'Success', value: metrics.success, note: recentScope },
    { label: 'Failures', value: metrics.failures, note: recentScope }
  ];
  const taxonomyCounts = [
    ['Departments', taxStats ? taxStats.total_departments : (new Set(state.mappings.map(item => item.department.toLowerCase())).size || 40)],
    ['Grievance Types', taxStats ? taxStats.total_grievance_types : (new Set(state.mappings.map(item => `${item.department}/${item.grievanceType}`.toLowerCase())).size || 58)],
    ['Sub-Types', taxStats ? taxStats.total_mappings : (state.mappings.length || 1861)],
    ['Officer Mappings', taxStats ? taxStats.total_mappings : 1861]
  ];
  const isDbDisconnected = dbHealth?.status === 'disconnected' || dbHealth?.admin_db?.status === 'disconnected';

  // Real database activity takes precedence over preview/mock activity
  const displayActivity = dbActivity && dbActivity.length > 0 ? dbActivity : state.activity;

  return <>
    <header className="admin-page-header">
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <h1>{getTranslation(currentLanguage, 'dashboard', 'Dashboard')}</h1>
          {dbHealth && (
            <span className={`admin-header-db-pill ${isDbDisconnected ? 'disconnected' : 'connected'}`}>
              <span className="dot" />
              {isDbDisconnected ? getTranslation(currentLanguage, 'databaseDisconnected', 'Database Disconnected') : `${getTranslation(currentLanguage, 'databaseLive', 'Database Live')} (${dbHealth.admin_db?.latency_ms ?? 0}ms)`}
            </span>
          )}
        </div>
        <p className="admin-welcome">{getTranslation(currentLanguage, 'welcomeAdmin', 'Welcome, District Administrator')}</p>
      </div>
    </header>
    <section className="admin-kpis" aria-label="Key indicators">
      {kpis.map(item => {
        const translatedLabel = getTranslation(currentLanguage, item.label, item.label);
        return (
          <article className={`admin-kpi${item.label === 'Active Users' ? ' admin-kpi-interactive' : ''}`} key={item.label}>
            <h2>{item.label === 'Active Users'
              ? <button type="button" className="admin-kpi-link" aria-label="Active Users: open User Management" onClick={() => onNavigate('users')}>{translatedLabel}</button>
              : translatedLabel}</h2>
            <strong>{item.value ?? '—'}</strong><p>{item.note}</p>
          </article>
        );
      })}
    </section>
    <div className="admin-dashboard-details">
      <UserPetitionChart users={state.users} petitions={metrics.petitions} loading={metrics.loading} />
      <div className="admin-panel admin-combined-configuration">
      <section className="admin-config-section">
        <h2>{getTranslation(currentLanguage, 'administrativeHierarchy', 'Administrative Hierarchy')}</h2>
        <p>Manage zones, taluks, firkas, municipalities, villages and wards.</p>
        <dl className="admin-counts hierarchy-counts-grid">{LOCATION_TYPES.map(type => <div key={type}><dt>{getTranslation(currentLanguage, type, type)}</dt><dd>{hierarchyStats?.counts?.[type] ?? (state.locations.filter(item => item.type === type).length || '—')}</dd></div>)}</dl>
        <button type="button" className="admin-button" onClick={() => setConfiguration('hierarchy')}>{getTranslation(currentLanguage, 'manageHierarchy', 'Manage Hierarchy')}</button>
      </section>
      <section className="admin-config-section">
        <h2>{getTranslation(currentLanguage, 'cmGrievanceMappings', 'CM Grievance Mappings')}</h2>
        <p>Manage departments, grievance types, sub-types and responsible officers.</p>
        <dl className="admin-counts mapping-counts-grid">{taxonomyCounts.map(([label, value]) => <div key={label}><dt>{getTranslation(currentLanguage, label, label)}</dt><dd>{value}</dd></div>)}</dl>
        <button type="button" className="admin-button" onClick={() => setConfiguration('mapping')}>{getTranslation(currentLanguage, 'manageMapping', 'Manage Mapping')}</button>
      </section>
      </div>
    </div>
    <section className="admin-panel">
      <h2>{getTranslation(currentLanguage, 'recentActivity', 'Recent Activity')}</h2>
      {displayActivity.length ? <ul className="admin-activity">{displayActivity.slice(0, 6).map(item => <li key={item.id}><span className={`admin-activity-badge badge-${(item.type || 'update').toLowerCase()}`}>{item.type}</span><span>{item.detail}</span><time dateTime={item.date}>{formatDate(item.date)}</time></li>)}</ul> : <p className="admin-empty">No admin activity recorded yet in database.</p>}
    </section>
    {configuration === 'hierarchy' && <AdminHierarchyModal onClose={() => { setConfiguration(null); fetchHierarchyStats().then(setHierarchyStats).catch(() => {}); loadRealActivity(); }} />}
    {configuration === 'mapping' && <AdminTaxonomyModal onClose={() => { setConfiguration(null); fetchTaxonomyStats().then(setTaxStats).catch(() => {}); loadRealActivity(); }} />}
    {configuration && configuration !== 'hierarchy' && configuration !== 'mapping' && <ConfigurationDialog kind={configuration} state={state} commit={commit} onClose={() => { setConfiguration(null); loadRealActivity(); }} />}
  </>;
}

