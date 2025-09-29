import os
import argparse

from src.flatten_dcp import main as flatten_dcp
from src.convert_flat_dcp_to_tier1 import main as dcp_to_tier1


FLAT_DIR = 'data/denormalised_spreadsheet'
OUTPUT_DIR = 'data/tier1_output'


def define_parser():
    """Defines and returns the argument parser."""
    parser = argparse.ArgumentParser(description='Parser for the arguments')
    parser.add_argument('-s', '--spreadsheet_path', action='store',
                        dest='spreadsheet_path', type=str, required=True, help='dcp spreadsheet path')
    parser.add_argument("-g", "--group_field", action="store", default='specimen_from_organism.biomaterial_core.biomaterial_id',
                        dest="group_field", type=str, required=False, help="DCP field to group output with")
    parser.add_argument('-d', action='store_true', dest='denormalised', required=False,
                        help='use the denormalised flat file instead of the grouped one')
    return parser

def main(spreadsheet_path, flat_dir, output_dir, group_field, denormalised):

    os.makedirs(flat_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    if group_field == "" or denormalised:
        denormalised = True
        group_field = ""

    flatten_dcp(spreadsheet_path, flat_dir, group_field)
    flat_filename = os.path.basename(spreadsheet_path).replace('.xlsx', '_denormalised.csv' if denormalised else '.csv')
    dcp_to_tier1(os.path.join(flat_dir, flat_filename), output_dir)

if __name__ == "__main__":
    args = define_parser().parse_args()

    main(spreadsheet_path=args.spreadsheet_path, flat_dir=FLAT_DIR, output_dir=OUTPUT_DIR,
        group_field=args.group_field, denormalised=args.denormalised)