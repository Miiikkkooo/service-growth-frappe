import frappe
from frappe.utils import getdate, nowdate, add_days
from service_growth.analytics import aggregate

@frappe.whitelist()
def get_growth(from_date=None, to_date=None, city=None, grain="day"):
    if frappe.session.user == "Guest" or not set(frappe.get_roles()).intersection({"Growth Viewer", "Growth Manager", "System Manager"}):
        frappe.throw("无增长分析权限", frappe.PermissionError)
    frappe.has_permission("Service Record", "read", throw=True)
    start, end = getdate(from_date or nowdate()), getdate(to_date or nowdate())
    if end > getdate(nowdate()):
        frappe.throw("结束日期不能晚于今天")
    if end < start or (end-start).days > 366 or grain not in ("day", "month"):
        frappe.throw("请选择不超过367个自然日的有效日期范围和汇总粒度")
    # get_list preserves Frappe row-level/user permissions; never use get_all here.
    # Fetch history, not just selected-period starts, to compute opening stock and returners.
    filters = {"opened_at": ["<", str(add_days(end, 1)) + " 00:00:00"]}
    city = city.strip() if isinstance(city, str) else city
    if city:
        filters["city"] = city
    records = frappe.get_list("Service Record", filters=filters, fields=["user_id", "service_id", "city", "channel", "opened_at", "closed_at", "churn_reason", "is_mock"], limit_page_length=50001)
    if len(records) > 50000:
        frappe.throw("演示版支持最多50000条历史服务记录，请缩小城市范围或使用预聚合方案")
    # A visible fragment of a user's history is insufficient for user-level metrics.
    # Only compare counts; never return hidden records or identifiers to the caller.
    visible_by_user = {}
    for row in records:
        visible_by_user[row.user_id] = visible_by_user.get(row.user_id, 0) + 1
    users = list(visible_by_user)
    for offset in range(0, len(users), 500):
        full_counts = frappe.get_all("Service Record", filters={"user_id": ["in", users[offset:offset+500]], "opened_at": filters["opened_at"]}, fields=["user_id", "count(name) as total"], group_by="user_id")
        if any(int(row.total) != visible_by_user[row.user_id] for row in full_counts):
            frappe.throw("当前权限只覆盖部分用户历史，无法准确统计。请联系管理员按完整用户历史授权", frappe.PermissionError)
    return aggregate(records, start, end, city, grain)
