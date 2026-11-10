/**
 * Date and Time utilities for HandoverLedger.
 * Formats timestamps in the viewer's local time zone with a clear format
 * (e.g. "10 Nov 2026, 10:23 am IST") and provides an exact ISO UTC string for tooltips.
 */

export function formatLocalDateTime(dateInput?: string | Date | null): { display: string; iso: string } {
  if (!dateInput) {
    return { display: '—', iso: '' };
  }
  const date = typeof dateInput === 'string' ? new Date(dateInput) : dateInput;
  if (isNaN(date.getTime())) {
    return { display: String(dateInput), iso: '' };
  }

  // Format in user's local timezone: "10 Nov 2026, 10:23 am IST"
  try {
    const options: Intl.DateTimeFormatOptions = {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
      timeZoneName: 'short',
    };
    const display = new Intl.DateTimeFormat(undefined, options).format(date);
    const iso = date.toISOString();
    return { display, iso };
  } catch {
    return { display: date.toLocaleString(), iso: date.toISOString() };
  }
}

export function formatLocalDateOnly(dateInput?: string | Date | null): string {
  if (!dateInput) return '—';
  const date = typeof dateInput === 'string' ? new Date(dateInput) : dateInput;
  if (isNaN(date.getTime())) return String(dateInput);
  try {
    return new Intl.DateTimeFormat(undefined, {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    }).format(date);
  } catch {
    return date.toLocaleDateString();
  }
}
