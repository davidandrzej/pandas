# pylint: disable=W0612,E1101


from datetime import datetime
import os
import operator
import unittest

import numpy as np

from pandas.core.api import DataFrame, Index, notnull
from pandas.core.datetools import bday
from pandas.core.frame import group_agg
from pandas.core.panel import WidePanel, LongPanel, pivot
import pandas.core.panel as panelmod

from pandas.util.testing import (assert_panel_equal,
                                 assert_frame_equal,
                                 assert_series_equal,
                                 assert_almost_equal)
import pandas.core.panel as panelm
import pandas.util.testing as common

class PanelTests(object):
    panel = None

    def test_pickle(self):
        import cPickle
        pickled = cPickle.dumps(self.panel)
        unpickled = cPickle.loads(pickled)
        assert_frame_equal(unpickled['ItemA'], self.panel['ItemA'])

    def test_cumsum(self):
        cumsum = self.panel.cumsum()
        assert_frame_equal(cumsum['ItemA'], self.panel['ItemA'].cumsum())

class SafeForLongAndSparse(object):

    def test_repr(self):
        foo = repr(self.panel)

    def test_iter(self):
        common.equalContents(list(self.panel), self.panel.items)

    def _check_statistic(self, frame, name, alternative):
        f = getattr(frame, name)

        for i, ax in enumerate(['items', 'major', 'minor']):
            result = f(axis=i)
            assert_frame_equal(result, frame.apply(alternative, axis=ax))

    def test_count(self):
        f = lambda s: notnull(s).sum()

        self._check_statistic(self.panel, 'count', f)

    def test_sum(self):
        def f(x):
            x = np.asarray(x)
            nona = x[notnull(x)]

            if len(nona) == 0:
                return np.NaN
            else:
                return nona.sum()

        self._check_statistic(self.panel, 'sum', f)

    def test_prod(self):
        def f(x):
            x = np.asarray(x)
            nona = x[notnull(x)]

            if len(nona) == 0:
                return np.NaN
            else:
                return np.prod(nona)

        self._check_statistic(self.panel, 'prod', f)

    def test_mean(self):
        def f(x):
            x = np.asarray(x)
            return x[notnull(x)].mean()

        self._check_statistic(self.panel, 'mean', f)

    def test_median(self):
        def f(x):
            x = np.asarray(x)
            return np.median(x[notnull(x)])

        self._check_statistic(self.panel, 'median', f)

    def test_min(self):
        def f(x):
            x = np.asarray(x)
            nona = x[notnull(x)]

            if len(nona) == 0:
                return np.NaN
            else:
                return nona.min()

        self._check_statistic(self.panel, 'min', f)

    def test_max(self):
        def f(x):
            x = np.asarray(x)
            nona = x[notnull(x)]

            if len(nona) == 0:
                return np.NaN
            else:
                return nona.max()

        self._check_statistic(self.panel, 'max', f)

    def test_var(self):
        def f(x):
            x = np.asarray(x)
            nona = x[notnull(x)]

            if len(nona) < 2:
                return np.NaN
            else:
                return nona.var(ddof=1)

        self._check_statistic(self.panel, 'var', f)

    def test_std(self):
        def f(x):
            x = np.asarray(x)
            nona = x[notnull(x)]

            if len(nona) < 2:
                return np.NaN
            else:
                return nona.std(ddof=1)

        self._check_statistic(self.panel, 'std', f)

    def test_skew(self):
        return
        try:
            from scipy.stats import skew
        except ImportError:
            return

        def f(x):
            x = np.asarray(x)
            return skew(x[notnull(x)], bias=False)

        self._check_statistic(self.panel, 'skew', f)

class SafeForSparse(object):

    @staticmethod
    def assert_panel_equal(x, y):
        assert_panel_equal(x, y)

    def test_get_axis(self):
        assert(self.panel._get_axis(0) is self.panel.items)
        assert(self.panel._get_axis(1) is self.panel.major_axis)
        assert(self.panel._get_axis(2) is self.panel.minor_axis)

    def test_set_axis(self):
        new_items = Index(np.arange(len(self.panel.items)))
        new_major = Index(np.arange(len(self.panel.major_axis)))
        new_minor = Index(np.arange(len(self.panel.minor_axis)))

        self.panel.items = new_items
        self.assert_(self.panel.items is new_items)

        self.panel.major_axis = new_major
        self.assert_(self.panel.major_axis is new_major)

        self.panel.minor_axis = new_minor
        self.assert_(self.panel.minor_axis is new_minor)

    def test_get_axis_number(self):
        self.assertEqual(self.panel._get_axis_number('items'), 0)
        self.assertEqual(self.panel._get_axis_number('major'), 1)
        self.assertEqual(self.panel._get_axis_number('minor'), 2)

    def test_get_axis_name(self):
        self.assertEqual(self.panel._get_axis_name(0), 'items')
        self.assertEqual(self.panel._get_axis_name(1), 'major_axis')
        self.assertEqual(self.panel._get_axis_name(2), 'minor_axis')

    def test_get_plane_axes(self):
        # what to do here?

        index, columns = self.panel._get_plane_axes('items')
        index, columns = self.panel._get_plane_axes('major_axis')
        index, columns = self.panel._get_plane_axes('minor_axis')
        index, columns = self.panel._get_plane_axes(0)

    def test_truncate(self):
        dates = self.panel.major_axis
        start, end = dates[1], dates[5]

        trunced = self.panel.truncate(start, end, axis='major')
        expected = self.panel['ItemA'].truncate(start, end)

        assert_frame_equal(trunced['ItemA'], expected)

        trunced = self.panel.truncate(before=start, axis='major')
        expected = self.panel['ItemA'].truncate(before=start)

        assert_frame_equal(trunced['ItemA'], expected)

        trunced = self.panel.truncate(after=end, axis='major')
        expected = self.panel['ItemA'].truncate(after=end)

        assert_frame_equal(trunced['ItemA'], expected)

        # XXX test other axes

    def test_arith(self):
        self._test_op(self.panel, operator.add)
        self._test_op(self.panel, operator.sub)
        self._test_op(self.panel, operator.mul)
        self._test_op(self.panel, operator.div)
        self._test_op(self.panel, operator.pow)

        self._test_op(self.panel, lambda x, y: y + x)
        self._test_op(self.panel, lambda x, y: y - x)
        self._test_op(self.panel, lambda x, y: y * x)
        self._test_op(self.panel, lambda x, y: y / x)
        self._test_op(self.panel, lambda x, y: y ** x)

        self.assertRaises(Exception, self.panel.__add__, self.panel['ItemA'])

    @staticmethod
    def _test_op(panel, op):
        result = op(panel, 1)
        assert_frame_equal(result['ItemA'], op(panel['ItemA'], 1))

    def test_keys(self):
        common.equalContents(self.panel.keys(), self.panel.items)

    def test_iteritems(self):
        # just test that it works
        for k, v in self.panel.iteritems():
            pass

        self.assertEqual(len(list(self.panel.iteritems())),
                         len(self.panel.items))

    def test_combineFrame(self):
        def check_op(op, name):
            # items
            df = self.panel['ItemA']

            func = getattr(self.panel, name)

            result = func(df, axis='items')

            assert_frame_equal(result['ItemB'], op(self.panel['ItemB'], df))

            # major
            xs = self.panel.major_xs(self.panel.major_axis[0])
            result = func(xs, axis='major')

            idx = self.panel.major_axis[1]

            assert_frame_equal(result.major_xs(idx),
                               op(self.panel.major_xs(idx), xs))

            # minor
            xs = self.panel.minor_xs(self.panel.minor_axis[0])
            result = func(xs, axis='minor')

            idx = self.panel.minor_axis[1]

            assert_frame_equal(result.minor_xs(idx),
                               op(self.panel.minor_xs(idx), xs))

        check_op(operator.add, 'add')
        check_op(operator.sub, 'subtract')
        check_op(operator.mul, 'multiply')
        check_op(operator.div, 'divide')

    def test_combinePanel(self):
        result = self.panel.add(self.panel)
        self.assert_panel_equal(result, self.panel * 2)

    def test_neg(self):
        self.assert_panel_equal(-self.panel, self.panel * -1)

    def test_select(self):
        p = self.panel

        # select items
        result = p.select(lambda x: x in ('ItemA', 'ItemC'), axis='items')
        expected = p.reindex(items=['ItemA', 'ItemC'])
        self.assert_panel_equal(result, expected)

        # select major_axis
        result = p.select(lambda x: x >= datetime(2000, 1, 15), axis='major')
        new_major = p.major_axis[p.major_axis >= datetime(2000, 1, 15)]
        expected = p.reindex(major=new_major)
        self.assert_panel_equal(result, expected)

        # select minor_axis
        result = p.select(lambda x: x in ('D', 'A'), axis=2)
        expected = p.reindex(minor=['A', 'D'])
        self.assert_panel_equal(result, expected)

        # corner case, empty thing
        result = p.select(lambda x: x in ('foo',), axis='items')
        self.assert_panel_equal(result, p.reindex(items=[]))

class TestWidePanel(unittest.TestCase, PanelTests,
                    SafeForLongAndSparse,
                    SafeForSparse):

    @staticmethod
    def assert_panel_equal(x, y):
        assert_panel_equal(x, y)

    def setUp(self):
        self.panel = common.makeWidePanel()
        common.add_nans(self.panel)

    def test_constructor(self):
        # with BlockManager
        wp = WidePanel(self.panel._data)
        self.assert_(wp._data is self.panel._data)

        wp = WidePanel(self.panel._data, copy=True)
        self.assert_(wp._data is not self.panel._data)
        assert_panel_equal(wp, self.panel)

        # strings handled prop
        wp = WidePanel([[['foo', 'foo', 'foo',],
                         ['foo', 'foo', 'foo']]])
        self.assert_(wp.values.dtype == np.object_)

        vals = self.panel.values

        # no copy
        wp = WidePanel(vals)
        self.assert_(wp.values is vals)

        # copy
        wp = WidePanel(vals, copy=True)
        self.assert_(wp.values is not vals)

    def test_constructor_cast(self):
        casted = WidePanel(self.panel._data, dtype=int)
        casted2 = WidePanel(self.panel.values, dtype=int)

        exp_values = self.panel.values.astype(int)
        assert_almost_equal(casted.values, exp_values)
        assert_almost_equal(casted2.values, exp_values)

        # can't cast
        data = [[['foo', 'bar', 'baz']]]
        self.assertRaises(ValueError, WidePanel, data, dtype=float)

    def test_consolidate(self):
        self.assert_(self.panel._data.is_consolidated())

        self.panel['foo'] = 1.
        self.assert_(not self.panel._data.is_consolidated())

        panel = self.panel.consolidate()
        self.assert_(panel._data.is_consolidated())

    def test_ctor_dict(self):
        itema = self.panel['ItemA']
        itemb = self.panel['ItemB']

        d = {'A' : itema, 'B' : itemb[5:]}
        d2 = {'A' : itema._series, 'B' : itemb[5:]._series}
        d3 = {'A' : DataFrame(itema._series),
              'B' : DataFrame(itemb[5:]._series)}

        wp = WidePanel.from_dict(d)
        wp2 = WidePanel.from_dict(d2) # nested Dict
        wp3 = WidePanel.from_dict(d3)
        self.assert_(wp.major_axis.equals(self.panel.major_axis))
        assert_panel_equal(wp, wp2)

        # intersect
        wp = WidePanel.from_dict(d, intersect=True)
        self.assert_(wp.major_axis.equals(itemb.index[5:]))

        # use constructor
        assert_panel_equal(WidePanel(d), WidePanel.from_dict(d))
        assert_panel_equal(WidePanel(d2), WidePanel.from_dict(d2))
        assert_panel_equal(WidePanel(d3), WidePanel.from_dict(d3))

        # cast
        result = WidePanel(d, dtype=int)
        expected = WidePanel(dict((k, v.astype(int)) for k, v in d.iteritems()))

    def test_from_dict_mixed(self):
        pass

    def test_values(self):
        self.assertRaises(Exception, WidePanel, np.random.randn(5, 5, 5),
                          range(5), range(5), range(4))

    def test_getitem(self):
        self.assertRaises(Exception, self.panel.__getitem__, 'ItemQ')

    def test_delitem_and_pop(self):
        expected = self.panel['ItemA']
        result = self.panel.pop('ItemA')
        assert_frame_equal(expected, result)
        self.assert_('ItemA' not in self.panel.items)

        del self.panel['ItemB']
        self.assert_('ItemB' not in self.panel.items)
        self.assertRaises(Exception, self.panel.__delitem__, 'ItemB')

        values = np.empty((3, 3, 3))
        values[0] = 0
        values[1] = 1
        values[2] = 2

        panel = WidePanel(values, range(3), range(3), range(3))

        # did we delete the right row?

        panelc = panel.copy()
        del panelc[0]
        assert_frame_equal(panelc[1], panel[1])
        assert_frame_equal(panelc[2], panel[2])

        panelc = panel.copy()
        del panelc[1]
        assert_frame_equal(panelc[0], panel[0])
        assert_frame_equal(panelc[2], panel[2])

        panelc = panel.copy()
        del panelc[2]
        assert_frame_equal(panelc[1], panel[1])
        assert_frame_equal(panelc[0], panel[0])

    def test_setitem(self):

        # LongPanel with one item
        lp = self.panel.filter(['ItemA']).to_long()
        self.panel['ItemE'] = lp

        lp = self.panel.filter(['ItemA', 'ItemB']).to_long()
        self.assertRaises(Exception, self.panel.__setitem__,
                          'ItemE', lp)

        # DataFrame
        df = self.panel['ItemA'][2:].filter(items=['A', 'B'])
        self.panel['ItemF'] = df
        self.panel['ItemE'] = df

        df2 = self.panel['ItemF']

        assert_frame_equal(df, df2.reindex(index=df.index,
                                           columns=df.columns))

        # scalar
        self.panel['ItemG'] = 1
        self.panel['ItemE'] = 1

        # object dtype
        self.panel['ItemQ'] = 'foo'
        self.assert_(self.panel['ItemQ'].values.dtype == np.object_)

        # boolean dtype
        self.panel['ItemP'] = self.panel['ItemA'] > 0
        self.assert_(self.panel['ItemP'].values.dtype == np.bool_)

    def test_conform(self):
        df = self.panel['ItemA'][:-5].filter(items=['A', 'B'])
        conformed = self.panel.conform(df)

        assert(conformed.index.equals(self.panel.major_axis))
        assert(conformed.columns.equals(self.panel.minor_axis))

    def test_reindex(self):
        ref = self.panel['ItemB']

        # items
        result = self.panel.reindex(items=['ItemA', 'ItemB'])
        assert_frame_equal(result['ItemB'], ref)

        # major
        new_major = list(self.panel.major_axis[:10])
        result = self.panel.reindex(major=new_major)
        assert_frame_equal(result['ItemB'], ref.reindex(index=new_major))

        # raise exception put both major and major_axis
        self.assertRaises(Exception, self.panel.reindex,
                          major_axis=new_major, major=new_major)

        # minor
        new_minor = list(self.panel.minor_axis[:2])
        result = self.panel.reindex(minor=new_minor)
        assert_frame_equal(result['ItemB'], ref.reindex(columns=new_minor))

        result = self.panel.reindex(items=self.panel.items,
                                    major=self.panel.major_axis,
                                    minor=self.panel.minor_axis)

        assert(result.items is self.panel.items)
        assert(result.major_axis is self.panel.major_axis)
        assert(result.minor_axis is self.panel.minor_axis)

        self.assertRaises(Exception, self.panel.reindex)

        # with filling
        smaller_major = self.panel.major_axis[::5]
        smaller = self.panel.reindex(major=smaller_major)

        larger = smaller.reindex(major=self.panel.major_axis,
                                 method='pad')

        assert_frame_equal(larger.major_xs(self.panel.major_axis[1]),
                           smaller.major_xs(smaller_major[0]))

        # don't necessarily copy
        result = self.panel.reindex(major=self.panel.major_axis, copy=False)
        self.assert_(result is self.panel)

    def test_reindex_like(self):
        # reindex_like
        smaller = self.panel.reindex(items=self.panel.items[:-1],
                                     major=self.panel.major_axis[:-1],
                                     minor=self.panel.minor_axis[:-1])
        smaller_like = self.panel.reindex_like(smaller)
        assert_panel_equal(smaller, smaller_like)

    def test_sort_index(self):
        import random

        ritems = list(self.panel.items)
        rmajor = list(self.panel.major_axis)
        rminor = list(self.panel.minor_axis)
        random.shuffle(ritems)
        random.shuffle(rmajor)
        random.shuffle(rminor)

        random_order = self.panel.reindex(items=ritems)
        sorted_panel = random_order.sort_index(axis=0)
        assert_panel_equal(sorted_panel, self.panel)

        # descending
        random_order = self.panel.reindex(items=ritems)
        sorted_panel = random_order.sort_index(axis=0, ascending=False)
        assert_panel_equal(sorted_panel,
                           self.panel.reindex(items=self.panel.items[::-1]))

        random_order = self.panel.reindex(major=rmajor)
        sorted_panel = random_order.sort_index(axis=1)
        assert_panel_equal(sorted_panel, self.panel)

        random_order = self.panel.reindex(minor=rminor)
        sorted_panel = random_order.sort_index(axis=2)
        assert_panel_equal(sorted_panel, self.panel)

    def test_fillna(self):
        filled = self.panel.fillna(0)
        self.assert_(np.isfinite(filled.values).all())

        filled = self.panel.fillna(method='backfill')
        assert_frame_equal(filled['ItemA'],
                           self.panel['ItemA'].fillna(method='backfill'))

        empty = self.panel.reindex(items=[])
        filled = empty.fillna(0)
        assert_panel_equal(filled, empty)

    def test_combinePanel_with_long(self):
        lng = self.panel.to_long(filter_observations=False)
        result = self.panel.add(lng)
        self.assert_panel_equal(result, self.panel * 2)

    def test_major_xs(self):
        ref = self.panel['ItemA']

        idx = self.panel.major_axis[5]
        xs = self.panel.major_xs(idx)

        assert_series_equal(xs['ItemA'], ref.xs(idx))

        # not contained
        idx = self.panel.major_axis[0] - bday
        self.assertRaises(Exception, self.panel.major_xs, idx)

    def test_major_xs_mixed(self):
        self.panel['ItemD'] = 'foo'
        xs = self.panel.major_xs(self.panel.major_axis[0])
        self.assert_(xs['ItemA'].dtype == np.float64)
        self.assert_(xs['ItemD'].dtype == np.object_)

    def test_minor_xs(self):
        ref = self.panel['ItemA']

        idx = self.panel.minor_axis[1]
        xs = self.panel.minor_xs(idx)

        assert_series_equal(xs['ItemA'], ref[idx])

        # not contained
        self.assertRaises(Exception, self.panel.minor_xs, 'E')

    def test_minor_xs_mixed(self):
        self.panel['ItemD'] = 'foo'

        xs = self.panel.minor_xs('D')
        self.assert_(xs['ItemA'].dtype == np.float64)
        self.assert_(xs['ItemD'].dtype == np.object_)

    def test_swapaxes(self):
        result = self.panel.swapaxes('items', 'minor')
        self.assert_(result.items is self.panel.minor_axis)

        result = self.panel.swapaxes('items', 'major')
        self.assert_(result.items is self.panel.major_axis)

        result = self.panel.swapaxes('major', 'minor')
        self.assert_(result.major_axis is self.panel.minor_axis)

        # this should also work
        result = self.panel.swapaxes(0, 1)
        self.assert_(result.items is self.panel.major_axis)

        # this should also work
        self.assertRaises(Exception, self.panel.swapaxes, 'items', 'items')

    def test_to_long(self):
        # filtered
        filtered = self.panel.to_long()

        # unfiltered
        unfiltered = self.panel.to_long(filter_observations=False)

        assert_panel_equal(unfiltered.to_wide(), self.panel)

    def test_to_long_mixed(self):
        panel = self.panel.fillna(0)
        panel['str'] = 'foo'
        panel['bool'] = panel['ItemA'] > 0

        lp = panel.to_long()
        wp = lp.to_wide()
        self.assertEqual(wp['bool'].values.dtype, np.bool_)
        assert_frame_equal(wp['bool'], panel['bool'])

    def test_filter(self):
        pass

    def test_apply(self):
        pass

    def test_compound(self):
        compounded = self.panel.compound()

        assert_series_equal(compounded['ItemA'],
                            (1 + self.panel['ItemA']).product(0) - 1)

    def test_shift(self):
        # major
        idx = self.panel.major_axis[0]
        idx_lag = self.panel.major_axis[1]

        shifted = self.panel.shift(1)

        assert_frame_equal(self.panel.major_xs(idx),
                           shifted.major_xs(idx_lag))

        # minor
        idx = self.panel.minor_axis[0]
        idx_lag = self.panel.minor_axis[1]

        shifted = self.panel.shift(1, axis='minor')

        assert_frame_equal(self.panel.minor_xs(idx),
                           shifted.minor_xs(idx_lag))

        self.assertRaises(Exception, self.panel.shift, 1, axis='items')

class TestLongPanel(unittest.TestCase):

    def setUp(self):
        panel = common.makeWidePanel()
        common.add_nans(panel)

        self.panel = panel.to_long()
        self.unfiltered_panel = panel.to_long(filter_observations=False)

    def test_pickle(self):
        import cPickle

        pickled = cPickle.dumps(self.panel)
        unpickled = cPickle.loads(pickled)

        assert_almost_equal(unpickled['ItemA'].values,
                            self.panel['ItemA'].values)

    def test_len(self):
        len(self.unfiltered_panel)

    def test_constructor(self):
        pass

    def test_fromRecords_toRecords(self):
        # structured array
        K = 10

        recs = np.zeros(K, dtype='O,O,f8,f8')
        recs['f0'] = range(K / 2) * 2
        recs['f1'] = np.arange(K) / (K / 2)
        recs['f2'] = np.arange(K) * 2
        recs['f3'] = np.arange(K)

        lp = LongPanel.fromRecords(recs, 'f0', 'f1')
        self.assertEqual(len(lp.items), 2)

        lp = LongPanel.fromRecords(recs, 'f0', 'f1', exclude=['f2'])
        self.assertEqual(len(lp.items), 1)

        torecs = lp.toRecords()
        self.assertEqual(len(torecs.dtype.names), len(lp.items) + 2)

        # DataFrame
        df = DataFrame.from_records(recs)
        lp = LongPanel.fromRecords(df, 'f0', 'f1', exclude=['f2'])
        self.assertEqual(len(lp.items), 1)

        # dict of arrays
        series = DataFrame.from_records(recs)._series
        lp = LongPanel.fromRecords(series, 'f0', 'f1', exclude=['f2'])
        self.assertEqual(len(lp.items), 1)
        self.assert_('f2' in series)

        self.assertRaises(Exception, LongPanel.fromRecords, np.zeros((3, 3)),
                          0, 1)

    def test_factors(self):
        # structured array
        K = 10

        recs = np.zeros(K, dtype='O,O,f8,f8,O,O')
        recs['f0'] = ['one'] * 5 + ['two'] * 5
        recs['f1'] = ['A', 'B', 'C', 'D', 'E'] * 2
        recs['f2'] = np.arange(K) * 2
        recs['f3'] = np.arange(K)
        recs['f4'] = ['A', 'B', 'C', 'D', 'E'] * 2
        recs['f5'] = ['foo', 'bar'] * 5

        lp = LongPanel.fromRecords(recs, 'f0', 'f1')

    def test_columns(self):
        self.assert_(np.array_equal(self.panel.items, self.panel.columns))

    def test_copy(self):
        thecopy = self.panel.copy()
        self.assert_(np.array_equal(thecopy.values, self.panel.values))
        self.assert_(thecopy.values is not self.panel.values)

    def test_getitem(self):
        col = self.panel['ItemA']

    def test_setitem(self):
        self.panel['ItemE'] = self.panel['ItemA']
        self.panel['ItemF'] = 1.

        wp = self.panel.to_wide()
        assert_frame_equal(wp['ItemA'], wp['ItemE'])

        itemf = wp['ItemF'].values.ravel()
        self.assert_((itemf[np.isfinite(itemf)] == 1).all())

        # check exceptions raised
        lp = self.panel.filter(['ItemA', 'ItemB'])
        lp2 = self.panel.filter(['ItemC', 'ItemE'])
        self.assertRaises(Exception, lp.__setitem__, 'foo', lp2)

    def test_ops_differently_indexed(self):
        # trying to set non-identically indexed panel
        wp = self.panel.to_wide()
        wp2 = wp.reindex(major=wp.major_axis[:-1])
        lp2 = wp2.to_long()

        self.assertRaises(Exception, self.panel.__setitem__, 'foo',
                          lp2.filter(['ItemA']))

        self.assertRaises(Exception, self.panel.add, lp2)

    def test_combineFrame(self):
        wp = self.panel.to_wide()
        result = self.panel.add(wp['ItemA'])
        assert_frame_equal(result.to_wide()['ItemA'], wp['ItemA'] * 2)

    def test_combinePanel(self):
        wp = self.panel.to_wide()
        result = self.panel.add(self.panel)
        wide_result = result.to_wide()
        assert_frame_equal(wp['ItemA'] * 2, wide_result['ItemA'])

        # one item
        result = self.panel.add(self.panel.filter(['ItemA']))

    def test_operators(self):
        wp = self.panel.to_wide()
        result = (self.panel + 1).to_wide()
        assert_frame_equal(wp['ItemA'] + 1, result['ItemA'])

    def test_sort(self):
        def is_sorted(arr):
            return (arr[1:] > arr[:-1]).any()

        sorted_minor = self.panel.sortlevel(level=1)
        self.assert_(is_sorted(sorted_minor.minor_labels))

        sorted_major = sorted_minor.sortlevel(level=0)
        self.assert_(is_sorted(sorted_major.major_labels))

    def test_to_wide(self):
        pass

    def test_toCSV(self):
        self.panel.toCSV('__tmp__')
        os.remove('__tmp__')

    def test_toString(self):
        from cStringIO import StringIO

        buf = StringIO()
        self.panel.toString(buf)

    def test_swapaxes(self):
        swapped = self.panel.swapaxes()

        self.assert_(swapped.major_axis is self.panel.minor_axis)

        # what else to test here?

    def test_truncate(self):
        dates = self.panel.major_axis
        start, end = dates[1], dates[5]

        trunced = self.panel.truncate(start, end).to_wide()
        expected = self.panel.to_wide()['ItemA'].truncate(start, end)

        assert_frame_equal(trunced['ItemA'], expected)

        trunced = self.panel.truncate(before=start).to_wide()
        expected = self.panel.to_wide()['ItemA'].truncate(before=start)

        assert_frame_equal(trunced['ItemA'], expected)

        trunced = self.panel.truncate(after=end).to_wide()
        expected = self.panel.to_wide()['ItemA'].truncate(after=end)

        assert_frame_equal(trunced['ItemA'], expected)

        # truncate on dates that aren't in there
        wp = self.panel.to_wide()
        new_index = wp.major_axis[::5]

        wp2 = wp.reindex(major=new_index)

        lp2 = wp2.to_long()
        lp_trunc = lp2.truncate(wp.major_axis[2], wp.major_axis[-2])

        wp_trunc = wp2.truncate(wp.major_axis[2], wp.major_axis[-2])

        assert_panel_equal(wp_trunc, lp_trunc.to_wide())

        # throw proper exception
        self.assertRaises(Exception, lp2.truncate, wp.major_axis[-2],
                          wp.major_axis[2])


    def test_filter(self):
        pass

    def test_axis_dummies(self):
        minor_dummies = self.panel.get_axis_dummies('minor')
        self.assertEqual(len(minor_dummies.items),
                         len(self.panel.minor_axis))

        major_dummies = self.panel.get_axis_dummies('major')
        self.assertEqual(len(major_dummies.items),
                         len(self.panel.major_axis))

        mapping = {'A' : 'one',
                   'B' : 'one',
                   'C' : 'two',
                   'D' : 'two'}

        transformed = self.panel.get_axis_dummies('minor',
                                                  transform=mapping.get)
        self.assertEqual(len(transformed.items), 2)
        self.assert_(np.array_equal(transformed.items, ['one', 'two']))

        # TODO: test correctness

    def test_get_dummies(self):
        self.panel['Label'] = self.panel.minor_labels

        minor_dummies = self.panel.get_axis_dummies('minor')
        dummies = self.panel.get_dummies('Label')

        self.assert_(np.array_equal(dummies.values, minor_dummies.values))

    def test_apply(self):
        # ufunc
        applied = self.panel.apply(np.sqrt)
        self.assert_(assert_almost_equal(applied.values,
                                         np.sqrt(self.panel.values)))

    def test_mean(self):
        means = self.panel.mean('major')

        # test versus WidePanel version
        wide_means = self.panel.to_wide().mean('major')
        assert_frame_equal(means, wide_means)

        means_broadcast = self.panel.mean('major', broadcast=True)
        self.assert_(isinstance(means_broadcast, LongPanel))

        # how to check correctness?

    def test_sum(self):
        sums = self.panel.sum('major')

        # test versus WidePanel version
        wide_sums = self.panel.to_wide().sum('major')
        assert_frame_equal(sums, wide_sums)

    def test_count(self):
        index = self.panel.index

        major_count = self.panel.count(level=0)['ItemA']
        labels = index.labels[0]
        for i, idx in enumerate(index.levels[0]):
            self.assertEqual(major_count[i], (labels == i).sum())

        minor_count = self.panel.count(level=1)['ItemA']
        labels = index.labels[1]
        for i, idx in enumerate(index.levels[1]):
            self.assertEqual(minor_count[i], (labels == i).sum())

    def test_join(self):
        lp1 = self.panel.filter(['ItemA', 'ItemB'])
        lp2 = self.panel.filter(['ItemC'])

        joined = lp1.join(lp2)

        self.assertEqual(len(joined.items), 3)

        self.assertRaises(Exception, lp1.join,
                          self.panel.filter(['ItemB', 'ItemC']))

    def test_merge(self):
        pass

    def test_addPrefix(self):
        lp = self.panel.addPrefix('foo#')
        self.assertEqual(lp.items[0], 'foo#ItemA')

        lp = self.panel.addPrefix()
        assert_panel_equal(lp.to_wide(), self.panel.to_wide())

    def test_pivot(self):
        df = pivot(np.array([1, 2, 3, 4, 5]),
                   np.array(['a', 'b', 'c', 'd', 'e']),
                   np.array([1, 2, 3, 5, 4.]))
        self.assertEqual(df['a'][1], 1)
        self.assertEqual(df['b'][2], 2)
        self.assertEqual(df['c'][3], 3)
        self.assertEqual(df['d'][4], 5)
        self.assertEqual(df['e'][5], 4)

        # weird overlap, TODO: test?
        a, b, c = (np.array([1, 2, 3, 4, 4]),
                   np.array(['a', 'a', 'a', 'a', 'a']),
                   np.array([1, 2, 3, 5, 4]))
        df = pivot(a, b, c)
        expected = panelmod._slow_pivot(a, b, c)
        assert_frame_equal(df, expected)

        # corner case, empty
        df = pivot(np.array([]), np.array([]), np.array([]))

def test_group_agg():
    values = np.ones((10, 2)) * np.arange(10).reshape((10, 1))
    bounds = np.arange(5) * 2
    f = lambda x: x.mean(axis=0)

    agged = group_agg(values, bounds, f)

    assert(agged[1][0] == 2.5)
    assert(agged[2][0] == 4.5)

def test_monotonic():
    pos = np.array([1, 2, 3, 5])

    assert panelm._monotonic(pos)

    neg = np.array([1, 2, 3, 4, 3])

    assert not panelm._monotonic(neg)

    neg2 = np.array([5, 1, 2, 3, 4, 5])

    assert not panelm._monotonic(neg2)

if __name__ == '__main__':
    import nose
    nose.runmodule(argv=[__file__,'-vvs','-x','--pdb', '--pdb-failure'],
                   exit=False)
