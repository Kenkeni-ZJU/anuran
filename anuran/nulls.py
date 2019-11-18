"""
The null models module contains functions for constructing permutations of input networks.
Generation of null models is done on the adjacency matrix for speed;
the NetworkX representation is unfortunately slower.
The functions can either change (random model) or preserve (degree model) the degree distribution.

The functions in this module also calculate intersections or differences of networks.
The first function is a wrapper that
subsamples networks from a list of null models to output a dataframe of set sizes.

These functions run operations in parallel. utils.py contains the operations they carry out.

"""

__author__ = 'Lisa Rottjers'
__email__ = 'lisa.rottjers@kuleuven.be'
__status__ = 'Development'
__license__ = 'Apache 2.0'

from anuran.utils import _generate_null_parallel
import multiprocessing as mp

import logging.handlers

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def generate_null(networks, n, core, fraction=False, prev=False):
    """
    This function takes a list of networks.
    For each network, a list with length n is generated,
    with each item in the list being a permutation of the original network.
    This is returned as a list of lists with this structure:
    ---List corresponding to each original network (length networks)
        ---List of permutations per original network (length n)
    :param networks: List of input NetworkX objects
    :param n: Number of randomized networks per input network
    :param core: Number of processor cores
    :param fraction: Fraction of conserved interactions
    :param prev: Prevalence of core. If provided, null models have conserved interactions.
    :return: List of lists with randomized networks
    """
    all_results = {'random': {x: {'random': [], 'core': {}} for x in networks},
                   'degree': {x: {'degree': [], 'core': {}} for x in networks}}
    # firt generate list of network models that need to be generated
    all_models = list()
    for x in networks:
        all_models.append({'networks': networks[x],
                           'name': x,
                           'fraction': None,
                           'prev': None,
                           'n': n,
                           'mode': 'random'})
        all_models.append({'networks': networks[x],
                           'name': x,
                           'fraction': None,
                           'prev': None,
                           'n': n,
                           'mode': 'degree'})
        if fraction:
            for frac in fraction:
                all_results['random'][x]['core'][frac] = dict()
                all_results['degree'][x]['core'][frac] = dict()
                for p in prev:
                    all_models.append({'networks': networks[x],
                                       'name': x,
                                       'fraction': frac,
                                       'prev': p,
                                       'n': n,
                                       'mode': 'random'})
                    all_models.append({'networks': networks[x],
                                       'name': x,
                                       'fraction': frac,
                                       'prev': p,
                                       'n': n,
                                       'mode': 'degree'})
    # run size inference in parallel
    pool = mp.Pool(core)
    results = pool.map(_generate_null_parallel, all_models)
    pool.close()
    for result in results:
        if len(result[0]) == 3:
            all_results[result[0][0]][result[0][1]][result[0][2]] = result[1]
        else:
            all_results[result[0][0]][result[0][1]][result[0][2]][result[0][3]][result[0][4]] = result[1]
    return all_results['random'], all_results['degree']

