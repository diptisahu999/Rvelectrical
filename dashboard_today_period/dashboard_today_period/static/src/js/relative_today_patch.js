/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { RELATIVE_DATE_RANGE_TYPES } from "@spreadsheet/helpers/constants";
import * as dateHelpers from "@spreadsheet/global_filters/helpers";
import { serializeDate, serializeDateTime } from "@web/core/l10n/dates";
import { Domain } from "@web/core/domain";

// Ensure idempotency if assets are reloaded multiple times
if (!RELATIVE_DATE_RANGE_TYPES.some((t) => t.type === "today")) {
  const todayType = { type: "today", description: _t("Today") };
  const ytdIndex = RELATIVE_DATE_RANGE_TYPES.findIndex(
    (t) => t.type === "year_to_date"
  );
  if (ytdIndex >= 0) {
    RELATIVE_DATE_RANGE_TYPES.splice(ytdIndex + 1, 0, todayType);
  } else {
    RELATIVE_DATE_RANGE_TYPES.unshift(todayType);
  }
}

// Patch getRelativeDateDomain to support "today"
if (!dateHelpers.__patched_today_relative_range__) {
  const original = dateHelpers.getRelativeDateDomain;
  dateHelpers.getRelativeDateDomain = function (
    now,
    offset,
    rangeType,
    fieldName,
    fieldType
  ) {
    if (rangeType === "today") {
      const offsetParam = { days: offset || 0 };
      const startDate = now.startOf("day").plus(offsetParam);
      const endDate = now.endOf("day").plus(offsetParam);
      const leftBound =
        fieldType === "date"
          ? serializeDate(startDate)
          : serializeDateTime(startDate);
      const rightBound =
        fieldType === "date"
          ? serializeDate(endDate)
          : serializeDateTime(endDate);
      return new Domain([
        "&",
        [fieldName, ">=", leftBound],
        [fieldName, "<=", rightBound],
      ]);
    }
    return original
      ? original(now, offset, rangeType, fieldName, fieldType)
      : undefined;
  };
  dateHelpers.__patched_today_relative_range__ = true;
}
