import argparse
import os
import re

import requests
from dateutil.parser import date_parse

import pandas as pd
import numpy as np

from src.dcp_to_tier1_mapping import (
    DCP_TIER1_MAP, TIER1, HSAP_AGE_TO_DEV_DICT, 
    GOLDEN_SPREADSHEET, COLLECTION_DICT
)
from src.flatten_dcp import explode_csv_col

OUTPUT_DIR = 'data/tier1_output'


def define_parser():
    '''Defines and returns the argument parser.'''
    parser = argparse.ArgumentParser(description='Parser for the arguments')
    parser.add_argument('--flat_path', '-s', action='store',
                        dest='flat_path', type=str, required=True, help='flat dcp spreadsheet path')
    parser.add_argument("-o", "--output_dir", action="store", default='data/tier1_output',
                    dest="output_dir", type=str, required=False, help="directory to output tier1 spreadsheet")
    return parser

def get_ols_id(term, ontology):
    request_query = 'https://www.ebi.ac.uk/ols4/api/search?q='
    if term is np.nan:
        return term
    response = requests.get(request_query + f"{term.replace(' ', '+')}&ontology={ontology}", timeout=10).json()
    if response["response"]["numFound"] == 0:
        print(f"No ontology found for {term} in {ontology}")
        return term
    return response["response"]["docs"][0]['obo_id']

def get_ols_label(ontology_id, only_label=True, ontology=None):
    if ontology_id is np.nan or not re.match(r"\w+:\d+", ontology_id):
        return ontology_id
    ontology_name = ontology if ontology else ontology_id.split(":")[0].lower()
    ontology_term = ontology_id.replace(":", "_")
    url = f'https://www.ebi.ac.uk/ols4/api/ontologies/{ontology_name}/terms/http%253A%252F%252Fpurl.obolibrary.org%252Fobo%252F{ontology_term}'
    if ontology_name == 'efo':
        url = f'https://www.ebi.ac.uk/ols4/api/ontologies/{ontology_name}/terms/http%253A%252F%252Fwww.ebi.ac.uk%252Fefo%252F{ontology_term}'
    try:
        response = requests.get(url, timeout=10)
        results = response.json()
    except ConnectionError as e:
        print(e)
        return ontology_id
    return results['label'] if only_label else results

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
    return explode_csv_col(dcp_df, column='sample_id', sep='\|\|').reset_index(drop=True)

def get_sex_id(term):
    if term in ['mixed', 'unknown']:
        return 'unknown'
    return get_ols_id(term, 'pato')

def edit_sex(dcp_df):
    sex_dict = {sex: get_sex_id(sex) for sex in dcp_df['donor_organism.sex'].unique()}
    dcp_df['sex_ontology_term_id'] = dcp_df['donor_organism.sex'].replace(sex_dict)
    dcp_df['sex_ontology_term'] = dcp_df['donor_organism.sex'].replace({'mixed': 'unknown'})
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

def age_to_dev(age, age_unit, age_to_dev_dict):
    # TODO add a way to record the following options
    # Embryonic stage = A term from the set of Carnegie stages 1-23 = (up to 8 weeks after conception; e.g. HsapDv:0000003)
    # Fetal development = A term from the set of 9 to 38 week post-fertilization human stages = (9 weeks after conception and before birth; e.g. HsapDv:0000046)
    if not age:
        return None
    age = convert_to_years(age, age_unit)
    if isinstance(age, str) and '-' in age:
        age = [float(age) for age in age.split('-')]
        for age_range, label in age_to_dev_dict.items():
            if age_range[0] <= age[0] <= age_range[1] and \
                    age_range[0] <= age[1] <= age_range[1]:
                return age_range
            print(f"Given range {age} overlaps the acceptable ranges. Will use 'developmental stage' instead.")
            return None
    if isinstance(age, (int, float, str)) and (age.isdigit() or age.replace('.', '', 1).isdigit()):
        age = float(age) if isinstance(age, str) else age
        for age_range, label in age_to_dev_dict.items():
            if age_range[0] <= age <= age_range[1]:
                return age_range
    # print(f"Age {age} could not be mapped to accepted ranges {['-'.join(map(str, age)) for age in age_to_dev_dict.keys()]}")
    return None

def dev_stage_helper(row):
    if 'donor_organism.organism_age' in row and row['donor_organism.biomaterial_core.ncbi_taxon_id'] == '9606':
        dev_stage = age_to_dev(age=row['donor_organism.organism_age'],
                               age_unit=row['donor_organism.organism_age_unit.ontology_label'],
                               age_to_dev_dict=HSAP_AGE_TO_DEV_DICT)
        if dev_stage:
            return dev_stage
    return None

def edit_developement_stage(dcp_df):
    dev_age_stage = dcp_df.apply(dev_stage_helper, axis=1)
    dcp_df['age_range'] = dev_age_stage.apply(lambda x: '-'.join(map(str, x)) if x else np.nan)
    dcp_df['development_stage_ontology_term_id'] = dev_age_stage.apply(lambda x: HSAP_AGE_TO_DEV_DICT[x] if x in HSAP_AGE_TO_DEV_DICT else None)
    dcp_df.fillna({'development_stage_ontology_term_id': dcp_df['donor_organism.development_stage.ontology']}, inplace=True)
    dev_dict = {dev: get_ols_label(dev) for dev in dcp_df['development_stage_ontology_term_id'].unique() if dev != 'unknown'}
    dcp_df['development_stage_ontology_term'] = dcp_df['development_stage_ontology_term_id'].replace(dev_dict)
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
    software = 'analysis_protocol.alignment_software'
    version = 'analysis_protocol.alignment_software_version'
    if software not in dcp_df:
        print('No alignment software provided')
        return dcp_df
    if version not in dcp_df:
        dcp_df['analysis_software'] = dcp_df[software]
    else:
        dcp_df['alignment_software'] = dcp_df[[software, version]].apply(lambda x: " ".join(x.astype(str)), axis=1)
    return dcp_df

def edit_reference_genome(dcp_df):
    if 'analysis_file.genome_assembly_version' not in dcp_df:
        print('No genome assembly version provided')
        return dcp_df
    dcp_df['reference_genome'] = dcp_df['analysis_file.genome_assembly_version'].dropna()\
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

def edit_collection_method(dcp_df):
    if 'collection_protocol.method.ontology_label' in dcp_df:
        dcp_df['sample_collection_method'] = dcp_df['collection_protocol.method.ontology_label'].replace(COLLECTION_DICT)
    return dcp_df

def tissue_helper(row, ontology=False):
    field = 'ontology' if ontology else 'ontology_label'
    if f'specimen_from_organism.organ_parts.{field}' in row:
        return row[f'specimen_from_organism.organ_parts.{field}']
    if f'specimen_from_organism.organ.{field}' in row:
        return row[f'specimen_from_organism.organ.{field}']
    return None

def edit_tissue(dcp_df):
    dcp_df['tissue_ontology_term'] = dcp_df.apply(tissue_helper, axis=1)
    dcp_df['tissue_ontology_term_id'] = dcp_df.apply(tissue_helper, axis=1, ontology=True)
    return dcp_df

def tissue_free_text_helper(row):
    organ_parts = 'specimen_from_organism.organ_parts'
    organ = 'specimen_from_organism.organ'
    if f'{organ_parts}.text' in row and \
        row[f'{organ_parts}.text'] is not np.nan and \
        row[f'{organ_parts}.text'].lower() != row[f'{organ_parts}.ontology_label'].lower():
        return row[f'{organ_parts}.text']
    if f'{organ}.text' in row and row[f'{organ}.text'].lower() != row[f'{organ}.ontology_label'].lower():
        return row[f'{organ}.text']
    return None

def edit_tissue_free_text(dcp_df):
    dcp_df['tissue_free_text'] = dcp_df.apply(tissue_free_text_helper, axis=1)
    return dcp_df

def edit_diseases(dcp_df):
    # if we have multiple diseases, we would need to select one. by default select the first and print what was not selected
    if 'donor_organism.diseases.ontology_label' in dcp_df:
        unique_diseases = dcp_df['donor_organism.diseases.ontology_label'].str.split("\\|\\|", expand=True, n=1).drop_duplicates().dropna()
        if unique_diseases.shape[1] > 1:
            selected_disease = ", ".join(np.unique(unique_diseases[0]))
            unselected_diseases = " and ".join(unique_diseases[1])
            print(f"From multiple diseases, we will use {selected_disease}, instead of {unselected_diseases}")
        dcp_df['disease_ontology_term_id'] = dcp_df['donor_organism.diseases.ontology'].str.split("\\|\\|").str[0]
        dcp_df['disease_ontology_term'] = dcp_df['donor_organism.diseases.ontology_label'].str.split("\\|\\|").str[0]
    return dcp_df

def edit_sampled_site_condition(dcp_df):
    """Diseased donor and healthy specimen does not mean adjacent every time. 
    i.e. if donor has lung cancer the heart specimen will not be adjacent
    This needs to be inspected manually
    """
    if 'donor_organism.diseases.ontology_label' in dcp_df.keys() and 'specimen_from_organism.diseases.ontology_label' in dcp_df.keys():
        dcp_df['sampled_site_condition'] = None
        dcp_df.loc[(dcp_df['donor_organism.diseases.ontology_label'] == 'normal') & \
                    (dcp_df['specimen_from_organism.diseases.ontology_label'] == 'normal'), 'sampled_site_condition'] = 'healthy'
        dcp_df.loc[(dcp_df['donor_organism.diseases.ontology_label'] != 'normal') & \
                    (dcp_df['specimen_from_organism.diseases.ontology_label'] == 'normal'), 'sampled_site_condition'] = 'adjacent'
        dcp_df.loc[(dcp_df['specimen_from_organism.diseases.ontology_label'] != 'normal'), 'sampled_site_condition'] = 'diseased'
        
        if any(dcp_df['sampled_site_condition'] == 'adjacent'):
            print("Found diseases in donor but with healthy specimen.",
                "Please investigate if diseases of donor could apply in specimen,",
                "in order to define healthy or adjacent sampled_site_condition.")
            print(dcp_df.loc[dcp_df['sampled_site_condition'] == 'adjacent', \
                                ['sampled_site_condition', 'donor_organism.diseases.ontology_label', \
                                 'specimen_from_organism.diseases.ontology_label', 'specimen_from_organism.organ.text']])
    return dcp_df

def manner_of_death_helper(row):
    if 'donor_organism.death.hardy_scale' in row and not np.isnan(float(row['donor_organism.death.hardy_scale'])):
        return row['donor_organism.death.hardy_scale']
    if row['donor_organism.is_living'] == 'yes':
        return 'not applicable'
    return 'unknown'

def edit_manner_of_death(dcp_df):
    dcp_df['manner_of_death'] = dcp_df.apply(manner_of_death_helper, axis=1)
    return dcp_df

def edit_sequenced_fragment(dcp_df):
    seq_frag = {
        '3 prime tag': '3 prime tag',
        '3 prime end bias': '3 prime tag',
        '5 prime tag': '5 prime tag',
        '5 prime end bias': '5 prime tag',
        'full length': 'full length'
        # no dcp option for 'probe-based' "sequencing"
    }
    dcp_df['sequenced_fragment'] = dcp_df['library_preparation_protocol.end_bias'].replace(seq_frag)
    return dcp_df

def edit_consortia(dcp_df):
    dcp_df['consortia'] = 'HCA'
    return dcp_df

def get_uns(dcp_df:pd.DataFrame)->pd.DataFrame:
    return pd.DataFrame({
        'title': dcp_df['project.project_core.project_title'].unique(), 
        'study_pi': dcp_df['project.contributors.name'].unique() if 'project.contributors.name' in dcp_df else None,
        'contact_email': dcp_df['project.contributors.email'].unique() if 'project.contributors.email' in dcp_df else None,
        'consortia': ['HCA'],
        'publication_doi': dcp_df['project.publications.doi'].unique() if 'project.publications.doi' in dcp_df else None
        })

def rename_cols(dcp_df:pd.DataFrame, map_dict:dict)->pd.DataFrame:
    dcp_df = dcp_df.rename(columns=map_dict)
    return dcp_df

def select_cols(dcp_df:pd.DataFrame, cols:list)->pd.DataFrame:
    na_cols = [col for col in cols if col not in dcp_df]
    dcp_df[na_cols] = np.nan
    return dcp_df[cols].drop_duplicates()

def main(flat_path:str, output_dir:str):
    filename = os.path.basename(flat_path)
    dcp_spreadsheet = pd.read_csv(flat_path, dtype=str)
    
    dcp_spreadsheet = edit_sample_source(dcp_spreadsheet)
    dcp_spreadsheet = edit_tissue_type(dcp_spreadsheet)
    dcp_spreadsheet = edit_sex(dcp_spreadsheet)
    dcp_spreadsheet = edit_developement_stage(dcp_spreadsheet)
    dcp_spreadsheet = edit_suspension_type(dcp_spreadsheet)
    dcp_spreadsheet = edit_alignment_software(dcp_spreadsheet)
    dcp_spreadsheet = edit_reference_genome(dcp_spreadsheet)
    dcp_spreadsheet = edit_collection_year(dcp_spreadsheet)
    dcp_spreadsheet = edit_collection_method(dcp_spreadsheet)
    dcp_spreadsheet = edit_tissue(dcp_spreadsheet)
    dcp_spreadsheet = edit_tissue_free_text(dcp_spreadsheet)
    dcp_spreadsheet = edit_diseases(dcp_spreadsheet)
    dcp_spreadsheet = edit_sampled_site_condition(dcp_spreadsheet)
    dcp_spreadsheet = edit_manner_of_death(dcp_spreadsheet)
    dcp_spreadsheet = edit_sequenced_fragment(dcp_spreadsheet)
    dcp_spreadsheet = edit_consortia(dcp_spreadsheet)
    dcp_spreadsheet = merge_sample_ids(dcp_spreadsheet)

    dcp_spreadsheet = rename_cols(dcp_spreadsheet, map_dict=DCP_TIER1_MAP)

    obs = select_cols(dcp_spreadsheet, cols=TIER1['obs'])
    obs.to_csv(os.path.join(output_dir, f"{filename.replace('.csv', '_tier1.csv')}"), index=False)

    output_path = os.path.join(output_dir, f"{filename.replace('.csv', '_tier1.xlsx')}")
    with pd.ExcelWriter(output_path) as writer:
        for tab, fields in GOLDEN_SPREADSHEET.items():
            select_cols(dcp_spreadsheet, cols=fields).to_excel(writer, sheet_name=tab, index=True, header=True)


if __name__ == "__main__":
    args = define_parser().parse_args()

    main(flat_path=args.flat_path, output_dir=OUTPUT_DIR)
