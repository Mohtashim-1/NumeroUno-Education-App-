from frappe.tests.utils import FrappeTestCase

from numerouno.numerouno.doctype.overtime_request.overtime_request import compute_overtime_hours


class TestOvertimeRequest(FrappeTestCase):
    def test_regular_day_uses_actual_duration(self):
        self.assertEqual(compute_overtime_hours("2026-03-23", "18:00:00", "20:30:00"), 2.5)

    def test_sunday_short_work_returns_eight_hours(self):
        self.assertEqual(compute_overtime_hours("2026-03-22", "09:00:00", "15:00:00"), 8)

    def test_sunday_long_work_still_returns_eight_hours(self):
        self.assertEqual(compute_overtime_hours("2026-03-22", "08:00:00", "18:00:00"), 8)
