#!/usr/bin/env python

# ----------------------------------------------------------------------------
# Copyright (c) 2015--, The Horizomer Development Team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

#
# Parse output files of HGT tools.
#

import click
import sys
from skbio import Sequence


# T-REX version 3.6
# RANGER-DTL-U version 1.0
# RIATA-HGT version 3.5.6
# JANE version 4
# each tuple consists of three strings, first string is the unique string to
# identify the line with HGT information, second and third strings are the
# bounds for the actual number of HGTs
hgt_parse_strs = {
    'ranger-dtl': ('The minimum reconciliation cost is: ',
                   'Transfers: ',
                   ', Losses'),
    'trex': ('hgt : number of HGT(s) found = ',
             'hgt : number of HGT(s) found = ',
             ' '),
    'jane4': ('Host Switch: ',
              'Host Switch: ',
              ' '),
    'riata-hgt': ('There are ',
                  'There are ',
                  ' component(s)')}


def parse_hgts(input_f, method):
    """ Extract number of HGTs found.

    Parameters
    ----------
    input_f: string
        file descriptor for T-REX output results
    method: string
        HGT detection method

    Returns
    -------
    number_of_hgts: string
        number of HGTs reported by a tool, or NaN if an entry was not found
    """
    for line in input_f:
        if hgt_parse_strs[method][0] in line:
            return line.strip().split(
                hgt_parse_strs[method][1])[1].split(
                    hgt_parse_strs[method][2])[0]
    return 'NaN'


def parse_consel(input_f):
    """ Parse output of Consel version 0.20.

    Parameters
    ----------
    input_f: string
        file descriptor for Consel output results

    Returns
    -------
    pvalues: list
        list of P-values
    """
    pvalues = []
    # skip header lines
    skip_lines = 3
    for s in range(skip_lines):
        next(input_f)

    for line in input_f:
        line = line.split()
        # skip empty line at bottom of file
        if not line:
            continue
        pv_au = line[4]
        if 0 <= float(pv_au) <= 1:
            pvalues.append("%.2f" % float(pv_au))
    return pvalues


def parse_darkhorse(input_f, output_fp, low_lpi=0.0, high_lpi=0.6):
    """ Parse output of DarkHorse (smry file).

    Paramters
    ---------
    input_f: string
        file descriptor for Consel output results
    output_fp: str
        Filepath to output best hit genome IDs
    low_lpi: float
        lower LPI (lineage probability index) score bound
    high_lpi: float
        upper LPI score bound

    Returns
    -------
    hgts: string
        one putative HGT-derived gene per line
        columns: query_id, besthit_id, tax_id, species, lineage, pct_id,
        pct_coverage, norm_LPI

    Notes
    -----
    Parse output of DarkHorse to return tab-separated file of putative HGTs
    using the LPI bounds and a file with all best hit genome IDs.
    """
    best_hit_ids = set()
    hgts = []
    # skip header
    next(input_f)
    for l in input_f:
        l = l.strip('\r\n').split('\t')
        best_hit_ids.add(l[3])
        if low_lpi < float(l[5]) < high_lpi:
            hgt = '\t'.join((l[0], l[3], l[12], l[13], l[14],
                             l[6], l[9], l[4]))
            hgts.append(hgt)
    if output_fp:
        with open(output_fp, 'w') as output_f:
            output_f.write('\n'.join(best_hit_ids))
    return '\n'.join(hgts)


def parse_hgtector(input_f):
    """ Parse output of HGTector version 0.2.1.

    Parameters
    ----------
    input_f: string
        file descriptor for HGTector output results

    Returns
    -------
    output: string
        one putative HGT-derived gene per line
        columns: query_id, donor_taxid, donor_species, donor_lineage, pct_id,
        pct_coverage
    """
    hgts = []
    for line in input_f:
        l = line.strip('\r\n').split('\t')
        if (len(l) == 15) and (l[7] == '1'):
            hgt = '\t'.join((l[0], l[12], l[13], l[14], l[10], l[11]))
            hgts.append(hgt)
    return '\n'.join(hgts)


def parse_egid(input_f, genbank_fp):
    """ Extract genes contained in GIs identified by EGID

    Parameters
    ----------
    input_f: string
        file descriptor for EGID output results (GI coordinates)
    genbank_fp: string
        file path to genome in GenBank format (containing gene coordinates)

    Notes
    -----
    genbank_fp is the intermediate GenBank file generated by reformat_input.py,
    in which multiple sequences are concantenated, instead of the original
    GenBank file.

    Returns
    -------
    output: string
        gene names (protein_ids) separated by newline
    """
    genes = {}
    gb = Sequence.read(genbank_fp, format='genbank')
    for feature in gb.interval_metadata.query(metadata={'type': 'CDS'}):
        m = feature.metadata
        if 'protein_id' in m:
            protein_id = m['protein_id'].replace('\"', '')
            if protein_id not in genes:
                # in scikit-bio, this number is the start location - 1
                start = feature.bounds[0][0] + 1
                end = feature.bounds[0][1]
                genes[protein_id] = (start, end)
    genes_in_gi = {}
    for line in input_f:
        l = line.strip().split()
        # a valid GI definition should have at least 2 columns
        if len(l) < 2:
            continue
        start = int(l[0])
        end = int(l[1])
        for (gene, pos) in genes.items():
            if (pos[0] >= start and pos[1] <= end):
                if gene not in genes_in_gi:
                    genes_in_gi[gene] = 1
    return '\n'.join(sorted(genes_in_gi))


def parse_genemark(input_f, genbank_fp):
    """ Extract atypical genes identified by GeneMark

    Parameters
    ----------
    input_f: string
        file descriptor for GeneMark output gene list (*.lst)
    genbank_fp: string
        file path to genome in GenBank format

    Notes
    -----
    genbank_fp is the intermediate GenBank file generated by reformat_input.py,
    in which multiple sequences are concantenated, instead of the original
    GenBank file.

    Returns
    -------
    output: string
        gene names (protein_ids) separated by newline
    """
    genes = {}
    gb = Sequence.read(genbank_fp, format='genbank')
    for feature in gb.interval_metadata._intervals:
        m = feature.metadata
        if m['type'] == 'CDS' and 'protein_id' in m:
            protein_id = m['protein_id'].replace('\"', '')
            if protein_id not in genes:
                strand = m['strand']
                start = feature.bounds[0][0] + 1
                end = feature.bounds[0][1]
                genes[protein_id] = (start, end, strand)
    atypical_genes = []
    reading = False
    for line in input_f:
        l = line.strip().split()
        if len(l) == 2 and l == ['#', 'Length']:
            reading = True
        # atypical genes have class '2' in the 6th column
        elif reading and len(l) == 6 and l[5] == '2':
            (start, end, strand) = (int(l[2].lstrip('<>')),
                                    int(l[3].lstrip('<>')),
                                    l[1])
            for (gene, l) in genes.items():
                if l[0] == start and l[1] == end and l[2] == strand:
                    atypical_genes.append(gene)
    return '\n'.join(sorted(atypical_genes))


def parse_output(hgt_results_fp,
                 method,
                 genbank_fp=None,
                 low_lpi=0.0,
                 high_lpi=0.6,
                 output_fp=None):
    """Call parse_hgts() based on HGT detection method used.
    Parameters
    ----------
    hgt_results_fp: str
        filepath to detected HGTs
    genbank_fp: string
        file path to genome in GenBank format
    method: string
        tool used to detect HGTs
    output_fp: str
        output file storing best hit IDs (DarkHorse)
    low_lpi: float
        lower bound LPI score (DarkHorse Lineage Probability Index)
    high_lpi: float
        upper bound LPI score (DarkHorse Lineage Probability Index)
    Returns
    -------
    output: string
        number of HGTs detected
    """
    with open(hgt_results_fp, 'r') as input_f:
        if (method == 'ranger-dtl' or
                method == 'trex' or
                method == 'jane4' or
                method == 'riata-hgt'):
            output = parse_hgts(input_f=input_f,
                                method=method)
        elif method == 'consel':
            output = parse_consel(input_f=input_f)
        elif method == 'darkhorse':
            output = parse_darkhorse(input_f=input_f,
                                     output_fp=output_fp,
                                     low_lpi=low_lpi,
                                     high_lpi=high_lpi)
        elif method == 'hgtector':
            output = parse_hgtector(input_f=input_f)
        elif method == 'egid':
            output = parse_egid(input_f=input_f,
                                genbank_fp=genbank_fp)
        elif method == 'genemark':
            output = parse_genemark(input_f=input_f,
                                    genbank_fp=genbank_fp)
        else:
            raise ValueError("Method is not supported: %s" % method)
        return output


@click.command()
@click.option('--hgt-results-fp', required=True,
              type=click.Path(resolve_path=True, readable=True, exists=True,
                              file_okay=True),
              help='Output file containing HGT information')
@click.option('--genbank-fp', required=False,
              type=click.Path(resolve_path=True, readable=True, exists=True,
                              file_okay=True),
              help='Output file containing HGT information')
@click.option('--ncbi-nr', required=False,
              type=click.Path(resolve_path=True, readable=True, exists=True,
                              file_okay=True),
              help='NCBI nr database in FASTA format to link'
                   'taxon ids with accession numbers for DarkHorse output')
@click.option('--method', required=True,
              type=click.Choice(['trex', 'ranger-dtl',
                                 'riata-hgt', 'consel',
                                 'darkhorse', 'hgtector',
                                 'genemark', 'egid', 'jane4',
                                 'tree-puzzle']),
              help='The method used for HGT detection')
@click.option('--darkhorse-low-lpi', type=float, default=0.0,
              show_default=True, required=False, help='Lower bound LPI score')
@click.option('--darkhorse-high-lpi', type=float, default=0.6,
              show_default=True, required=False, help='Upper bound LPI score')
@click.option('--darkhorse-output-fp', required=False,
              type=click.Path(resolve_path=True, readable=True, exists=False,
                              file_okay=True),
              help='Output all best hit IDs from DarkHorse summary')
def main(hgt_results_fp,
         genbank_fp,
         method,
         ncbi_nr,
         darkhorse_low_lpi,
         darkhorse_high_lpi,
         darkhorse_output_fp=None):
    """ Parsing functions for various HGT detection tool outputs.
    """
    output = parse_output(hgt_results_fp=hgt_results_fp,
                          method=method,
                          genbank_fp=genbank_fp,
                          low_lpi=darkhorse_low_lpi,
                          high_lpi=darkhorse_high_lpi,
                          output_fp=darkhorse_output_fp)
    sys.stdout.write(output)


if __name__ == "__main__":
    main()
