## Init notebook by Amnon Khen
## https://github.com/ebi-ait/hca-ebi-dev-team/blob/master/scripts/metadata-spreadsheet-by-file/HCA%20Project%20Metadata%20Spreadsheet.ipynb

import argparse
from os.path import basename, splitext

from datetime import datetime
from functools import partial, reduce
from dataclasses import dataclass

import pandas as pd


def define_parser():
    """Defines and returns the argument parser."""
    parser = argparse.ArgumentParser(description="Parser for the arguments")
    parser.add_argument("--spreadsheet", "-s", action="store",
                        dest="spreadsheet", type=str, required=True, help="dcp spreadsheet filename")
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
    Link('Sequence file','Library preparation protocol', 'LIBRARY PREPARATION PROTOCOL ID (Required)'),
    Link('Sequence file', 'Cell suspension', 'INPUT CELL SUSPENSION ID (Required)','CELL SUSPENSION ID (Required)'),
    
    Link('Analysis file', 'Analysis protocol', 'ANALYSIS PROTOCOL ID (Required)', 'ANALYSIS PROTOCOL ID'),
    Link('Analysis file', 'Cell suspension', 'CELL SUSPENSION ID (Required)'),
    Link('Analysis file', 'Library preparation protocol', 'LIBRARY PREPARATION PROTOCOL ID (Required)'),
    Link('Analysis file', 'Sequencing protocol', 'SEQUENCING PROTOCOL ID (Required)'),
    Link('Analysis file', 'Imaged specimen', 'IMAGED SPECIMEN ID (Required)'),    
    
    Link('Cell suspension', 'Organoid','INPUT ORGANOID ID (Required)','ORGANOID ID (Required)'),
    Link('Cell suspension', 'Cell line','INPUT CELL LINE ID (Required)','CELL LINE ID (Required)'),
    Link('Cell suspension', 'Specimen from organism','INPUT SPECIMEN FROM ORGANISM ID (Required)','SPECIMEN FROM ORGANISM ID (Required)'),
    Link('Cell suspension', 'Enrichment protocol','ENRICHMENT PROTOCOL ID (Required)'),
    Link('Cell suspension', 'Dissociation protocol','DISSOCIATION PROTOCOL ID (Required)'),
    
    Link('Organoid', 'Cell line','INPUT CELL LINE ID (Required)','CELL LINE ID (Required)'),
    Link('Organoid', 'Differentiation protocol','DIFFERENTIATION PROTOCOL ID (Required)', 'DIFFERENTIATION PROTOCOL ID (Required)'),
    Link('Organoid', 'Specimen from organism','INPUT SPECIMEN FROM ORGANISM ID (Required)','SPECIMEN FROM ORGANISM ID (Required)'),
    
    Link('Cell line', 'Specimen from organism','INPUT SPECIMEN FROM ORGANISM ID (Required)','SPECIMEN FROM ORGANISM ID (Required)'),
    Link('Cell line', 'Enrichment protocol','ENRICHMENT PROTOCOL ID (Required)'),
    Link('Cell line', 'Dissociation protocol','DISSOCIATION PROTOCOL ID (Required)'),
    
    Link('Imaged specimen', 'Analysis file', 'IMAGED SPECIMEN ID (Required)', join_type='left'),
    Link('Imaged specimen', 'Specimen from organism', 'INPUT SPECIMEN FROM ORGANISM ID (Required)', 'SPECIMEN FROM ORGANISM ID (Required)'),
    Link('Imaged specimen', 'Imaging preparation protocol', 'IMAGING PREPARATION PROTOCOL ID (Required)'),
    
    Link('Specimen from organism', 'Collection protocol', 'COLLECTION PROTOCOL ID (Required)'),
    Link('Specimen from organism', 'Donor organism','INPUT DONOR ORGANISM ID (Required)','DONOR ORGANISM ID (Required)')        
]

def remove_empty_tabs(spreadsheet:str, first_data_line:int):
    spreadsheet_obj = pd.ExcelFile(spreadsheet, engine_kwargs={'read_only': False})
    for sheet in spreadsheet_obj.sheet_names:
        if len(spreadsheet_obj.parse(sheet)) <= first_data_line:
            spreadsheet_obj.book.remove(spreadsheet_obj.book[sheet])
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
    return df[first_data_line:]

def join_worksheet(worksheet:pd.DataFrame, 
                   link:Link, 
                   spreadsheet:str) -> pd.DataFrame:
    print(f'joining [{link.source}] to [{link.target}]')
    print(f'fields [{link.source_field}] and [{link.target_field}]')
    try:
        source_field = format_column_name(column_name=link.source_field, namespace=link.source)
        target_field = format_column_name(column_name=link.target_field, namespace=link.target)
        worksheet = explode_csv_col(df=worksheet, column=source_field, sep=sep)
        
        spreadsheet_obj = pd.ExcelFile(spreadsheet)
        if link.target not in spreadsheet_obj.sheet_names:
            raise ValueError(f'spreadsheet does not contain {link.target} sheet. Possible names {sorted(spreadsheet_obj.sheet_names)}')
        target = spreadsheet_obj.parse(link.target)
        
        target = pd.read_excel(spreadsheet, link.target)
        target = remove_field_desc_lines(target)
        target = prefix_columns(target, prefix=link.target)
        
        target = explode_csv_col(target, column=target_field, sep=sep)
        
        result = worksheet.merge(target, 
                                 how=link.join_type, 
                                 left_on=source_field, 
                                 right_on=target_field)
        print(f'record count: original {len(worksheet)}, joined {len(result)}')
        result.drop(columns=target_field)
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

def main(spreadsheet:str, input_dir:str, output_dir:str):
    spreadsheet = f'{input_dir}/{spreadsheet}'
    report_entities = ['Analysis file', 'Sequence file', 'Image file']
    remove_empty_tabs(spreadsheet, first_data_line)
    spreadsheet_obj = pd.ExcelFile(spreadsheet)
    report_entity = next((entity for entity in report_entities if entity in spreadsheet_obj.sheet_names), None)
    links = [link for link in links_all if link.source in spreadsheet_obj.sheet_names and link.target in spreadsheet_obj.sheet_names]
    
    # TODO append other report_entities in the flattened spreadsheet if available
    flattened = flatten_spreadsheet(spreadsheet, report_entity, links)
    
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
    
    report_entity_clean = report_entity.replace(" ","-")
    flattened_filename = f'{output_dir}/{splitext(basename(spreadsheet))[0]}_denormalised_{report_entity_clean}.xlsx'
    flattened.to_excel(flattened_filename, index=False)
    flattened.to_csv(flattened_filename.replace('xlsx', 'csv'), index=False)


if __name__ == "__main__":
    args = define_parser().parse_args()

    sep='\\|\\|'
    first_data_line=4

    main(spreadsheet=args.spreadsheet, input_dir=args.input_dir, output_dir=args.output_dir)
