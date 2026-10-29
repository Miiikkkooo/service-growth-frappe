"""Independent review tests: order invariance and midnight cutoffs."""
import itertools
import unittest
from service_growth.analytics import aggregate


def row(service, start, end, reason):
    return dict(user_id='review-user', service_id=service, opened_at=start,
                closed_at=end, churn_reason=reason, city='杭州', channel='线上推广')


class ReviewEdgeTests(unittest.TestCase):
    def test_simultaneous_close_reasons_order_invariant(self):
        records = [row(str(i), '2026-10-01', '2026-10-10', r)
                   for i, r in enumerate(['价格因素', '价格因素', '服务体验', '需求结束'])]
        for permutation in itertools.permutations(records):
            with self.subTest(order=[r['service_id'] for r in permutation]):
                result = aggregate(permutation, '2026-10-01', '2026-10-31')
                self.assertEqual(result['reasons'], {'多服务同时关闭': 1})
                self.assertEqual(result['totals']['churn'], 1)

    def test_earlier_closures_do_not_pollute_final_reason(self):
        records = [row('1', '2026-10-01', '2026-10-08', '价格因素'),
                   row('2', '2026-10-01', '2026-10-09', '服务体验'),
                   row('3', '2026-10-01', '2026-10-10', '需求结束')]
        for permutation in itertools.permutations(records):
            self.assertEqual(aggregate(permutation, '2026-10-01', '2026-10-31')['reasons'], {'需求结束': 1})

    def test_last_microsecond_event_included(self):
        result = aggregate([row('1','2026-10-31 23:59:59.999999', None, None)], '2026-10-31', '2026-10-31')
        self.assertEqual(result['totals']['new'], 1)
        self.assertEqual(result['totals']['closing'], 1)

    def test_right_midnight_closure_belongs_to_next_period(self):
        records = [row('1','2026-10-01','2026-11-01', '需求结束')]
        october = aggregate(records,'2026-10-01','2026-10-31')
        november = aggregate(records,'2026-11-01','2026-11-01')
        self.assertEqual(october['totals']['closing'],1)
        self.assertEqual(october['totals']['churn'],0)
        self.assertEqual(november['totals']['opening'],1)
        self.assertEqual(november['totals']['churn'],1)
        self.assertEqual(november['totals']['closing'],0)
