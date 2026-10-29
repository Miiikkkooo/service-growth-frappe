from service_growth.api import get_growth

def execute(filters=None):
    filters = filters or {}
    result = get_growth(**{k: filters.get(k) for k in ("from_date", "to_date", "city")}, grain=filters.get("grain") or "day")
    columns = [{"fieldname": "period", "label": "统计周期", "fieldtype": "Data", "width": 130}]
    for field, label in [("opening","期初在服人数"),("new","首次开通次数"),("reactivated","回流次数"),("churn","流失次数"),("net","净增长"),("closing","期末在服人数")]:
        columns.append({"fieldname":field,"label":label,"fieldtype":"Int","width":135})
    chart = {"data":{"labels":[r["period"] for r in result["rows"]],"datasets":[{"name":label,"values":[r[field] for r in result["rows"]]} for field,label in [("new","首次开通"),("reactivated","回流"),("churn","流失")]]},"type":"line","height":280}
    summary = [{"label":label,"value":result["totals"][field],"datatype":"Int"} for field,label in [("new","首次开通次数"),("reactivated","回流次数"),("churn","流失次数"),("net","净增长"),("closing","期末在服人数")]]
    summary.append({"label":"期初人群流失率","value":str(result["totals"]["churn_rate"])+"%" if result["totals"]["churn_rate"] is not None else "—","datatype":"Data"})
    message = "合成演示数据；" if result["has_mock"] else ""
    message += "事件按次数统计；期初 + 首次开通 + 回流 − 流失 = 期末。城市/渠道为用户固定归属。"
    return columns, result["rows"], message, chart, summary
