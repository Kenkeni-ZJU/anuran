"""
The functions in this module calculate different graph-level properties.

The first function is a wrapper that
subsamples networks from a list of null models to output a dataframe of set sizes.
"""

__author__ = 'Lisa Rottjers'
__email__ = 'lisa.rottjers@kuleuven.be'
__status__ = 'Development'
__license__ = 'Apache 2.0'

import pandas as pd
import networkx as nx
from random import sample
import numpy as np
import os


def generate_graph_frame(networks, random, degree, fractions, core, perm):
    """
    This function estimates graph-level properties of all networks provided in
    the network, random and degree lists.
    The random and degree lists are structured as follows:
    ---List corresponding to each original network (length networks)
        ---List of permutations per original network (length n in generate_null)
    The core list is structured as follows:
    ---List of all shared fractions (length fractions)
        ---List corresponding to core prevalence(length core)
            ---List of permutations per original network (length networks)
    The function returns a pandas dataframe with the size of the intersection,
    the type of model and the shared fraction as a separate column.
    The length of the dataset is equal to the number of original networks,
    the number of permuted sets for the random models and the number of permuted sets
    for the degree-preserving model.
    :param networks: List of input networks
    :param random: Dictionary with permuted input networks without preserved degree distribution
    :param degree: Dictionary with permuted input networks with preserved degree distribution
    :param fractions: List with fractions of shared interactions
    :param core: List with prevalence of shared interactions
    :param perm: Number of sets to take from null models
    :return: List of lists with set sizes
    """
    # Create empty pandas dataframe
    results = pd.DataFrame(columns=['Network', 'Name', 'Group', 'Network type', 'Conserved fraction',
                                    'Prevalence of conserved fraction',
                                    'Property', 'Value'])
    for x in networks:
        group = os.path.basename(x)
        results = _generate_graph_rows(name='Input', data=results, group=group,
                                       networks=networks[x], fraction=None, prev=None, perm=None)
        # construct the subsampled model sets nperm times
        for i in range(perm):
            degreeperm = [sample(degree[x]['degree'][r], 1)[0] for r in range(len(degree[x]['degree']))]
            results = _generate_graph_rows(name='Degree', data=results, group=group,
                                           networks=degreeperm, fraction=None, prev=None, perm=i)
            randomperm = [sample(random[x]['random'][r], 1)[0] for r in range(len(random[x]['random']))]
            results = _generate_graph_rows(name='Random', data=results, group=group,
                                           networks=randomperm, fraction=None, prev=None, perm=i)
        if fractions:
            num_models = len(random[group]['core'][fractions[0]][core[0]])
            for frac in fractions:
                for c in core:
                    for i in range(num_models):
                        degreeperm = degree[x]['core'][frac][c][i]
                        randomperm = random[x]['core'][frac][c][i]
                        results = _generate_graph_rows(name='Degree', data=results, group=group,
                                                       networks=degreeperm, fraction=frac, prev=c, perm=None)
                        results = _generate_graph_rows(name='Random', data=results, group=group,
                                                       networks=randomperm, fraction=frac, prev=c, perm=None)
    return results


def _generate_graph_rows(data, name, group, networks, fraction, prev, perm):
    """
    Generates Pandas rows with network measures for a list of networks.

    :param data: Pandas dataframe
    :param name: Name for the list of NetworkX objects
    :param group: Name for grouping NetworkX objects
    :param networks: List of NetworkX objects
    :param fraction: If a null model with core is provided, adds the core fraction to the row
    :param prev: If a null model with core is provided, adds the core prevalence to the row
    :param perm: iteration of graph subsampling, necessary for permutation testing
    :return: Pandas dataframe with added rows
    """
    full_name = name + ' networks'
    if fraction:
        name += ' size: ' + str(fraction) + ' prev:' + str(prev)
    properties = generate_graph_properties(networks)
    for property in properties:
        for network in properties[property]:
            data = data.append({'Network': name,
                                'Name': network[0],
                                'Group': group,
                                'Network type': full_name,
                                'Conserved fraction': fraction,
                                'Prevalence of conserved fraction': prev,
                                'Property': property,
                                'Value': network[1],
                                'iteration': perm},
                               ignore_index=True)
    return data


def generate_graph_properties(networks):
    """
    This function constructs lists with centrality rankings of nodes in multiple networks.
    Instead of using the absolute degree or betweenness centrality, this takes metric bias into account.

    If the graph is not connected, the values are calculated for the largest connected component.

    :param networks: List of input networks
    :return: Pandas dataframe with rankings
    """
    properties = dict()
    property_names = ['Assortativity', 'Connectivity', 'Diameter', 'Radius', 'Average shortest path length']
    for property in property_names:
        properties[property] = list()
    for network in networks:
        if len(network[1].nodes) > 0:
            properties['Assortativity'].append((network[0],
                                                nx.degree_pearson_correlation_coefficient(network[1])))
            properties['Connectivity'].append((network[0],
                                               nx.average_node_connectivity(network[1])))
            if nx.is_connected(network[1]):
                properties['Diameter'].append((network[0], nx.diameter(network[1])))
                properties['Radius'].append((network[0], nx.radius(network[1])))
                properties['Average shortest path length'].append((network[0],
                                                                   nx.average_shortest_path_length(network[1])))
            else:
                components = list(nx.connected_components(network[1]))
                sizes = []
                for component in components:
                    sizes.append(len(component))
                subnetwork = nx.subgraph(network[1], components[np.where(np.max(sizes) == sizes)[0][0]])
                properties['Diameter'].append((network[0], nx.diameter(subnetwork)))
                properties['Radius'].append((network[0], nx.radius(subnetwork)))
                properties['Average shortest path length'].append((network[0],
                                                                  nx.average_shortest_path_length(subnetwork)))
        else:
            properties['Assortativity'].append(None)
            properties['Connectivity'].append(None)
            properties['Diameter'].append(None)
            properties['Radius'].append(None)
            properties['Average shortest path length'].append(None)
    return properties


