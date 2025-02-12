import { DateTime } from 'luxon';

import { convertToISOLuxonDate } from './convert-to-iso-luxon-date.util';

describe('convertToISOLuxonDate', () => {
  it('should return date object of given string if valid', () => {
    const dateStr = '2025-01-23T13:27:00Z';

    expect(convertToISOLuxonDate(dateStr)).toStrictEqual(
      DateTime.fromISO(dateStr),
    );
  });

  it('should return string if it is not valid date string', () => {
    const invalidDateStr = '10 * * * * *';

    expect(convertToISOLuxonDate(invalidDateStr)).toBe(false);
  });
});
