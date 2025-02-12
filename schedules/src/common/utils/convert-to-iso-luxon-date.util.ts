import { DateTime } from 'luxon';

/**
 *
 * @param dateStr date in string representation
 * @returns if dateStr is valid date in ISO format it returns DateTime from luxon library else it returns that string
 */
export function convertToISOLuxonDate(dateStr: string): DateTime | false {
  const date = DateTime.fromISO(dateStr);

  if (!date.isValid) {
    return false;
  } else {
    return date;
  }
}
