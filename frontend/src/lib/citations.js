// Helpers for displaying source citations returned by the backend.
// The backend already validates citation URLs; the frontend checks again so a
// link is only ever rendered for https URLs on an approved USIU-Africa domain.

const DEFAULT_DOMAINS = ['usiu.ac.ke'];

export const allowedSourceDomains = () => {
  const configured = import.meta.env?.VITE_ALLOWED_SOURCE_DOMAINS;
  const domains = configured ? configured.split(',').map((d) => d.trim().toLowerCase()).filter(Boolean) : [];
  return domains.length ? domains : DEFAULT_DOMAINS;
};

export const isSafeSourceUrl = (url, domains = allowedSourceDomains()) => {
  if (typeof url !== 'string' || url.length > 2048) return false;
  let parsed;
  try {
    parsed = new URL(url);
  } catch {
    return false;
  }
  if (parsed.protocol !== 'https:' || parsed.username || parsed.password) return false;
  if (parsed.port && parsed.port !== '443') return false;
  const host = parsed.hostname.toLowerCase();
  return domains.some((d) => host === d || host.endsWith(`.${d}`));
};

// Pages fetched live and "places to look" must be on an exactly listed host
// (subdomains such as the student portal are not trusted automatically).
const DEFAULT_PAGE_HOSTS = ['www.usiu.ac.ke'];

export const trustedPageHosts = () => {
  const configured = import.meta.env?.VITE_TRUSTED_SOURCE_HOSTS;
  const hosts = configured ? configured.split(',').map((h) => h.trim().toLowerCase()).filter(Boolean) : [];
  return hosts.length ? hosts : DEFAULT_PAGE_HOSTS;
};

export const isOfficialPageUrl = (url, hosts = trustedPageHosts()) => {
  if (!isSafeSourceUrl(url, hosts)) return false;
  return hosts.includes(new URL(url).hostname.toLowerCase());
};

// The optional "unverified search" link: a web search restricted to the official site,
// opened in the user's browser only.
export const isSiteSearchUrl = (url, hosts = trustedPageHosts()) => {
  if (typeof url !== 'string' || url.length > 2048) return false;
  let parsed;
  try {
    parsed = new URL(url);
  } catch {
    return false;
  }
  const query = parsed.searchParams.get('q') || '';
  return parsed.protocol === 'https:' && parsed.hostname === 'www.google.com' && parsed.pathname === '/search'
    && hosts.some((h) => query.startsWith(`site:${h} `) || query === `site:${h}`);
};

// External bodies (e.g. KUCCPS) whose pages may be cited. They are always labelled as external.
const DEFAULT_EXTERNAL_DOMAINS = ['kuccps.net', 'cue.or.ke', 'knqa.go.ke'];

export const externalSourceDomains = () => {
  const configured = import.meta.env?.VITE_EXTERNAL_SOURCE_DOMAINS;
  const domains = configured ? configured.split(',').map((d) => d.trim().toLowerCase()).filter(Boolean) : [];
  return domains.length ? domains : DEFAULT_EXTERNAL_DOMAINS;
};

// The link to show for a citation: official sources on USIU-Africa domains, external sources
// only on a listed external domain. Anything else is shown as text.
export const citationLink = (c) => {
  if (!c || c.available === false) return null;
  if (c.external) return isSafeSourceUrl(c.url, externalSourceDomains()) ? c.url : null;
  return isSafeSourceUrl(c.url) ? c.url : null;
};

// "Student-Handbook.pdf, page 11" / "pages 2-3" plus the section heading, for dataset passages.
export const citationLocation = (c) => {
  if (!c) return null;
  const parts = [];
  if (c.document_file) parts.push(c.document_file);
  if (Number.isInteger(c.page_start)) {
    parts.push(c.page_end && c.page_end !== c.page_start ? `pages ${c.page_start}-${c.page_end}` : `page ${c.page_start}`);
  }
  if (c.section_heading && !(c.title || '').includes(c.section_heading)) parts.push(`section "${c.section_heading}"`);
  return parts.length ? parts.join(', ') : null;
};

export const CATEGORY_NAMES = {
  '01': 'General University Information',
  '02': 'Academic Programmes',
  '03': 'Admissions and Applications',
  '04': 'Fees and Payments',
  '05': 'Registrar and Academic Administration',
  '06': 'Department Contacts and Query Routing',
  '07': 'Academic Documents, Results and Verified Eligibility',
  '08': 'Questions, Answers and Unresolved Enquiries',
};

export const ORIGIN_LABELS = {
  live: 'retrieved live from the official website',
  staff_answer: 'answer from USIU staff',
  approved_source: 'approved source',
};

export const DEPARTMENT_LABELS = {
  admissions: 'Admissions',
  registrar: 'Registrar',
  finance: 'Finance',
  academic_programmes: 'Academic Programmes',
  marketing: 'Marketing',
  student_affairs: 'Student Affairs',
  ict: 'ICT',
  library: 'Library',
  general_university: 'General University Information',
};

export const departmentLabel = (value) => DEPARTMENT_LABELS[value] || 'General';

// "2025" / "2025-09" / "2025-09-30" are shown as given; ISO timestamps as a date.
export const formatSourceDate = (value) => {
  if (!value || typeof value !== 'string') return null;
  return value.length > 10 ? value.slice(0, 10) : value;
};
