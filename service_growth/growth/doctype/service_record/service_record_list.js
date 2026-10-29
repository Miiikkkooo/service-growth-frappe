frappe.listview_settings["Service Record"] = {
    add_fields: ["closed_at", "is_mock"],
    get_indicator(doc) {
        return doc.closed_at ? [__("已关闭"), "gray", "closed_at,is,set"] : [__("在服"), "green", "closed_at,is,not set"];
    }
};
