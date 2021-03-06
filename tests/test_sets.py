"""
This file contains a testing function + resources for testing whether
the correct sets are returned with set.py.
"""

__author__ = 'Lisa Rottjers'
__maintainer__ = 'Lisa Rottjers'
__email__ = 'lisa.rottjers@kuleuven.be'
__status__ = 'Development'
__license__ = 'Apache 2.0'

import unittest
import networkx as nx
from anuran.nulls import generate_null
from anuran.sets import generate_sizes, generate_sample_sizes, generate_size_differences
from anuran.utils import _difference, _intersection, _generate_rows
from scipy.special import binom
import pandas as pd

# generate three alternative networks with first 4 edges conserved but rest random
nodes = ["OTU_1", "OTU_2", "OTU_3", "OTU_4", "OTU_5"]
one = [("OTU_1", "OTU_2"), ("OTU_1", "OTU_3"),
       ("OTU_2", "OTU_5"), ("OTU_3", "OTU_4"),
       ("OTU_2", "OTU_3"), ("OTU_2", "OTU_4")]
two = [("OTU_1", "OTU_2"), ("OTU_1", "OTU_3"),
       ("OTU_2", "OTU_5"), ("OTU_3", "OTU_4"),
       ("OTU_3", "OTU_5"), ("OTU_4", "OTU_5")]
three = [("OTU_1", "OTU_2"), ("OTU_1", "OTU_3"),
         ("OTU_2", "OTU_5"), ("OTU_3", "OTU_4"),
         ("OTU_1", "OTU_4"), ("OTU_4", "OTU_5")]
weights = dict()
weights[("OTU_1", "OTU_2")] = float(1.0)
weights[("OTU_1", "OTU_3")] = float(1.0)
weights[("OTU_2", "OTU_5")] = float(1.0)
weights[("OTU_3", "OTU_4")] = float(-1.0)
weights[("OTU_2", "OTU_3")] = float(-1.0)
weights[("OTU_2", "OTU_4")] = float(-1.0)
weights[("OTU_3", "OTU_5")] = float(-1.0)
weights[("OTU_4", "OTU_5")] = float(-1.0)
weights[("OTU_1", "OTU_4")] = float(-1.0)

a = nx.Graph()
a.add_nodes_from(nodes)
a.add_edges_from(one)
nx.set_edge_attributes(a, values=weights, name='weight')
a = a.to_undirected()

b = nx.Graph()
b.add_nodes_from(nodes)
b.add_edges_from(two)
nx.set_edge_attributes(b, values=weights, name='weight')
b = b.to_undirected()

weights[("OTU_1", "OTU_2")] = float(-1.0)
c = nx.Graph()
c.add_nodes_from(nodes)
c.add_edges_from(three)
nx.set_edge_attributes(c, values=weights, name='weight')
c = c.to_undirected()

networks = {'a': [('a', a)], 'b': [('b', b)], 'c': [('c', c)]}


class TestMain(unittest.TestCase):
    """"
    Tests whether the main clustering function properly assigns cluster IDs.
    """

    def test_generate_sizes(self):
        """Checks whether the set sizes are correctly returned. """
        perm = 10
        nperm = 10
        random, degree = generate_null(networks, core=2, n=perm, npos=10)
        results = generate_sizes(networks, random_models=random, core=2,
                                 degree_models=degree, prev=None, fractions=False,
                                 perm=nperm, sizes=[1], sign=True)
        # 126: 2 set operations * 21 networks * 3 groups
        self.assertEqual(len(results), 126)

    def test_intersection_1_network(self):
        """Checks whether the intersection set size is correctly returned. """
        results = _intersection(networks['a'], size=1, sign=False)
        self.assertEqual(results, 0)

    def test_intersection(self):
        """Checks whether the intersection set size is correctly returned. """
        results = _intersection([networks['a'][0], networks['b'][0], networks['c'][0]], size=1, sign=False)
        self.assertEqual(results, 4)

    def test_intersection_size(self):
        """Checks whether the intersection set size is correctly returned. """
        results = _intersection([networks['a'][0], networks['b'][0], networks['c'][0]], size=0.6, sign=True)
        self.assertEqual(results, 5)

    def test_intersection_sign(self):
        """Checks whether the intersection set size is correctly returned. """
        results = _intersection([networks['a'][0], networks['b'][0], networks['c'][0]], size=1, sign=True)
        self.assertEqual(results, 3)

    def test_difference(self):
        """Checks whether the difference set size is correctly returned. """
        results = _difference([networks['a'][0], networks['b'][0], networks['c'][0]], sign=True)
        self.assertEqual(results, 5)

    def test_difference_sign(self):
        """Checks whether the difference set size is correctly returned. """
        results = _difference([networks['a'][0], networks['b'][0], networks['c'][0]], sign=False)
        self.assertEqual(results, 4)

    def test_generate_sample_sizes(self):
        """Checks whether the subsampled set sizes are correctly returned. """
        perm = 10
        nperm = 10
        new = {'a': [networks['a'][0], networks['b'][0], networks['c'][0]]}
        random, degree = generate_null(new, core=2, n=perm, npos=10)
        results = generate_sample_sizes(new, random_models=random, degree_models=degree,
                                        sign=True, prev=False, core=2,
                                        fractions=False, perm=perm, sizes=[1], limit=False,
                                        number=[1, 2, 3])
        num = 42 * binom(3, 3) + 42 * binom(3, 2) + 42 * binom(3, 1)
        self.assertEqual(int(len(results)), int(num))

    def test_generate_sample_sizes_fractions(self):
        """Checks whether the subsampled set sizes are correctly returned. """
        perm = 10
        nperm = 10
        npos = 10
        new = {'a': [networks['a'][0], networks['b'][0], networks['c'][0]]}
        fractions = [0.2, 0.6]
        prev = [1]
        random_models, degree_models = generate_null(new, n=perm, npos=npos, core=2, fraction=fractions, prev=prev)
        results = generate_sample_sizes(new, random_models=random_models, degree_models=degree_models,
                                        sign=True, prev=[1], core=2,
                                        fractions=[0.2, 0.6], perm=nperm, sizes=[1], limit=False, number=[1, 2, 3])
        # 1 network for original sample
        # 10 * 2 for negative control models
        # 10 * 2 * 2 for positive control models
        # 61 networks total
        # 7 combinations
        # 2 sets (difference and intersection 1)
        number_networks = 61*2
        num = number_networks * binom(3, 3) + \
              number_networks * binom(3, 2) + \
              number_networks * binom(3, 1)
        self.assertEqual(int(len(results)), int(num))

    def test_generate_rows(self):
        """
        Tests whether the dataframe is updated correctly and the absolute intersection size added.
        """
        results = pd.DataFrame(columns=['Network', 'Group', 'Network type', 'Conserved fraction',
                                        'Prevalence of conserved fraction',
                                        'Set type', 'Set size', 'Set type (absolute)'])
        new = {'a': [networks['a'][0], networks['b'][0], networks['c'][0]]}
        values = {'networks': new['a'],
                  'name': 'Test',
                  'group': 'a',
                  'sizes': [0.6, 1],
                  'sign': True,
                  'fraction': None,
                  'prev': None}
        for result in _generate_rows(values):
            all_results = results.append(result, ignore_index=True)
        self.assertEqual(float(all_results[all_results['Set type'] ==
                                           'Intersection 1'].iloc[0]['Set type (absolute)']), 3.0)

    def test_generate_size_differences(self):
        """
        Tests whether the size differences are returned correctly.
        :return:
        """
        perm = 10
        nperm = 10
        new = {'a': [networks['a'][0], networks['a'][0], networks['b'][0]]}
        random, degree = generate_null(new, core=2, n=perm, npos=10)
        results = generate_sizes(new, random_models=random, core=2,
                                 degree_models=degree, prev=None, fractions=False,
                                 perm=nperm, sizes=[0.6, 1], sign=True)
        results = generate_size_differences(results, sizes=[0.6, 1])
        results = results[results['Network'] == 'Input']
        results = results[results['Interval'] == '1->1']
        self.assertEqual(results['Set size'].iloc[0], 4.0)


if __name__ == '__main__':
    unittest.main()
