import argparse

import requests
import pandas as pd

from dcp_to_tier1_mapping import dcp_to_tier1_mapping, tier1, age_to_dev_dict


def define_parser():
    '''Defines and returns the argument parser.'''
    parser = argparse.ArgumentParser(description='Parser for the arguments')
    parser.add_argument('--flat_filename', '-f', action='store',
                        dest='flat_filename', type=str, required=True, help='flat dcp spreadsheet filename')
    parser.add_argument('--input_dir', '-i', action='store', default='denormalised_spreadsheet',
                        dest='input_dir', type=str, required=False, help='directory of the flat dcp spreadsheet file')
    parser.add_argument('--output_dir', '-o', action='store', default='tier1_output',
                        dest='output_dir', type=str, required=False, help='directory for the tier1 spreadsheet output')
    return parser

def get_ols_id(term, ontology):
    request_query = 'https://www.ebi.ac.uk/ols4/api/search?q='
    response = requests.get(request_query + f"{term.replace(' ', '+')}&ontology={ontology}", timeout=10).json()
    if response["response"]["numFound"] == 0:
        print(f"No ontology found for {term} in {ontology}")
        return term
    return response["response"]["docs"][0]['obo_id']

def edit_sample_source(dcp_df:pd.DataFrame):
    if 'donor_organism.is_living' not in dcp_df:
        return dcp_df
    # fill living with surgical and deceaced with post-mortem, and if there is transplant donor information overwrite
    dcp_df.loc[(dcp_df['donor_organism.is_living'] == 'yes'), 'sample_source'] = 'surgical donor'
    dcp_df.loc[(dcp_df['donor_organism.is_living'] == 'no'), 'sample_source'] = 'postmortem donor'
    
    if  'specimen_from_organism.transplant_organ' in dcp_df.keys():
        dcp_df.loc[(dcp_df['specimen_from_organism.transplant_organ'] == 'yes'), 'sample_source'] = 'organ donor'
    return dcp_df

def library_to_tissue_type(row):
    """
    Add tissue type for each row, based on presence of organoid, cell line or specimen ID in row. 
    Organoid might go from specimen to cell line to organoid, therefore it allows all values to be present,
    cell line will have to be derived by specimen, but it's extreme rare to be derived by organoid
    specimen cannot have any other type of tissues present
    """
    tissue_type_dict = {
        'organoid.biomaterial_core.biomaterial_id': 'organoid',
        'cell_line.biomaterial_core.biomaterial_id': 'cell culture',
        'specimen_from_organism.biomaterial_core.biomaterial_id': 'tissue'
    }
    tissue_type_dcp = [
        'organoid.biomaterial_core.biomaterial_id',
        'cell_line.biomaterial_core.biomaterial_id', 
        'specimen_from_organism.biomaterial_core.biomaterial_id'
        ]
    row = row.dropna()
    for dcp_type in tissue_type_dcp:
        if dcp_type in row.index:
            return tissue_type_dict[dcp_type]
    print(f"No tissue type found for {row['cell_suspension.biomaterial_core.biomaterial_id']}. Will add 'tissue'.")
    return 'tissue'

def edit_tissue_type(dcp_df):
    dcp_df['tissue_type'] = dcp_df.apply(library_to_tissue_type, axis=1)
    return dcp_df

def merge_sample_ids(dcp_df):
    """
    Sample IDs could be derived from organoid, cell line or specimen. 
    Here we merge those samples, to use the most recent one before lib prep
    """
    tissue_type_dcp = [
        'organoid.biomaterial_core.biomaterial_id',
        'cell_line.biomaterial_core.biomaterial_id', 
        'specimen_from_organism.biomaterial_core.biomaterial_id'
        ]
    merge_cols = [col for col in tissue_type_dcp if col in dcp_df]
    dcp_df['sample_id'] = dcp_df[merge_cols].bfill(axis=1)[merge_cols[0]]
    return dcp_df

def get_sex_id(term):
    if term in ['mixed', 'unknown']:
        return 'unknown'
    return get_ols_id(term, 'pato')

def edit_sex(dcp_df):
    sex_dict = {sex: get_sex_id(sex) for sex in dcp_df['donor_organism.sex'].unique()}
    dcp_df['sex_ontology_term_id'] = dcp_df['donor_organism.sex'].replace(sex_dict)
    return dcp_df

def get_uns(dcp_df:pd.DataFrame)->pd.DataFrame:
    return pd.DataFrame({
        'title': dcp_df['project.project_core.project_title'].unique(), 
        'study_pi': dcp_df['project.contributors.name'].unique() if 'project.contributors.name' in dcp_df else None,
        'contact_email': dcp_df['project.contributors.email'].unique() if 'project.contributors.email' in dcp_df else None,
        'consortia': ['HCA'],
        'publication_doi': dcp_df['project.publications.doi'].unique() if 'project.publications.doi' in dcp_df else None
        })

def get_obs(dcp_df:pd.DataFrame):
    return dcp_df.rename(columns=dcp_to_tier1_mapping)\
        .drop(columns=[col for col in dcp_df if col not in tier1['obs']])

def main(flat_filename:str, input_dir:str, output_dir:str):
    dcp_spreadsheet_filename = f'{input_dir}/{flat_filename}'
    dcp_spreadsheet = pd.read_csv(dcp_spreadsheet_filename, dtype=str)
    
    dcp_spreadsheet = edit_sample_source(dcp_spreadsheet)
    dcp_spreadsheet = edit_tissue_type(dcp_spreadsheet)
    dcp_spreadsheet = edit_sex(dcp_spreadsheet)
    dcp_spreadsheet = merge_sample_ids(dcp_spreadsheet)

    uns = get_uns(dcp_spreadsheet)
    obs = get_obs(dcp_spreadsheet)
    
    uns.to_csv(f"{output_dir}/{flat_filename.replace(r'(denormalised)|(bysample).csv', 'uns.csv')}")
    obs.to_csv(f"{output_dir}/{flat_filename.replace('denormalised.csv', 'obs.csv')}")

if __name__ == "__main__":
    args = define_parser().parse_args()

    main(flat_filename=args.flat_filename, input_dir=args.input_dir, output_dir=args.output_dir)
