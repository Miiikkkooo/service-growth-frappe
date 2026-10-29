frappe.query_reports["User Growth"] = {
    filters: [
        {fieldname:"from_date", label:__("开始日期"), fieldtype:"Date", default:frappe.datetime.add_days(frappe.datetime.get_today(),-29), reqd:1},
        {fieldname:"to_date", label:__("结束日期"), fieldtype:"Date", default:frappe.datetime.get_today(), reqd:1},
        {fieldname:"city", label:__("城市"), fieldtype:"Data"},
        {fieldname:"grain", label:__("粒度"), fieldtype:"Select", options:[{label:__("按日"),value:"day"},{label:__("按月"),value:"month"}], default:"day", reqd:1}
    ]
};
