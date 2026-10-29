"""Deterministic synthetic dataset. Explicit opt-in; never silently seeds production."""
import random
from datetime import datetime, timedelta

CITIES = ["杭州", "宁波", "温州", "嘉兴", "绍兴", "金华"]
CHANNELS = ["线上推广", "线下门店", "用户推荐", "合作渠道"]
REASONS = ["价格因素", "服务体验", "需求结束", "迁移离开", "其他"]

def make_records(anchor="2026-10-29", users=360):
    rng = random.Random(20261029)
    anchor = datetime.fromisoformat(str(anchor)).replace(hour=0, minute=0, second=0, microsecond=0)
    data = []
    for i in range(users):
        city, channel = rng.choice(CITIES), rng.choice(CHANNELS)
        start = anchor - timedelta(days=rng.randint(0,180), hours=rng.randint(0,23))
        end = start + timedelta(days=rng.randint(8,65)) if rng.random()<.48 else None
        if end and end >= anchor:
            end = None
        base = dict(user_id=f"DEMO-{i+1:04d}", city=city, channel=channel, is_mock=1)
        def add(s,e,service="电池服务"):
            data.append(dict(base, service_id=service, opened_at=s, closed_at=e, churn_reason=rng.choice(REASONS) if e else None))
        add(start,end)
        if end and end + timedelta(days=10) < anchor and rng.random()<.55:
            add(end+timedelta(days=10),None)
        if rng.random()<.2 and start+timedelta(days=2) < anchor:
            add(start+timedelta(days=2),end,"换电服务")
    return data

def seed(anchor=None):
    import frappe
    from frappe.utils import nowdate, getdate
    if frappe.session.user != "Administrator":
        frappe.throw("合成数据导入仅限Administrator", frappe.PermissionError)
    anchor = anchor or "2026-10-29"
    if getdate(anchor) > getdate(nowdate()):
        frappe.throw("演示数据锚点不能晚于今天")
    rows = make_records(anchor)
    existing = frappe.get_all("Service Record", filters={"user_id":["like","DEMO-%"]}, fields=["name","user_id","service_id","opened_at","closed_at","city","channel","churn_reason","is_mock"])
    from service_growth.analytics import dt
    keys = {(r.user_id,r.service_id,dt(r.opened_at)) for r in existing if r.is_mock}
    if any(not r.is_mock for r in existing):
        frappe.throw("DEMO前缀与非合成记录冲突，已停止导入")
    expected = {(r["user_id"],r["service_id"],r["opened_at"]) for r in rows}
    expected_rows = {(r["user_id"],r["service_id"],r["opened_at"]): r for r in rows}
    changed = len(existing) != len(keys)
    for current in existing:
        target = expected_rows.get((current.user_id,current.service_id,dt(current.opened_at)))
        if target:
            changed = changed or any((current.get(k) or "") != (target.get(k) or "") for k in ("city","channel","churn_reason"))
            changed = changed or ((dt(current.closed_at) if current.closed_at else None) != target["closed_at"])
    if changed or (keys and not keys.issubset(expected)):
        frappe.throw("已有其他锚点或被修改的合成记录；为保护数据，本次停止导入。请使用独立演示站点")
    count = 0
    for row in rows:
        key = (row["user_id"],row["service_id"],row["opened_at"])
        if key not in keys:
            frappe.get_doc(dict(row,doctype="Service Record")).insert()
            keys.add(key)
            count += 1
    return {"inserted":count,"anchor":str(anchor),"synthetic":True}
