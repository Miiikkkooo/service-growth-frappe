"""Pure analytics: merge service intervals before counting user state transitions."""
from collections import defaultdict, Counter
from datetime import datetime, date, time, timedelta


def dt(value):
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def aggregate(records, from_date, to_date, city=None, grain="day"):
    begin, last = date.fromisoformat(str(from_date)), date.fromisoformat(str(to_date))
    if last < begin or (last - begin).days > 366:
        raise ValueError("日期范围须为0—366天差值，且结束不早于开始")
    if grain not in ("day", "month"):
        raise ValueError("汇总粒度须为day或month")
    left, right = datetime.combine(begin, time.min), datetime.combine(last + timedelta(days=1), time.min)
    users = defaultdict(list)
    attrs = {}
    for r in records:
        if city and r["city"] != city:
            continue
        uid = r["user_id"]
        attrs[uid] = (r["city"], r["channel"])
        users[uid].append((dt(r["opened_at"]), dt(r["closed_at"]) if r.get("closed_at") else None, r.get("churn_reason") or "其他"))
    events, merged = [], {}
    for uid, intervals in users.items():
        result = []
        for start, end, reason in sorted(intervals, key=lambda x: x[0]):
            if not result or (result[-1][1] is not None and start > result[-1][1]):
                result.append([start, end, reason])
            elif result[-1][1] is not None and (end is None or end > result[-1][1]):
                result[-1][1:] = [end, reason]
            elif result[-1][1] is not None and end == result[-1][1] and reason != result[-1][2]:
                result[-1][2] = "多服务同时关闭"
        merged[uid] = result
        for i, (start, end, reason) in enumerate(result):
            events.append((start, "new" if i == 0 else "reactivated", uid, None))
            if end is not None:
                events.append((end, "churn", uid, reason))
    # Snapshots use the left limit at midnight: an event exactly at midnight
    # belongs to the new day and has not changed the previous day's closing stock.
    def active_before(moment):
        return {uid for uid, xs in merged.items() if any(s < moment and (e is None or e >= moment) for s,e,_ in xs)}
    opening = active_before(left)
    ending = active_before(right)
    selected = [e for e in events if left <= e[0] < right]
    buckets = {}
    cursor = begin
    while cursor <= last:
        key = cursor.isoformat() if grain == "day" else cursor.strftime("%Y-%m")
        if key not in buckets:
            buckets[key] = dict(period=key, new=0, reactivated=0, churn=0)
        cursor += timedelta(days=1)
    reasons = Counter()
    for when, kind, uid, reason in selected:
        key = when.date().isoformat() if grain == "day" else when.strftime("%Y-%m")
        buckets[key][kind] += 1
        if kind == "churn":
            reasons[reason] += 1
    stock = len(opening)
    rows = []
    for row in buckets.values():
        row["opening"] = stock
        row["net"] = row["new"] + row["reactivated"] - row["churn"]
        stock += row["net"]
        row["closing"] = stock
        rows.append(row)
    totals = {k: sum(r[k] for r in rows) for k in ("new", "reactivated", "churn", "net")}
    totals.update(opening=len(opening), closing=len(ending), churn_rate=round(len(opening-ending)/len(opening)*100, 2) if opening else None)
    assert stock == len(ending), "Growth balance violated"
    cities = Counter(attrs[u][0] for u in ending)
    channels = Counter(attrs[u][1] for u in ending)
    return dict(rows=rows, totals=totals, cities=dict(cities.most_common()), channels=dict(channels.most_common()), reasons=dict(reasons.most_common()), from_date=begin.isoformat(), to_date=last.isoformat(), grain=grain, record_count=len(records), has_mock=any(r.get("is_mock") for r in records))
