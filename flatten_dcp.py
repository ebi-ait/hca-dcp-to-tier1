## Init notebook by Amnon Khen
## https://github.com/ebi-ait/hca-ebi-dev-team/blob/master/scripts/metadata-spreadsheet-by-file/HCA%20Project%20Metadata%20Spreadsheet.ipynb

import argparse
from os.path import basename, splitext

from datetime import datetime
from functools import partial, reduce
from dataclasses import dataclass
from shutil import copy

import pandas as pd


SEP='\\|\\|'
FIRST_DATA_LINE=4


def define_parser():
    """Defines and returns the argument parser."""
    parser = argparse.ArgumentParser(description="Parser for the arguments")
    parser.add_argument("--spreadsheet_filename", "-s", action="store",
                        dest="spreadsheet_filename", type=str, required=True, help="dcp spreadsheet filename")
    parser.add_argument("--input_dir", "-i", action="store", default='dcp_spreadsheet',
                        dest="input_dir", type=str, required=False, help="directory of the dcp spreadsheet file")
    parser.add_argument("--output_dir", "-o", action="store", default='denormalised_spreadsheet',
                        dest="output_dir", type=str, required=False, help="directory for the denormalised spreadsheet output")
    return parser

@dataclass
class SequencingProtocol:
    SEQUENCING_PROTOCOL_ID_Required: str

@dataclass
class LibraryPreparationProtocol:
    LIBRARY_PREPARATION_PROTOCOL_ID: str

@dataclass
class DissociationProtocol:
    DISSOCIATION_PROTOCOL_ID:str

@dataclass
class CollectionProtocol:
    COLLECTION_PROTOCOL_ID:str

@dataclass
class AnalysisProtocol:
    ANALYSIS_PROTOCOL_ID:str

@dataclass
class DifferentiationProtocol:
    DIFFERENTIATION_PROTOCOL_ID:str

@dataclass
class DonorOrganism:
    DONOR_ORGANISM_ID:str 

@dataclass
class SpecimenFromOrganism:
    SPECIMEN_FROM_ORGANISM_ID:str
    COLLECTION_PROTOCOL_ID:CollectionProtocol
    INPUT_DONOR_ORGANISM_ID:DonorOrganism

@dataclass
class EnrichmentProtocol:
    ENRICHMENT_PROTOCOL_ID:str

@dataclass
class CellLine:
    CELL_LINE_ID: str
    ENRICHMENT_PROTOCOL_ID:EnrichmentProtocol
    DISSOCIATION_PROTOCOL_ID:DissociationProtocol
    INPUT_SPECIMEN_FROM_ORGANISM_ID:SpecimenFromOrganism

@dataclass
class Organoid:
    ORGANOID_ID: str
    INPUT_CELL_LINE_ID:CellLine
    INPUT_SPECIMEN_FROM_ORGANISM_ID:SpecimenFromOrganism
    DIFFERENTIATION_PROTOCOL_ID:DifferentiationProtocol

@dataclass
class CellSuspension:
    CELL_SUSPENSION_ID: str
    ENRICHMENT_PROTOCOL_ID:EnrichmentProtocol
    INPUT_SPECIMEN_FROM_ORGANISM_ID:SpecimenFromOrganism
    DISSOCIATION_PROTOCOL_ID:DissociationProtocol
    INPUT_SPECIMEN_FROM_ORGANISM_ID:SpecimenFromOrganism
    INPUT_ORGANOID_ID:Organoid
    INPUT_CELL_LINE_ID:CellLine

@dataclass
class SequenceFile:
    SEQUENCING_PROTOCOL_ID_Required: SequencingProtocol
    LIBRARY_PREPARATION_PROTOCOL_ID_Required: LibraryPreparationProtocol
    INPUT_CELL_SUSPENSION_ID_Required: CellSuspension

@dataclass
class ImagingPreparationProtocol:
    IMAGING_PREPARATION_PROTOCOL_ID:str

@dataclass
class ImagedSpecimen:
    IMAGED_SPECIMEN_ID_Required:str
    INPUT_SPECIMEN_FROM_ORGANISM_ID_Required:SpecimenFromOrganism
    IMAGING_PREPARATION_PROTOCOL_ID_Required:ImagingPreparationProtocol

@dataclass
class AnalysisFile:
    ANALYSIS_PROTOCOL_ID_Required: AnalysisProtocol
    IMAGED_SPECIMEN_ID_Required:ImagedSpecimen
    CELL_SUSPENSION_ID_Required:CellSuspension
    LIBRARY_PREPARATION_PROTOCOL_ID_Required:LibraryPreparationProtocol
    SEQUENCING_PROTOCOL_ID_Required:SequencingProtocol

@dataclass
class ImagingProtocol:
    IMAGING_PROTOCOL_ID:str

@dataclass
class ImageFile:
    INPUT_IMAGED_SPECIMEN_ID:ImagedSpecimen
    IMAGING_PROTOCOL_ID:ImagingProtocol

@dataclass
class Link:
    source:str
    target:str
    source_field:str
    target_field:str = None
    join_type:str = 'left'
    
    
    def __post_init__(self):
        if self.target_field is None:
            self.target_field = self.source_field
        else:
            print(f'{self.source}->{self.target} using fields {self.source_field}->{self.target_field}')


# TODO: links list is assumed to be topologically sorted, in the future - sort
links_all = [
    Link('Image file', 'Imaged specimen', 'INPUT IMAGED SPECIMEN ID (Required)', 'IMAGED SPECIMEN ID (Required)'),
    Link('Image file', 'Imaging protocol', 'IMAGING PROTOCOL ID (Required)'),
    
    Link('Sequence file', 'Sequencing protocol', 'SEQUENCING PROTOCOL ID (Required)'),
    Link('Sequence file', 'Library preparation protocol', 'LIBRARY PREPARATION PROTOCOL ID (Required)'),
    Link('Sequence file', 'Cell suspension', 'INPUT CELL SUSPENSION ID (Required)','CELL SUSPENSION ID (Required)'),
    Link('Sequence file', 'Imaged specimen', 'INPUT IMAGED SPECIMEN ID (Required)', 'IMAGED SPECIMEN ID (Required)'),
    
    Link('Analysis file', 'Analysis protocol', 'ANALYSIS PROTOCOL ID (Required)', 'ANALYSIS PROTOCOL ID'),
    Link('Analysis file', 'Cell suspension', 'CELL SUSPENSION ID (Required)'),
    Link('Analysis file', 'Library preparation protocol', 'LIBRARY PREPARATION PROTOCOL ID (Required)'),
    Link('Analysis file', 'Sequencing protocol', 'SEQUENCING PROTOCOL ID (Required)'),
    Link('Analysis file', 'Imaged specimen', 'INPUT IMAGED SPECIMEN ID (Required)', 'IMAGED SPECIMEN ID (Required)'),
    
    Link('Cell suspension', 'Organoid','INPUT ORGANOID ID (Required)','ORGANOID ID (Required)'),
    Link('Cell suspension', 'Cell line','INPUT CELL LINE ID (Required)','CELL LINE ID (Required)'),
    Link('Cell suspension', 'Specimen from organism','INPUT SPECIMEN FROM ORGANISM ID (Required)','SPECIMEN FROM ORGANISM ID (Required)'),
    Link('Cell suspension', 'Enrichment protocol','ENRICHMENT PROTOCOL ID (Required)'),
    Link('Cell suspension', 'Dissociation protocol','DISSOCIATION PROTOCOL ID (Required)'),
    
    Link('Organoid', 'Cell line','INPUT CELL LINE ID (Required)','CELL LINE ID (Required)'),
    Link('Organoid', 'Differentiation protocol','DIFFERENTIATION PROTOCOL ID (Required)'),
    Link('Organoid', 'Dissociation protocol','DISSOCIATION PROTOCOL ID (Required)'),
    Link('Organoid', 'Specimen from organism','INPUT SPECIMEN FROM ORGANISM ID (Required)','SPECIMEN FROM ORGANISM ID (Required)'),
    
    Link('Cell line', 'Specimen from organism','INPUT SPECIMEN FROM ORGANISM ID (Required)','SPECIMEN FROM ORGANISM ID (Required)'),
    Link('Cell line', 'Enrichment protocol','ENRICHMENT PROTOCOL ID (Required)'),
    Link('Cell line', 'Dissociation protocol','DISSOCIATION PROTOCOL ID (Required)'),
    
    Link('Imaged specimen', 'Analysis file', 'IMAGED SPECIMEN ID (Required)'),
    Link('Imaged specimen', 'Specimen from organism','INPUT SPECIMEN FROM ORGANISM ID (Required)','SPECIMEN FROM ORGANISM ID (Required)'),
    Link('Imaged specimen', 'Imaging preparation protocol', 'IMAGING PREPARATION PROTOCOL ID (Required)'),
    
    Link('Specimen from organism', 'Collection protocol', 'COLLECTION PROTOCOL ID (Required)'),
    Link('Specimen from organism', 'Donor organism','INPUT DONOR ORGANISM ID (Required)','DONOR ORGANISM ID (Required)')
]

def remove_empty_tabs_and_fields(spreadsheet:str, first_data_line:int=FIRST_DATA_LINE):
    spreadsheet_obj = pd.ExcelFile(spreadsheet, engine_kwargs={'read_only': False})
    for sheet in spreadsheet_obj.sheet_names:
        if len(spreadsheet_obj.parse(sheet)) <= first_data_line:
            spreadsheet_obj.book.remove(spreadsheet_obj.book[sheet])
        del_cols = [i + 1 for i,x in enumerate(spreadsheet_obj.parse(sheet)[FIRST_DATA_LINE:].isna().all()) if x]
        del_cols.reverse()
        _ = [spreadsheet_obj.book[sheet].delete_cols(col, 1) for col in del_cols]
    spreadsheet_obj.book.save(spreadsheet)

def derive_exprimental_design(initial_tab, spreadsheet):
    spreadsheet_obj = pd.ExcelFile(spreadsheet)
    sheet_cache = {}
    applied_links = []
    
    def parse_sheet(sheet_name):
        if sheet_name not in sheet_cache:
            sheet_cache[sheet_name] = spreadsheet_obj.parse(sheet_name)
        return sheet_cache[sheet_name]
    
    def check_link_exists(link):
        if link.target not in spreadsheet_obj.sheet_names:
            return False
        source_sheet = parse_sheet(link.source)
        target_sheet = parse_sheet(link.target)
        if link.source_field not in source_sheet.columns:
            return False
        if link.target_field not in target_sheet.columns:
            return False
        return True
    
    def dfs(current_entity, current_path, all_paths):
        current_path.append(current_entity)
        next_links = [link for link in links_all if link.source == current_entity]
        if not next_links:
            all_paths.append(current_path.copy())
        else:
            for link in next_links:
                if link.target not in current_path and check_link_exists(link):
                    applied_links.append(link)
                    dfs(link.target, current_path, all_paths)
        current_path.pop()
    
    all_paths = []
    dfs(initial_tab, [], all_paths)
    return all_paths, applied_links
                

def rename_vague_friendly_names(spreadsheet:str, first_data_line:int=FIRST_DATA_LINE):
    req_str = "(Required)"
    vague_entities = ['BIOMATERIAL', 'PROTOCOL']
    vague_entities.extend([id + ' ' + req_str for id in vague_entities])
    spreadsheet_obj = pd.ExcelFile(spreadsheet, engine_kwargs={'read_only': False})
    # check if biomaterial ID of donor exists in donor tab
    if any(id.value == links_all[-1].target_field for id in spreadsheet_obj.book[links_all[-1].target][1]):
        return
    print('Spreadsheet does not have appropriate fiendly names. Will try to edit accordingly')
    spreadsheet_obj.book.save(spreadsheet.replace('.xlsx','_backup.xlsx'))
    for sheet in spreadsheet_obj.sheet_names:
        for field in spreadsheet_obj.book[sheet][1]:
            if not field.value:
                continue
            field.value = (field.value.removesuffix(req_str).upper() +  req_str) if req_str in field.value else field.value.upper()
            if any(entity in field.value for entity in vague_entities):
                field_program_name = spreadsheet_obj.book[sheet][first_data_line][field.column].value
                field_friendly_entity = field_program_name.split('.')[0].replace('_',' ').capitalize()
                entity = field.value.split(' ')[0]
                field.value = field.value.replace(entity, field_friendly_entity.upper())
                if field_friendly_entity != sheet and entity == 'BIOMATERIAL':
                    field.value = f'INPUT {field.value}'
    spreadsheet_obj.book.save(spreadsheet)


def now():
    return lambda : datetime.now().strftime('%H%M%S.%f')

def explode_csv_col(df :pd.DataFrame, column :str, sep=',') -> pd.DataFrame:
    cols={}
    cols[column] = df[column].str.split(sep)
    return df.assign(**cols).explode(column)

def format_column_name(column_name, namespace):
    return f'{namespace}_{column_name}'

def prefix_columns(df, prefix):
    return df.rename(columns=lambda c:format_column_name(namespace=prefix,column_name=c))

def remove_field_desc_lines(df:pd.DataFrame) -> pd.DataFrame:
    return df[FIRST_DATA_LINE:]

def merge_multiple_input_entities(worksheet:pd.DataFrame,
                            target:pd.DataFrame, 
                            source_field:str, 
                            target_field:str, 
                            link:Link):
    # Perform merge operation
    result = pd.merge(worksheet, target, how=link.join_type, left_on=source_field, right_on=target_field, suffixes=(None, '_y'))
    
    # Identify duplicated columns
    duplicated_cols = [col for col in result.columns if col.endswith('_y')]
    overwriting_cols = [x.strip('_y') for x in duplicated_cols]
    
    # Check for conflicts between columns
    result_na_none = result[overwriting_cols].dropna(how='all')
    result_na_y = result[duplicated_cols].dropna(how='all')
    
    # exclude case a field is derived from different tabs
    # (i.e. one cell suspension from organoid AND specimen)
    # for selected columns, values should either everything na, or None or _y should be na
    # If there are conflicts, print a message and drop duplicate columns
    if not result_na_y.index.intersection(result_na_none.index).empty:
        print(f'Multiple {link.target} for the same element. Will skip {link.target} from {link.source}')
        result = result.drop(columns=duplicated_cols)
    else:
        # If no conflicts, fill NaN values with values from duplicate columns and drop source_field
        result = result.drop(columns=duplicated_cols).fillna(result_na_y.rename(columns=lambda x: x.strip('_y')))
        result.drop(columns=source_field, inplace=True)
    return result


def join_worksheet(worksheet:pd.DataFrame, 
                   link:Link, 
                   spreadsheet:str) -> pd.DataFrame:
    print(f'joining [{link.source}] to [{link.target}]')
    print(f'fields [{link.source_field}] and [{link.target_field}]')
    try:
        source_field = format_column_name(column_name=link.source_field, namespace=link.source)
        target_field = format_column_name(column_name=link.target_field, namespace=link.target)
        worksheet = explode_csv_col(df=worksheet, column=source_field, sep=SEP)
        
        spreadsheet_obj = pd.ExcelFile(spreadsheet)
        if link.target not in spreadsheet_obj.sheet_names:
            raise ValueError(f'spreadsheet does not contain {link.target} sheet. Possible names {sorted(spreadsheet_obj.sheet_names)}')
        target = spreadsheet_obj.parse(link.target)
        
        target = pd.read_excel(spreadsheet, link.target)
        target = remove_field_desc_lines(target)
        target = prefix_columns(target, prefix=link.target)
        
        target = explode_csv_col(target, column=target_field, sep=SEP)
        
        result = worksheet.merge(target,
                                 how=link.join_type, 
                                 left_on=source_field, 
                                 right_on=target_field)
        if [col for col in result.columns if col.endswith('_y')]:
            result = merge_multiple_input_entities(worksheet, target, source_field, target_field, link)
        else:
            result.drop(columns=target_field)

        print(f'record count: original {len(worksheet)}, joined {len(result)}')
        if len(result.index) == 0:
            raise RuntimeError('problem joining [{link.source}] to [{link.target}] using fields [{source_field}] and [{target_field}]: join resulted in zero rows')
        
    except KeyError as e:
        err_msg = f'problem joining [{link.source}] to [{link.target}] using fields [{source_field}] and [{target_field}]: {e}'
        raise RuntimeError(err_msg) from e
    return result

def flatten_spreadsheet(spreadsheet, report_entity, links):
    spreadsheet_obj = pd.ExcelFile(spreadsheet)
    if report_entity not in spreadsheet_obj.sheet_names:
        raise ValueError(f'spreadsheet does not contain {report_entity} sheet')
    report_sheet = spreadsheet_obj.parse(report_entity)
    report_sheet = prefix_columns(report_sheet, prefix=report_entity)
    report_sheet = remove_field_desc_lines(report_sheet)
    flattened = reduce(partial(join_worksheet, spreadsheet=spreadsheet), 
                       links,
                       report_sheet)
    return flattened

def collapse_values(series):
    return "||".join(series.dropna().unique().astype(str))

def main(spreadsheet_filename:str, input_dir:str, output_dir:str):
    spreadsheet = f'{input_dir}/{spreadsheet_filename}'
    spreadsheet_backup = copy(spreadsheet, spreadsheet.replace('.xlsx', '_backup.xlsx'))
    print(f"Copied spreadsheet backup in {spreadsheet_backup}")
    remove_empty_tabs_and_fields(spreadsheet)
    rename_vague_friendly_names(spreadsheet)
    spreadsheet_obj = pd.ExcelFile(spreadsheet)
    report_entities = [entity for entity in ['Analysis file', 'Sequence file', 'Image file'] if entity in spreadsheet_obj.sheet_names]
        
    flattened_list = []
    for report_entity in report_entities:
        # Modify links to include only relevant to this report entity
        _, links_filt = derive_exprimental_design(report_entity, spreadsheet)
        flattened_list.append(flatten_spreadsheet(spreadsheet, report_entity, links_filt))
    flattened = pd.concat(flattened_list, axis=0, ignore_index=True)
    
    # remove empty columns
    flattened.dropna(axis='columns',how='all', inplace=True)
    
    # add project label
    project_info = pd.read_excel(spreadsheet, 'Project')
    data_row_idx = 4
    project_label = project_info['PROJECT LABEL (Required)'][data_row_idx]
    flattened['project_label'] = project_label
    
    # use ingest attribute names as columns
    for column in flattened.columns:
        tab, original_column = column.split('_')
        if tab not in spreadsheet_obj.sheet_names:
            continue
        tab_df = spreadsheet_obj.parse(tab)
        data_row_idx = 2
        ingest_attribute_name = tab_df[original_column][data_row_idx]
        if ingest_attribute_name not in flattened.columns:
            flattened.rename(columns={column:ingest_attribute_name}, inplace=True)
        else:
            flattened.drop(labels=column, axis='columns', inplace=True)
    
    flattened_filename = f'{output_dir}/{splitext(basename(spreadsheet))[0]}_denormalised.csv'
    flattened.to_csv(flattened_filename, index=False)

    flattened_bysample = flattened.groupby('specimen_from_organism.biomaterial_core.biomaterial_id').agg(collapse_values).dropna(axis=1, how='all')
    flattened_bysample_filename = f'{output_dir}/{splitext(basename(spreadsheet))[0]}_bysample.csv'
    flattened_bysample.to_csv(flattened_bysample_filename, index=False)



if __name__ == "__main__":
    args = define_parser().parse_args()

    main(spreadsheet_filename=args.spreadsheet_filename, input_dir=args.input_dir, output_dir=args.output_dir)
