#!/usr/bin/env python

"""
numma: Null models for replicate networks.
The script takes a network as input and uses this to generate null models.
The output of the null models is presented as a csv of set sizes
and a t-test is used to assess whether set sizes are different than expected from the null model.
Detailed explanations are available in the headers of each file.

numma uses the file extension to import networks.
Generation of null models is done on the adjacency matrix for speed;
the NetworkX representation is unfortunately slower.

The demo data for numma was downloaded from the following publication:
Meyer, K. M., Memiaghe, H., Korte, L., Kenfack, D., Alonso, A., & Bohannan, B. J. (2018).
Why do microbes exhibit weak biogeographic patterns?. The ISME journal, 12(6), 1404.
"""

__author__ = 'Lisa Rottjers'
__email__ = 'lisa.rottjers@kuleuven.be'
__status__ = 'Development'
__license__ = 'Apache 2.0'

import networkx as nx
import sys
import os
import argparse
import glob

import numma
from numma.nullmodels import generate_null, generate_core
from numma.set import generate_sizes, generate_sample_sizes
from numma.centrality import generate_ci_frame
from numma.graphvals import generate_graph_frame
from numma.setviz import draw_sets, draw_samples, draw_centralities
import logging.handlers
from pbr.version import VersionInfo

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# handler to sys.stdout
sh = logging.StreamHandler(sys.stdout)
sh.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
sh.setFormatter(formatter)
logger.addHandler(sh)


def set_numma():
    """This parser gets input settings for running numma.
    It requires an input format that can be read by NetworkX.
    Make sure to include the extension in the input filename
    as this is used to infer the file type."""
    parser = argparse.ArgumentParser(
        description='Run the microbial association network clustering algorithm.'
                    'If --central is added, centrality is calculated. '
                    'Exporting as .cyjs allows for import into Cytoscape with '
                    'a cluster- and phylogeny-informed layout.')
    parser.add_argument('-i', '--input_graphs',
                        dest='graph',
                        help='Locations of input network files. The format is detected based on the extension; \n'
                             'at the moment, .graphml, .txt (weighted edgelist), .gml and .cyjs are accepted. \n'
                             'If you set -i to "demo", a demo dataset will be loaded. \n'
                             'If you want to compare different sets of networks, \n'
                             'specify this by including multiple locations. ',
                        default=None,
                        required=False,
                        nargs='+')
    parser.add_argument('-o', '--output',
                        dest='fp',
                        help='Output filename. Specify full file path without extension.',
                        default=None, required=False)
    parser.add_argument('-set', '--set_type',
                        dest='set',
                        required=False,
                        help='Types of sets to compare. \n'
                             'By default, both the difference and intersection are calculated.',
                        choices=['difference', 'intersection'],
                        nargs='+',
                        default=['difference', 'intersection'])
    parser.add_argument('-size', '--intersection_size',
                        dest='size',
                        required=False,
                        nargs='+',
                        default=[1],
                        help='If specified, associations only shared by a number of networks '
                             'times the specified size fraction are included. \n'
                             'You can specify multiple numbers. By default, the full intersection is calculated.')
    parser.add_argument('-sign', '--edge_sign',
                        dest='sign',
                        required=False,
                        help='If flagged, signs of edge weights are not taken into account. \n'
                             'The set difference then includes edges that have a unique edge sign in one network. \n'
                             'The set intersection then only includes edges that have the same sign across networks.',
                        default=True,
                        action='store_false')
    parser.add_argument('-sample', '--resample',
                        dest='sample',
                        required=False,
                        type=int,
                        help='Resample your networks to observe the impact of increasing sample number. \n'
                             'when you increase the network number up until the total. \n'
                             'Specify an upper limit of resamples, or True if you want all possible resamples. \n'
                             'By default, the upper limit equal to the binomial coefficient of the input networks. \n'
                             'If the limit is higher than this coefficient, all possible combinations are resampled.',
                        default=False)
    parser.add_argument('-n', '--sample_number',
                        dest='number',
                        required=False,
                        nargs='+',
                        default=None,
                        help='If you have a lot of samples, specify the sample numbers to test here. \n'
                             'For example: -n 4 8 12 will test the effect of acquiring 4, 8, and 12 samples. \n'
                             'By default, all sample numbers are tested.')
    parser.add_argument('-cs', '--core_size',
                        dest='cs',
                        required=False,
                        nargs='+',
                        default=False,
                        help='If specified, true positive null models '
                             ' include a set fraction of shared interactions. \n'
                             'You can specify multiple fractions. '
                             'By default, null models have no shared interactions and '
                             'sets are computed for all randomized networks.\n. ')
    parser.add_argument('-prev', '--core_prevalence',
                        dest='prev',
                        required=False,
                        nargs='+',
                        help='Specify the prevalence of the core. \n'
                             'By default, 1; each interaction is present in all models.',
                        default=[1])
    parser.add_argument('-perm', '--permutations',
                        dest='perm',
                        type=int,
                        required=False,
                        help='Number of null models to generate for each input network. \n'
                             'Default: 10. ',
                        default=10)
    parser.add_argument('-nperm', '--permutationsets',
                        dest='nperm',
                        required=False,
                        type=int,
                        help='Number of sets to calculate from the null models. \n'
                             'The total number of possible sets is equal to \n'
                             'the number of null models raised to the number of networks.\n '
                             'This value becomes huge quickly, so a random subset of possible sets is taken.\n '
                             'Default: 50. ',
                        default=50)
    parser.add_argument('-c', '--centrality',
                        dest='centrality',
                        required=False,
                        action='store_true',
                        help='If true, extracts centrality ranking from networks \n'
                             'and compares these to rankings extracted from null models. ',
                        default=False)
    parser.add_argument('-net', '--network',
                        dest='network',
                        required=False,
                        action='store_true',
                        help='If true, extracts network-level properties \n'
                             'and compares these to properties of randomized networks. ',
                        default=False)
    parser.add_argument('-compare', '--compare_networks',
                        dest='comparison',
                        required=False,
                        help='If true, networks in the folders specified by the input parameter \n'
                             'are compared for different emergent properties. ',
                        default=False)
    parser.add_argument('-draw', '--draw_figures',
                        dest='draw',
                        required=False,
                        help='If flagged, draws figures showing the set sizes.',
                        action='store_true',
                        default=False)
    parser.add_argument('-p', '--pvals',
                        dest='pvals',
                        required=False,
                        help='If flagged, p-values are computed for the comparisons to null models \n'
                             'and to subsets of the networks.',
                        action='store_true',
                        default=False)
    parser.add_argument('-version', '--version',
                        dest='version',
                        required=False,
                        help='Version number.',
                        action='store_true',
                        default=False)
    return parser


def main():
    args = set_numma().parse_args(sys.argv[1:])
    args = vars(args)
    if args['version']:
        info = VersionInfo('numma')
        logger.info('Version ' + info.version_string())
        exit(0)
    if not args['graph']:
        logger.info('Please give an input location.')
    if args['graph'] != ['demo']:
        networks = {x: list() for x in args['graph']}
        # code for importing from multiple folders
        for location in args['graph']:
            files = [f for f in glob.glob(location + "**/*.graphml", recursive=True)]
            files.extend([f for f in glob.glob(location + "**/*.txt", recursive=True)])
            files.extend([f for f in glob.glob(location + "**/*.gml", recursive=True)])
            for file in files:
                filename = file.split(sep=".")
                extension = filename[len(filename)-1]
                try:
                    if extension == 'graphml':
                        network = nx.read_graphml(file)
                    elif extension == 'txt':
                        network = nx.read_weighted_edgelist(file)
                    elif extension == 'gml':
                        network = nx.read_gml(file)
                    else:
                        logger.warning('Format not accepted. '
                                       'Please specify the filename including extension (e.g. test.graphml).', exc_info=True)
                        exit()
                    # need to make sure the graphml function does not arbitrarily assign node ID
                    try:
                        if 'name' in network.nodes[list(network.nodes)[0]]:
                            if network.nodes[list(network.nodes)[0]]['name'] != list(network.nodes)[0]:
                                network = nx.relabel_nodes(network, nx.get_node_attributes(network, 'name'))
                    except IndexError:
                        logger.warning('One of the imported networks contains no nodes.', exc_info=True)
                    networks.append(network)
                except Exception:
                    logger.error('Could not import network file!', exc_info=True)
                    exit()
    elif args['graph'] == ['demo']:
        networks = {'demo': list()}
        path = os.path.dirname(numma.__file__)
        networks['demo'].append(nx.read_graphml(path + '//data//conet_family_a.graphml'))
        networks['demo'].append(nx.read_graphml(path + '//data//conet_family_b.graphml'))
        networks['demo'].append(nx.read_graphml(path + '//data//conet_family_c.graphml'))
    logger.info('Imported ' + str(len(networks)) + ' networks.')
    # first generate null models
    random = {x: {'random': [], 'core': {}} for x in networks}
    try:
        for x in networks:
            random[x]['random'] = generate_null(networks[x], n=args['perm'], share=0, mode='random')
            if args['cs']:
                for frac in args['cs']:
                    random[x]['core'][frac] = dict()
                    for core in args['prev']:
                        random[x]['core'][frac][core] = generate_core(networks[x],
                                                                      share=float(frac), mode='random',
                                                                      core=float(core))
                logger.info('Finished constructing all randomized networks.')
    except Exception:
        logger.error('Could not generate randomized null models!', exc_info=True)
        exit()
    degree = {x: {'degree': [], 'core': {}} for x in networks}
    try:
        for x in networks:
            degree[x]['degree'] = generate_null(networks[x], n=args['perm'], share=0, mode='degree')
            if args['cs']:
                for frac in args['cs']:
                    degree[x]['core'][frac] = dict()
                    for core in args['prev']:
                        degree[x]['core'][frac][core] = generate_core(networks[x],
                                                                      share=float(frac), mode='degree',
                                                                      core=float(core))
            logger.info('Finished constructing all degree-preserving randomized networks.')
    except Exception:
        logger.error('Could not generate degree-preserving null models! '
                     'Try increasing the conserved fraction. ', exc_info=True)
        exit()
    set_sizes = None
    try:
        set_sizes = generate_sizes(networks, random, degree,
                                   sign=args['sign'], set_operation=args['set'],
                                   fractions=args['cs'], core=args['prev'],
                                   perm=args['nperm'], sizes=args['size'])
        set_sizes.to_csv(args['fp'] + '_sets.csv')
        logger.info('Set sizes exported to: ' + args['fp'] + '_sets.csv')
    except Exception:
        logger.error('Failed to calculate set sizes!', exc_info=True)
        exit()
    if args['centrality']:
        try:
            centralities = generate_ci_frame(networks, random, degree,
                                             fractions=args['cs'], core=args['prev'], perm=args['nperm'])
            centralities.to_csv(args['fp'] + '_centralities.csv')
        except Exception:
            logger.error('Could not rank centralities!', exc_info=True)
            exit()
    if args['network']:
        try:
            graph_properties = generate_graph_frame(networks, random, degree,
                                             fractions=args['cs'], core=args['prev'], perm=args['nperm'])
            graph_properties.to_csv(args['fp'] + 'graph_properties.csv')
        except Exception:
            logger.error('Could not rank centralities!', exc_info=True)
            exit()
    samples = None
    if args['sample']:
        try:
            samples = generate_sample_sizes(networks, random, degree,
                                            sign=args['sign'], set_operation=args['set'],
                                            fractions=args['cs'], perm=args['nperm'], core=args['prev'],
                                            sizes=args['size'], limit=args['sample'], number=args['number'])
            samples.to_csv(args['fp'] + '_subsampled_sets.csv')
            logger.info('Subsampled set sizes exported to: ' + args['fp'] + '_subsampled_sets.csv')
        except Exception:
            logger.error('Failed to subsample networks!', exc_info=True)
            exit()
    if args['pval']:
        # add code for pvalue estimation
        pass
    if args['draw']:
        try:
            draw_sets(set_sizes, args['fp'])
            if args['centrality']:
                draw_centralities(centralities, args['fp'])
            if args['sample']:
                draw_samples(samples, args['fp'])
        except Exception:
            logger.error('Could not draw data!', exc_info=True)
            exit()
    logger.info('numma completed all tasks.')
    exit(0)


if __name__ == '__main__':
    main()
