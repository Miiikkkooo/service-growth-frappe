import frappe
from frappe.model.document import Document
from frappe.utils import get_datetime, now_datetime

class ServiceRecord(Document):
    def validate(self):
        for field in ("user_id", "service_id", "city"):
            value = (self.get(field) or "").strip()
            if not value or len(value) > 100:
                frappe.throw("用户、服务与城市须为1—100个字符")
            self.set(field, value)
        start = get_datetime(self.opened_at)
        end = get_datetime(self.closed_at) if self.closed_at else None
        if end and end <= start:
            frappe.throw("关闭时间必须晚于开通时间")
        if start > now_datetime() or (end and end > now_datetime()):
            frappe.throw("只记录已发生的服务变化，不接受未来时间")
        if end and not self.churn_reason:
            frappe.throw("关闭服务时必须填写原因")
        if not end:
            self.churn_reason = None
        # Serialize demo writes using a metadata row; the lock lasts until commit.
        # Redis lock alone would release before commit and allow conflicting writes.
        frappe.db.multisql({"mariadb": "SELECT name FROM `tabDocType` WHERE name=%s FOR UPDATE", "postgres": 'SELECT name FROM "tabDocType" WHERE name=%s FOR UPDATE'}, ("Service Record",))
        records = frappe.db.multisql({
            "mariadb": "SELECT service_id, city, channel, opened_at, closed_at FROM `tabService Record` WHERE user_id=%s AND name!=%s FOR UPDATE",
            "postgres": 'SELECT service_id, city, channel, opened_at, closed_at FROM "tabService Record" WHERE user_id=%s AND name!=%s FOR UPDATE'
        }, (self.user_id, self.name or ""), as_dict=True)
        for row in records:
            if row.city != self.city or row.channel != self.channel:
                frappe.throw("同一用户的归属城市与获客渠道须保持一致")
            if row.service_id == self.service_id:
                other_end = get_datetime(row.closed_at) if row.closed_at else None
                if (end is None or get_datetime(row.opened_at) < end) and (other_end is None or start < other_end):
                    frappe.throw("同一用户同一服务的有效周期不能重叠")
