import frappe
from frappe.tests.utils import FrappeTestCase
from service_growth.api import get_growth

class TestServiceRecord(FrappeTestCase):
    def make(self, **kw):
        data=dict(doctype='Service Record',user_id='TEST-GROWTH-'+self._testMethodName,service_id='one',city='测试城市-'+self._testMethodName,channel='线上推广',opened_at='2026-01-01 00:00:00')
        data.update(kw)
        return frappe.get_doc(data).insert()

    def test_invalid_date(self):
        with self.assertRaises(frappe.ValidationError):
            self.make(closed_at='2025-12-31',churn_reason='其他')

    def test_overlap(self):
        self.make()
        with self.assertRaises(frappe.ValidationError):
            self.make(opened_at='2026-02-01')

    def test_other_service_valid(self):
        self.make()
        self.make(service_id='two')
        result=get_growth('2026-01-01','2026-01-31',city='测试城市-'+self._testMethodName)
        self.assertEqual(result['totals']['closing'],1)
        self.assertEqual(result['totals']['new'],1)

    def test_guest_denied(self):
        frappe.set_user('Guest')
        try:
            with self.assertRaises(frappe.PermissionError):
                get_growth('2026-01-01','2026-01-31')
        finally:
            frappe.set_user('Administrator')

    def test_viewer_can_read_but_cannot_create(self):
        self.make()
        user=frappe.get_doc({"doctype":"User","email":"growth-viewer@example.invalid","first_name":"Growth QA","send_welcome_email":0,"roles":[{"role":"Growth Viewer"}]}).insert(ignore_permissions=True)
        frappe.set_user(user.name)
        try:
            self.assertEqual(get_growth('2026-01-01','2026-01-31',city='测试城市-'+self._testMethodName)['totals']['closing'],1)
            with self.assertRaises(frappe.PermissionError):
                self.make(service_id='forbidden')
        finally:
            frappe.set_user('Administrator')

    def test_future_event_rejected(self):
        from frappe.utils import add_days, nowdate
        with self.assertRaises(frappe.ValidationError):
            self.make(opened_at=add_days(nowdate(),1))

    def test_attribute_conflict_rejected(self):
        self.make()
        with self.assertRaises(frappe.ValidationError):
            self.make(service_id='two',city='其他城市')
