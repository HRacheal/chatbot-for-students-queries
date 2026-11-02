// Shared labels and helpers for enquiries and degree guidance.

// Same departments as the backend (services/sources.py DEPARTMENTS); Finance is separate from Admissions.
export const ENQUIRY_DEPARTMENTS = {
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

// Same statuses as the backend (services/enquiry_service.py STATUSES).
export const ENQUIRY_STATUS_LABELS = {
  new: 'New',
  pending: 'Pending',
  in_progress: 'In Progress',
  awaiting_response: 'Awaiting Response',
  resolved: 'Resolved',
  closed: 'Closed',
};

export const OPEN_ENQUIRY_STATUSES = ['new', 'pending', 'in_progress', 'awaiting_response'];
export const ATTENTION_ENQUIRY_STATUSES = ['new', 'pending'];

// Badge styles; each badge also shows its text label, so colour is never the only cue.
export const ENQUIRY_STATUS_STYLES = {
  new: 'bg-sky-500/15 text-sky-200 ring-1 ring-sky-400/40',
  pending: 'bg-amber-500/15 text-amber-200 ring-1 ring-amber-400/40',
  in_progress: 'bg-indigo-500/15 text-indigo-200 ring-1 ring-indigo-400/40',
  awaiting_response: 'bg-fuchsia-500/15 text-fuchsia-200 ring-1 ring-fuchsia-400/40',
  resolved: 'bg-emerald-500/15 text-emerald-200 ring-1 ring-emerald-400/40',
  closed: 'bg-slate-500/20 text-slate-300 ring-1 ring-slate-400/30',
};

// Who is asking (optional; asked only when someone sends an enquiry to staff).
export const USER_GROUPS = {
  current_student: 'Current student',
  prospective_student: 'Prospective student',
  parent_guardian: 'Parent or guardian',
  faculty: 'Faculty member',
  staff: 'University administrator or staff',
  other: 'Other',
};

export const ROLE_LABELS = {
  super_admin: 'Super Administrator',
  department_admin: 'Department Administrator',
  department_staff: 'Department Staff',
};

export const CONSENT_TEXT =
  'I agree that USIU-Africa staff may use the contact details I provide to respond to this enquiry. ' +
  'They are stored with my question and visible only to authorised staff.';

export const OUTCOME_LABELS = {
  meets_listed_requirements: { text: 'Meets the listed requirements', style: 'bg-green-800 text-green-100' },
  incomplete_information: { text: 'More information needed', style: 'bg-yellow-800 text-yellow-100' },
  below_listed_requirements: { text: 'Below the listed requirements', style: 'bg-gray-700 text-gray-200' },
};

// "Mathematics:C+; Physics|Chemistry:C" <-> [{subjects: [...], min_grade}]
export const parseRules = (text) => text.split(';').map((part) => part.trim()).filter(Boolean).map((part) => {
  const [subjects, grade] = part.split(':');
  return { subjects: (subjects || '').split('|').map((s) => s.trim()).filter(Boolean), min_grade: (grade || '').trim() };
});

export const formatRules = (rules = []) => rules.map((r) => `${r.subjects.join('|')}:${r.min_grade}`).join('; ');
