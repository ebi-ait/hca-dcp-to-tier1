import argparse

import requests
from dateutil.parser import date_parse
import pandas as pd
import numpy as np

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

def convert_to_years(age, age_unit):
    if age_unit == 'year':
        return age
    if isinstance(age, str) and '-' in age:
        if age_unit == 'year':
            return age
        print("Can't convert range to years")
        return age
    age_to_years = {
        'year': 1,
        'month': 12,
        'day': 365
    }
    try:
        return round(int(age) / age_to_years[age_unit], 2)
    except ValueError:
        print("Age " + str(age) + " is not a number")

def hs_age_to_dev(age, age_unit, age_to_dev_dict=age_to_dev_dict):
    # TODO add a way to record the following options
    # Embryonic stage = A term from the set of Carnegie stages 1-23 = (up to 8 weeks after conception; e.g. HsapDv:0000003)
    # Fetal development = A term from the set of 9 to 38 week post-fertilization human stages = (9 weeks after conception and before birth; e.g. HsapDv:0000046)
    if not age:
        return None
    age = convert_to_years(age, age_unit)
    if isinstance(age, str) and '-' in age:
        age = [int(age) for age in age.split('-')]
        for age_range, label in age_to_dev_dict.items():
            if age_range[0] <= age[0] <= age_range[1] and \
                    age_range[0] <= age[1] <= age_range[1]:
                return label
            if age_range[0] <= np.mean(age) <= age_range[1]:
                print(f"Given range {age} overlaps the acceptable ranges. Will use 'unknown'")
                return 'unknown'
    if isinstance(age, (int, float, str)) and age.isdigit():
        age = float(age) if isinstance(age, str) else age
        for age_range, label in age_to_dev_dict.items():
            if age_range[0] <= age <= age_range[1]:
                return label
    print(f"Age {age} could not be mapped to accepted ranges {['-'.join(map(str, age)) for age in age_to_dev_dict.keys()]}")
    return None

def dev_stage_helper(row):
    if 'donor_organism.organism_age' in row and row['donor_organism.biomaterial_core.ncbi_taxon_id'] == '9606':
        dev_stage = hs_age_to_dev(row['donor_organism.organism_age'], row['donor_organism.organism_age_unit.ontology_label'])
        if dev_stage:
            return dev_stage
    return row['donor_organism.development_stage.ontology']

def edit_developement_stage(dcp_df):
    dcp_df['development_stage_ontology_term_id'] = dcp_df.apply(dev_stage_helper, axis=1)
    return dcp_df

def edit_suspension_type(dcp_df):
    suspension_type_dict = {
        'single cell': 'cell',
        'single nucleus': 'nucleus',
        'bulk cell': 'na',
        'bulk nuclei': 'na'
    }
    dcp_df['suspension_type'] = dcp_df['library_preparation_protocol.nucleic_acid_source'].replace(suspension_type_dict)
    return dcp_df

def edit_alignment_software(dcp_df):
    if 'analysis_protocol.alignment_software' not in dcp_df:
        print('No alignment software provided')
        return dcp_df
    if 'analysis_protocol.alignment_software_version' not in dcp_df:
        dcp_df['analysis_software'] = dcp_df['analysis_protocol.alignment_software']
    else:
        dcp_df['alignment_software'] = f"{dcp_df['analysis_protocol.alignment_software']} {dcp_df['analysis_protocol.alignment_software_version'].astype(str)}"
    return dcp_df

def edit_reference_genome(dcp_df):
    dcp_df['reference_genome'] = dcp_df['analysis_file.genome_assembly_version']\
        .apply(lambda x: x if x == "Not Applicable" else (
            x.replace('||Not Applicable||', '||')
            .replace('||Not Applicable', '')
            .replace('Not Applicable||', '')
            .replace('Not Applicable', '')
            ))
    return dcp_df

def parse_year(date_value):
    try:
        if isinstance(date_value, str):
            return date_parse(date_value, fuzzy=True).year
        if isinstance(date_value, (int, float)):
            return date_parse(str(int(date_value)), fuzzy=True).year
    except (ValueError, TypeError):
        return pd.NA
    return pd.NA

def edit_collection_year(dcp_df):
    if 'specimen_from_organism.collection_time' in dcp_df:
        dcp_df['collection_year'] = dcp_df['specimen_from_organism.collection_time'].apply(parse_year)
    return dcp_df

def tissue_free_text_helper(row):
    if 'specimen_from_organism.organ_parts.text' in row:
        row['tissue_free_text'] = row['specimen_from_organism.organ_parts.text']
    return row

def edit_tissue_free_text(dcp_df):
    return dcp_df.apply(tissue_free_text_helper, axis=1)

def edit_diseases(dcp_df):
    # if we have multiple diseases, we would need to select one. by default select the first and print what was not selected
    if 'donor_organism.diseases.ontology' in dcp_df:
        unique_diseases = dcp_df['donor_organism.diseases.ontology'].str.split("\\|\\|", expand=True, n=1).drop_duplicates().dropna()
        if unique_diseases.shape[1] > 1:
            selected_disease = ", ".join(np.unique(unique_diseases[0]))
            unselected_diseases = " and ".join(unique_diseases[1])
            print(f"From multiple diseases, we will use {selected_disease}, instead of {unselected_diseases}")
        dcp_df['disease_ontology_term_id'] = dcp_df['donor_organism.diseases.ontology'].str.split("\\|\\|").str[0]
    return dcp_df

def get_uns(dcp_df:pd.DataFrame)->pd.DataFrame:
    return pd.DataFrame({
        'title': dcp_df['project.project_core.project_title'].unique(), 
        'study_pi': dcp_df['project.contributors.name'].unique() if 'project.contributors.name' in dcp_df else None,
        'contact_email': dcp_df['project.contributors.email'].unique() if 'project.contributors.email' in dcp_df else None,
        'consortia': ['HCA'],
        'publication_doi': dcp_df['project.publications.doi'].unique() if 'project.publications.doi' in dcp_df else None
        })

def get_obs(dcp_df:pd.DataFrame, tier1=tier1):
    dcp_df = dcp_df.rename(columns=dcp_to_tier1_mapping)
    drop_cols = [col for col in dcp_df if col not in tier1['obs']]
    return dcp_df.drop(columns=drop_cols)

def main(flat_filename:str, input_dir:str, output_dir:str):
    dcp_spreadsheet_filename = f'{input_dir}/{flat_filename}'
    dcp_spreadsheet = pd.read_csv(dcp_spreadsheet_filename, dtype=str)
    
    dcp_spreadsheet = edit_sample_source(dcp_spreadsheet)
    dcp_spreadsheet = edit_tissue_type(dcp_spreadsheet)
    dcp_spreadsheet = edit_sex(dcp_spreadsheet)
    dcp_spreadsheet = merge_sample_ids(dcp_spreadsheet)
    dcp_spreadsheet = edit_developement_stage(dcp_spreadsheet)
    dcp_spreadsheet = edit_suspension_type(dcp_spreadsheet)
    dcp_spreadsheet = edit_alignment_software(dcp_spreadsheet)
    dcp_spreadsheet = edit_reference_genome(dcp_spreadsheet)
    dcp_spreadsheet = edit_collection_year(dcp_spreadsheet)
    dcp_spreadsheet = edit_tissue_free_text(dcp_spreadsheet)
    dcp_spreadsheet = edit_diseases(dcp_spreadsheet)

    uns = get_uns(dcp_spreadsheet)
    obs = get_obs(dcp_spreadsheet)
    
    uns.to_csv(f"{output_dir}/{flat_filename.replace(r'(denormalised)|(bysample).csv', 'uns.csv')}")
    obs.to_csv(f"{output_dir}/{flat_filename.replace(r'(denormalised)|(bysample).csv', 'obs.csv')}")

if __name__ == "__main__":
    args = define_parser().parse_args()

    main(flat_filename=args.flat_filename, input_dir=args.input_dir, output_dir=args.output_dir)
