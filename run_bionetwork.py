import os
import argparse
import zipfile

import pandas as pd
from dcp_to_tier1 import main as dcp_to_tier1

INPUT_DIR = 'data/dcp_spreadsheet'
FLAT_DIR = 'data/denormalised_spreadsheet'
OUTPUT_DIR = 'data/tier1_output'
GROUP_FIELD = 'specimen_from_organism.biomaterial_core.biomaterial_id'
DENORMALISED = False

def define_parser():
    parser = argparse.ArgumentParser(description='Run bionetwork script')
    parser.add_argument('--bionetwork', '-b', action='store', dest='bionetwork', type=str, 
                        required=True, help='Name of the bionetwork to process')
    parser.add_argument('--csv', '-c', action='store', dest='csv', type=str,
                        required=False, default='data/bionetworks.csv', help='Path to bionetwork CSV file')
    parser.add_argument('--group_field', '-g', action='store', dest='group_field', type=str,
                        required=False, default=GROUP_FIELD, help='DCP field to group output with')
    parser.add_argument('--denormalised', '-d', action='store_true', dest='denormalised',
                        required=False, default=DENORMALISED, help='use the denormalised flat file instead of the grouped one')
    return parser

def make_zipfile(input_filenames:list, output_filename:str):
    with zipfile.ZipFile(output_filename, "w") as zip_file:
        for filename in input_filenames:
            zip_file.write(filename, arcname=os.path.basename(filename))
    print(f"Zip file created at {output_filename}")

def select_zip_files(xlsx_files, denormalised):
    tier1_files = []
    extensions = [f'_denormalised_tier1.{format}' if denormalised else f'_tier1.{format}' for format in ['csv', 'xlsx']]
    for extension in extensions:
        for xlsx_file in xlsx_files:
            output_file = f"{OUTPUT_DIR}/{xlsx_file.replace('.xlsx', extension)}"
            if os.path.exists(output_file):
                tier1_files.append(output_file)
    return tier1_files

def main(csv, bionetwork, group_field, denormalised):
    df = pd.read_csv(csv)
    xlsx_files = df.loc[df['bionetwork'] == bionetwork.lower(), 'spreadsheet'].tolist()
    for xlsx_file in xlsx_files:
        if xlsx_file not in os.listdir(INPUT_DIR):
            print(f"File {xlsx_file} not found in {INPUT_DIR}")
            continue
        print(f"=====Processing {xlsx_file}=====")
        dcp_to_tier1(xlsx_file, INPUT_DIR, FLAT_DIR, OUTPUT_DIR, group_field, denormalised)
    
    tier1_files = select_zip_files(xlsx_files, denormalised)
    output_filename = f"{OUTPUT_DIR}/{bionetwork}_denormalised_tier1.zip" if denormalised \
                 else f"{OUTPUT_DIR}/{bionetwork}_tier1.zip"
    make_zipfile(tier1_files, output_filename)

if __name__ == '__main__':
    args = define_parser().parse_args()
    main(args.csv, args.bionetwork, args.group_field, args.denormalised)