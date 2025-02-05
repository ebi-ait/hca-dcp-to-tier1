import os
import argparse

from flatten_dcp import main as flatten_dcp
from dcp_to_tier1 import main as dcp_to_tier1


def define_parser():
    """Defines and returns the argument parser."""
    parser = argparse.ArgumentParser(description='Parser for the arguments')
    parser.add_argument('-s', '--spreadsheet_filename', action='store',
                        dest='spreadsheet_filename', type=str, required=True, help='dcp spreadsheet filename')
    parser.add_argument('-i', '--input_dir', action='store', default='dcp_spreadsheet',
                        dest='input_dir', type=str, required=False, help='directory of the dcp spreadsheet file')
    parser.add_argument('-f', '--flat_dir', action='store', default='denormalised_spreadsheet',
                        dest='flat_dir', type=str, required=False, help='directory for the denormalised spreadsheet output')
    parser.add_argument('--output_dir', '-o', action='store', default='tier1_output',
                        dest='output_dir', type=str, required=False, help='directory for the tier1 spreadsheet output')
    parser.add_argument("-g", "--group_field", action="store", default='specimen_from_organism.biomaterial_core.biomaterial_id',
                        dest="group_field", type=str, required=False, help="field to group output with")
    parser.add_argument('-d', action='store_true', dest='denormalised', required=False,
                        help='use the denormalised flat file instead of the grouped one')
    return parser

def main(spreadsheet_filename, input_dir, flat_dir, output_dir, group_field, denormalised):

    os.makedirs(flat_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    flatten_dcp(spreadsheet_filename, input_dir, flat_dir, group_field)
    flat_filename = spreadsheet_filename.replace('.xlsx', '_denormalised.csv' if denormalised else '_grouped.csv')
    dcp_to_tier1(flat_filename, flat_dir, output_dir)

if __name__ == "__main__":
    args = define_parser().parse_args()

    main(spreadsheet_filename=args.spreadsheet_filename, input_dir=args.input_dir, 
        flat_dir=args.flat_dir, output_dir=args.output_dir,
        group_field=args.group_field, denormalised=args.denormalised)