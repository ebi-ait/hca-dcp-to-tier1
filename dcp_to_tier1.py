import os
import argparse

from src.flatten_dcp import main as flatten_dcp
from src.convert_flat_dcp_to_tier1 import main as dcp_to_tier1


INPUT_DIR = 'data/dcp_spreadsheet'
FLAT_DIR = 'data/denormalised_spreadsheet'
OUTPUT_DIR = 'data/tier1_output'


def define_parser():
    """Defines and returns the argument parser."""
    parser = argparse.ArgumentParser(description='Parser for the arguments')
    parser.add_argument('-s', '--spreadsheet_filename', action='store',
                        dest='spreadsheet_filename', type=str, required=True, help='dcp spreadsheet filename')
    parser.add_argument("-g", "--group_field", action="store", default='specimen_from_organism.biomaterial_core.biomaterial_id',
                        dest="group_field", type=str, required=False, help="DCP field to group output with")
    parser.add_argument('-d', action='store_true', dest='denormalised', required=False,
                        help='use the denormalised flat file instead of the grouped one')
    return parser

def main(spreadsheet_filename, input_dir, flat_dir, output_dir, group_field, denormalised):

    os.makedirs(flat_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    if spreadsheet_filename.startswith('data/' + input_dir):
        spreadsheet_filename = spreadsheet_filename.removeprefix('data' + '/' + input_dir + '/')
    elif spreadsheet_filename.startswith(input_dir):
        spreadsheet_filename = spreadsheet_filename.removeprefix(input_dir + "/")

    flatten_dcp(spreadsheet_filename, input_dir, flat_dir, group_field)
    flat_filename = spreadsheet_filename.replace('.xlsx', '_denormalised.csv' if denormalised else '_grouped.csv')
    dcp_to_tier1(flat_filename, flat_dir, output_dir)

if __name__ == "__main__":
    args = define_parser().parse_args()

    main(spreadsheet_filename=args.spreadsheet_filename, 
        input_dir=INPUT_DIR, flat_dir=FLAT_DIR, output_dir=OUTPUT_DIR, 
        group_field=args.group_field, denormalised=args.denormalised)