import unittest
from datetime import datetime, timedelta
from service_growth.analytics import aggregate
from service_growth.mock import make_records


def record(uid='A',start='2026-10-01 10:00:00',end=None,service='one',city='杭州'):
    return dict(user_id=uid,service_id=service,opened_at=start,closed_at=end,city=city,channel='线上推广',churn_reason='需求结束',is_mock=1)

class AnalyticsTests(unittest.TestCase):
    def calc(self, records, start='2026-10-01',end='2026-10-31',**kw):
        return aggregate(records,start,end,**kw)
    def test_empty(self):
        d=self.calc([]);self.assertEqual(d['totals']['closing'],0);self.assertIsNone(d['totals']['churn_rate'])
    def test_same_time_churn_reason_is_order_independent(self):
        a=record(end='2026-10-10');b=record(end='2026-10-10',service='two');b['churn_reason']='价格因素'
        self.assertEqual(self.calc([a,b])['reasons'],self.calc([b,a])['reasons'])
        self.assertEqual(self.calc([a,b])['reasons'],{'多服务同时关闭':1})
    def test_new(self):
        t=self.calc([record()])['totals'];self.assertEqual((t['new'],t['closing'],t['net']),(1,1,1))
    def test_partial_service_close_not_churn(self):
        t=self.calc([record(end='2026-10-10'),record(service='two')])['totals'];self.assertEqual(t['churn'],0);self.assertEqual(t['new'],1)
    def test_reactivation(self):
        t=self.calc([record(start='2026-09-01',end='2026-10-05'),record(start='2026-10-10')])['totals'];self.assertEqual((t['opening'],t['new'],t['reactivated'],t['churn'],t['closing']),(1,0,1,1,1));self.assertEqual(t['churn_rate'],0)
    def test_touching_intervals_are_continuous(self):
        t=self.calc([record(end='2026-10-05'),record(start='2026-10-05')])['totals'];self.assertEqual((t['new'],t['reactivated'],t['churn']),(1,0,0))
    def test_midnight_boundary(self):
        t=self.calc([record(start='2026-09-30',end='2026-10-01'),record(uid='B',start='2026-11-01')])['totals'];self.assertEqual((t['opening'],t['churn'],t['closing']),(1,1,0))
    def test_same_day_churn_and_return_counts(self):
        t=self.calc([record(end='2026-10-01 11:00:00'),record(start='2026-10-01 12:00:00')])['totals'];self.assertEqual((t['new'],t['churn'],t['reactivated'],t['closing']),(1,1,1,1))
    def test_city_filter(self):
        d=self.calc([record(),record(uid='B',city='宁波')],city='宁波');self.assertEqual(d['totals']['closing'],1);self.assertEqual(d['cities'],{'宁波':1})
    def test_month_matches_day(self):
        rows=make_records();day=self.calc(rows);month=self.calc(rows,grain='month');self.assertEqual(day['totals'],month['totals'])
    def test_invalid_filters(self):
        for start,end,grain in [('2026-10-02','2026-10-01','day'),('2024-01-01','2026-01-01','day'),('2026-10-01','2026-10-02','year')]:
            with self.assertRaises(ValueError):self.calc([],start,end,grain=grain)
    def test_deterministic_mock(self):
        self.assertEqual(make_records(),make_records())
    def test_daily_balance_and_distribution(self):
        d=self.calc(make_records(),'2026-05-01','2026-10-29')
        for r in d['rows']:self.assertEqual(r['opening']+r['new']+r['reactivated']-r['churn'],r['closing'])
        self.assertEqual(sum(d['cities'].values()),d['totals']['closing'])
        self.assertEqual(sum(d['reasons'].values()),d['totals']['churn'])
    def test_snapshots_match_independent_union(self):
        rows=make_records()
        for delta in range(0,150,7):
            start=datetime(2026,5,1)+timedelta(days=delta);end=start+timedelta(days=9)
            d=self.calc(rows,start.date().isoformat(),end.date().isoformat())
            boundary=end+timedelta(days=1)
            expected={r['user_id'] for r in rows if r['opened_at']<boundary and (r['closed_at'] is None or r['closed_at']>=boundary)}
            self.assertEqual(d['totals']['closing'],len(expected))

if __name__=='__main__':unittest.main()
