const SUPPORTED_MODULES = new Set(['gdp', 'audit', 'dashboard', 'users', 'backup', 'profile']);

export function readWorkstationRoute(location, isAdmin = false) {
  const params = new URLSearchParams(location?.search || '');
  const sourceId = params.get('petition');
  const routeView = params.get('view');
  const requestedModule = routeView === 'assistant' ? 'gdp' : routeView;
  const fallbackModule = isAdmin ? 'dashboard' : 'gdp';

  return {
    module: sourceId ? 'gdp' : (SUPPORTED_MODULES.has(requestedModule) ? requestedModule : fallbackModule),
    sourceId
  };
}

export function buildWorkstationUrl(currentUrl, module, sourceId = null) {
  const url = new URL(currentUrl);
  url.searchParams.set('view', module === 'gdp' ? 'assistant' : module);
  if (module === 'gdp' && sourceId) url.searchParams.set('petition', sourceId);
  else url.searchParams.delete('petition');
  return `${url.pathname}${url.search}${url.hash}`;
}
