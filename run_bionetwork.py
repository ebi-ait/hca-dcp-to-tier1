import os
from os.path import basename, splitext
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
    parser.add_argument('--format', '-f', action='store', dest='output_format', type=str,
                        required=False, default='both', help='Output format (csv, xlsx, both)')
    return parser

def make_zipfile(input_filenames:list, output_filename:str, filename_mapping:dict=None):
    with zipfile.ZipFile(output_filename, "w") as zip_file:
        for filename in input_filenames:
            arcname = filename_mapping.get(filename, os.path.basename(filename)) if filename_mapping else os.path.basename(filename)
            zip_file.write(filename, arcname=arcname)
    print(f"Zip file created at {output_filename}")

def select_zip_files(xlsx_files, denormalised, output_format):
    selected_files = []
    formats = ['csv', 'xlsx'] if output_format == "both" else [output_format]
    extensions = [f'_denormalised_tier1.{format}' if denormalised else f'_tier1.{format}' for format in formats]
    for extension in extensions:
        for xlsx_file in xlsx_files:
            output_file = f"{OUTPUT_DIR}/{xlsx_file.replace('.xlsx', extension)}"
            if os.path.exists(output_file):
                selected_files.append(output_file)
            else:
                print(f"File {output_file} not found!")
    return selected_files

def orig_filename(output_filename):
    return basename(output_filename.replace('_denormalised', '').replace('_tier1', '').replace('.csv', '.xlsx'))

def main(csv, bionetwork, group_field, denormalised, output_format):
    df = pd.read_csv(csv)
    xlsx_files = df.loc[df['bionetwork'] == bionetwork.lower(), 'spreadsheet'].tolist()
    for xlsx_file in xlsx_files:
        if xlsx_file not in os.listdir(INPUT_DIR):
            print(f"File {xlsx_file} not found in {INPUT_DIR}")
            continue
        print(f"=====Processing {xlsx_file}=====")
        dcp_to_tier1(os.path.join(INPUT_DIR, xlsx_file), FLAT_DIR, OUTPUT_DIR, group_field, denormalised)
    
    selected_files = select_zip_files(xlsx_files, denormalised, output_format)
    
    study_dict = df[['spreadsheet','source_study']].set_index('spreadsheet').to_dict()['source_study']
    files_mapping = {file: f"{study_dict.get(orig_filename(file), '')}{splitext(file)[1]}" for file in selected_files}
    
    denorm_fnm = "_denormalised" if denormalised else ""
    format_fnm = f"_{output_format}" if output_format != 'both' else ""

    output_filename = f"{OUTPUT_DIR}/{bionetwork}{denorm_fnm}{format_fnm}_tier1.zip"
    make_zipfile(selected_files, output_filename, files_mapping)

if __name__ == '__main__':
    args = define_parser().parse_args()
    main(args.csv, args.bionetwork, args.group_field, args.denormalised, args.output_format)