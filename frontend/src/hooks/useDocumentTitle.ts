import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

const APP_TITLE = 'Traxe';

/** Route path patterns to page title (order matters: more specific first) */
const ROUTE_TITLES: { pattern: RegExp | string; title: string }[] = [
  { pattern: '/', title: 'Dashboard' },
  { pattern: '/products/new', title: 'New parent' },
  { pattern: /^\/products\/\d+$/, title: 'Parent' },
  { pattern: '/products', title: 'Parents' },
  { pattern: '/variants', title: 'Products' },
  { pattern: /^\/groups\/\d+$/, title: 'Marketplace listing' },
  { pattern: '/groups', title: 'Marketplace listings' },
  { pattern: '/imports/new', title: 'New import' },
  { pattern: /^\/imports\/[^/]+\/map-attributes$/, title: 'Map attributes' },
  { pattern: /^\/imports\/[^/]+\/assign-category$/, title: 'Assign category' },
  { pattern: /^\/imports\/\d+$/, title: 'Import' },
  { pattern: '/imports', title: 'Raw Data – Import' },
  { pattern: '/translations/new', title: 'New translation' },
  { pattern: /^\/translations\/\d+$/, title: 'Translation' },
  { pattern: '/translations', title: 'Raw Data – Translation' },
  { pattern: '/keywords/saved-terms', title: 'Raw Data – Saved terms' },
  { pattern: '/keywords/new', title: 'Keyword run' },
  { pattern: /^\/keywords\/\d+\/mappings$/, title: 'Keyword mappings' },
  { pattern: /^\/keywords\/\d+$/, title: 'Keyword' },
  { pattern: '/keywords', title: 'Raw Data – Google Ads keywords' },
  { pattern: '/content/new', title: 'Generate content' },
  { pattern: '/content/generate-titles', title: 'Listings – Generate titles' },
  { pattern: '/content/generated-titles', title: 'Listings – Generated titles' },
  { pattern: '/content', title: 'Listings – Content' },
  { pattern: '/exports/new', title: 'New export' },
  { pattern: '/exports', title: 'Exports' },
  { pattern: '/attributes/new', title: 'New attribute' },
  { pattern: /^\/attributes\/\d+\/edit$/, title: 'Edit attribute' },
  { pattern: '/attributes', title: 'Attributes' },
  { pattern: '/templates/new', title: 'Create title template' },
  { pattern: /^\/templates\/\d+\/edit$/, title: 'Edit title template' },
  { pattern: '/templates', title: 'Listings – Title templates' },
  { pattern: '/settings', title: 'Settings' },
  { pattern: '/auth', title: 'Sign in' },
];

function matchTitle(pathname: string): string {
  for (const { pattern, title } of ROUTE_TITLES) {
    if (typeof pattern === 'string') {
      if (pathname === pattern || (pattern !== '/' && pathname.startsWith(pattern + '/'))) return title;
    } else {
      if (pattern.test(pathname)) return title;
    }
  }
  return 'Traxe';
}

/**
 * Sets document.title from the current route using a title template: "{Page} | Traxe".
 * Renders nothing; use inside BrowserRouter (e.g. in App).
 */
export function useDocumentTitle(): void {
  const { pathname } = useLocation();

  useEffect(() => {
    const pageTitle = matchTitle(pathname);
    const fullTitle = pageTitle ? `${pageTitle} | ${APP_TITLE}` : APP_TITLE;
    document.title = fullTitle;
    return () => {
      document.title = APP_TITLE;
    };
  }, [pathname]);
}

/** Component that syncs document title to the current route. Render once inside BrowserRouter. */
export function DocumentTitle() {
  useDocumentTitle();
  return null;
}

export { APP_TITLE };
