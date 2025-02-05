# Init notebook by Amnon Khen
# https://github.com/ebi-ait/hca-ebi-dev-team/blob/master/scripts/metadata-spreadsheet-by-file/HCA%20Project%20Metadata%20Spreadsheet.ipynb

import argparse

from functools import partial, reduce
from dataclasses import dataclass

import pandas as pd


SEP = '\\|\\|'
FIRST_DATA_LINE = 4


def define_parser():
    """Defines and returns the argument parser."""
    parser = argparse.ArgumentParser(description="Parser for the arguments")
    parser.add_argument("-s", "--spreadsheet_filename", action="store",
                        dest="spreadsheet_filename", type=str, required=True, help="dcp spreadsheet filename")
    parser.add_argument("-i", "--input_dir", action="store", default='dcp_spreadsheet',
                        dest="input_dir", type=str, required=False, help="directory of the dcp spreadsheet file")
    parser.add_argument("-o", "--output_dir", action="store", default='denormalised_spreadsheet',
                        dest="output_dir", type=str, required=False, help="directory for the denormalised spreadsheet output")
    parser.add_argument("-g", "--group_field", action="store", default='specimen_from_organism.biomaterial_core.biomaterial_id',
                        dest="group_field", type=str, required=False, help="field to group output with")
    return parser


@dataclass
class Link:
    source: str
    target: str
    source_field: str
    target_field: str = None
    join_type: str = 'left'
    
    def __post_init__(self):
        if self.target_field is None:
            self.target_field = self.source_field


# All available links that HCA DCP metadata schema supports
links_all = [
    Link('Image file', 'Imaged specimen',
         'INPUT IMAGED SPECIMEN ID (Required)', 'IMAGED SPECIMEN ID (Required)'),
    Link('Image file', 'Imaging protocol', 'IMAGING PROTOCOL ID (Required)'),
    
    Link('Sequence file', 'Sequencing protocol',
         'SEQUENCING PROTOCOL ID (Required)'),
    Link('Sequence file', 'Library preparation protocol',
         'LIBRARY PREPARATION PROTOCOL ID (Required)'),
    Link('Sequence file', 'Cell suspension',
         'INPUT CELL SUSPENSION ID (Required)', 'CELL SUSPENSION ID (Required)'),
    Link('Sequence file', 'Imaged specimen',
         'INPUT IMAGED SPECIMEN ID (Required)', 'IMAGED SPECIMEN ID (Required)'),
    
    Link('Analysis file', 'Analysis protocol',
         'ANALYSIS PROTOCOL ID (Required)', 'ANALYSIS PROTOCOL ID'),
    Link('Analysis file', 'Library preparation protocol',
         'LIBRARY PREPARATION PROTOCOL ID (Required)'),
    Link('Analysis file', 'Sequencing protocol',
         'SEQUENCING PROTOCOL ID (Required)'),
    Link('Analysis file', 'Cell suspension', 
         'CELL SUSPENSION ID (Required)'),
    Link('Analysis file', 'Imaged specimen',
         'INPUT IMAGED SPECIMEN ID (Required)', 'IMAGED SPECIMEN ID (Required)'),
    
    Link('Cell suspension', 'Enrichment protocol',
         'ENRICHMENT PROTOCOL ID (Required)'),
    Link('Cell suspension', 'Dissociation protocol',
         'DISSOCIATION PROTOCOL ID (Required)'),
    Link('Cell suspension', 'Organoid',
         'INPUT ORGANOID ID (Required)', 'ORGANOID ID (Required)'),
    Link('Cell suspension', 'Cell line',
         'INPUT CELL LINE ID (Required)', 'CELL LINE ID (Required)'),
    Link('Cell suspension', 'Specimen from organism',
         'INPUT SPECIMEN FROM ORGANISM ID (Required)', 'SPECIMEN FROM ORGANISM ID (Required)'),
    
    Link('Organoid', 'Differentiation protocol',
         'DIFFERENTIATION PROTOCOL ID (Required)'),
    Link('Organoid', 'Dissociation protocol',
         'DISSOCIATION PROTOCOL ID (Required)'),
    Link('Organoid', 'Cell line', 'INPUT CELL LINE ID (Required)',
         'CELL LINE ID (Required)'),
    Link('Organoid', 'Specimen from organism',
         'INPUT SPECIMEN FROM ORGANISM ID (Required)', 'SPECIMEN FROM ORGANISM ID (Required)'),
    
    Link('Cell line', 'Enrichment protocol',
         'ENRICHMENT PROTOCOL ID (Required)'),
    Link('Cell line', 'Dissociation protocol',
         'DISSOCIATION PROTOCOL ID (Required)'),
    Link('Cell line', 'Specimen from organism',
         'INPUT SPECIMEN FROM ORGANISM ID (Required)', 'SPECIMEN FROM ORGANISM ID (Required)'),
    
    Link('Imaged specimen', 'Specimen from organism',
         'INPUT SPECIMEN FROM ORGANISM ID (Required)', 'SPECIMEN FROM ORGANISM ID (Required)'),
    Link('Imaged specimen', 'Imaging preparation protocol',
         'IMAGING PREPARATION PROTOCOL ID (Required)'),

    Link('Specimen from organism', 'Collection protocol',
         'COLLECTION PROTOCOL ID (Required)'),
    Link('Specimen from organism', 'Donor organism',
         'INPUT DONOR ORGANISM ID (Required)', 'DONOR ORGANISM ID (Required)')
]


def remove_empty_tabs_and_fields(spreadsheet_obj: pd.ExcelFile, first_data_line: int = FIRST_DATA_LINE):
    for sheet in spreadsheet_obj.sheet_names:
        if len(spreadsheet_obj.parse(sheet)) <= first_data_line:
            spreadsheet_obj.book.remove(spreadsheet_obj.book[sheet])
            continue
        # is all values NA? and get index values to remove unnamed columns
        del_df = spreadsheet_obj.parse(sheet)[first_data_line:].isna().all().reset_index()
        del_cols = [index + 1 for index, row in del_df.iterrows() if row[0] or 'Unnamed' in row['index']]
        del_cols.reverse()
        _ = [spreadsheet_obj.book[sheet].delete_cols(col, 1) for col in del_cols]
    return spreadsheet_obj


def rename_vague_friendly_names(spreadsheet_obj: pd.ExcelFile, first_data_line: int = FIRST_DATA_LINE):
    req_str = "(Required)"
    vague_entities = ['BIOMATERIAL', 'PROTOCOL']
    vague_entities.extend([id + ' ' + req_str for id in vague_entities])
    # check if biomaterial ID of donor exists in donor tab
    vague_exists = False
    all_fields = {sheet.title: [field.value for field in sheet[1]] for sheet in spreadsheet_obj.book}
    for link in links_all:
        if link.source in all_fields and link.target in all_fields:
            if link.source_field in all_fields[link.source] or link.target_field in all_fields[link.target]:
                vague_exists = True
                break
    if not vague_exists:
        return spreadsheet_obj
    print('Spreadsheet uses vague fiendly names. Will try to edit accordingly')
    for sheet in spreadsheet_obj.sheet_names:
        for field in spreadsheet_obj.book[sheet][1]:
            if not field.value:
                continue
            field.value = (field.value.removesuffix(req_str).upper() +  req_str) if req_str in field.value else field.value.upper()
            if any(entity in field.value for entity in vague_entities):
                field_program_name = spreadsheet_obj.book[sheet][first_data_line][field.column - 1].value
                field_friendly_entity = field_program_name.split('.')[0].replace('_',' ').capitalize()
                entity = field.value.split(' ')[0]
                field.value = field.value.replace(entity, field_friendly_entity.upper())
                if sheet == 'Analysis file' and field_friendly_entity == 'Cell suspension':
                    pass
                elif field_friendly_entity != sheet and entity == 'BIOMATERIAL':
                    field.value = f'INPUT {field.value}'
                if req_str not in field.value and field.value.endswith('ID'):
                    field.value = f'{field.value} {req_str}'
    return spreadsheet_obj


def derive_exprimental_design(report_entity, spreadsheet_obj):
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
    dfs(report_entity, [], all_paths)
    all_paths = sorted(all_paths, key=len)
    print(f"All different paths in the experimental design starting from {report_entity} (no: {len(all_paths)}):")
    for path in all_paths:
        print('->'.join(path))
    return all_paths, applied_links

def extract_pi(spreadsheet_obj:pd.ExcelFile):
    contacts_df = remove_field_desc_lines(spreadsheet_obj.parse('Project - Contributors'))
    pi_details = ['CONTACT NAME (Required)', 'EMAIL ADDRESS']
    present_contacts = [col for col in pi_details if col in contacts_df]
    last_author = pd.DataFrame({col: [None] for col in pi_details})
    corresponding_authors = contacts_df.loc[contacts_df['CORRESPONDING CONTRIBUTOR'] == 'yes', present_contacts] \
        if 'CORRESPONDING CONTRIBUTOR' in contacts_df else pd.DataFrame()
    if not corresponding_authors.empty:
        last_author = corresponding_authors.iloc[[-1]]
    elif 'PROJECT ROLE' in contacts_df:
        filtered_authors = contacts_df.loc[contacts_df['PROJECT ROLE'] != 'data curator', present_contacts]
        last_author = filtered_authors.iloc[[-1]] if not filtered_authors.empty else None
    return last_author.rename(lambda x: f'Project - Contributors_{x}', axis=1).dropna(axis=1, how='all')


def extract_project_info(spreadsheet_obj: pd.ExcelFile, fields: list):
    df = pd.DataFrame()
    for tab in ['Project', 'Project - Publications']:
        if tab not in spreadsheet_obj.sheet_names:
            return df
        sheet = remove_field_desc_lines(spreadsheet_obj.parse(tab))
        cols = [col for col in fields if col in sheet]
        if not cols:
            return df
        sheet = sheet[cols].groupby(cols[0]).agg('; '.join).reset_index().add_prefix(tab + '_')
        df = pd.concat([df, sheet], axis=1)
    return df


def explode_csv_col(df: pd.DataFrame, column: str, sep=',') -> pd.DataFrame:
    cols = {}
    cols[column] = df[column].str.split(sep)
    return df.assign(**cols).explode(column)


def format_column_name(column_name, namespace):
    return f'{namespace}_{column_name}'


def prefix_columns(df, prefix):
    return df.rename(columns=lambda c: format_column_name(namespace=prefix, column_name=c))


def remove_field_desc_lines(df: pd.DataFrame) -> pd.DataFrame:
    return df[FIRST_DATA_LINE:]


def merge_multiple_input_entities(worksheet: pd.DataFrame,
                                  target: pd.DataFrame,
                                  source_field: str,
                                  target_field: str,
                                  link: Link):
    # Perform merge operation
    result = pd.merge(worksheet, target, how=link.join_type, suffixes=(None, '_y'),
                      left_on=source_field, right_on=target_field)

    # Identify duplicated columns
    duplicated_cols = [col for col in result.columns if col.endswith('_y')]
    overwriting_cols = [x.strip('_y') for x in duplicated_cols]

    # Check for conflicts
    for orig_col, dup_col in zip(overwriting_cols, duplicated_cols):
        # Find rows where both original and duplicate columns have non-null values
        conflict_mask = result[orig_col].notna() & result[dup_col].notna()
        if conflict_mask.any():
            identical_mask = conflict_mask & (result[orig_col] == result[dup_col])
            combine_mask = conflict_mask & ~identical_mask
            if combine_mask.any():
                print(f"Combining non-identical values in {orig_col}")
                result.loc[combine_mask, orig_col] = result.loc[combine_mask, [orig_col, dup_col]]\
                    .apply(lambda x: '||'.join(x.astype(str)))
            
            # For identical values, keep the original
            result.loc[identical_mask, orig_col] = result.loc[identical_mask, orig_col]
        
        # Fill NA values in original column from duplicate column
        result[orig_col] = result[orig_col].where(
            result[orig_col].notna(),
            result[dup_col]
        )
        
        # Drop the duplicate column
        result = result.drop(columns=[dup_col])

    # Drop the source field if it's no longer needed
    if source_field != target_field:
        result = result.drop(columns=[source_field])

    return result

def join_worksheet(worksheet: pd.DataFrame,
                   link: Link,
                   spreadsheet_obj: pd.ExcelFile) -> pd.DataFrame:
    print(f'joining [{link.source}] to [{link.target}]')
    # print(f'fields [{link.source_field}] and [{link.target_field}]')
    try:
        source_field = format_column_name(column_name=link.source_field, namespace=link.source)
        target_field = format_column_name(column_name=link.target_field, namespace=link.target)
        worksheet = explode_csv_col(df=worksheet, column=source_field, sep=SEP)
        
        if link.target not in spreadsheet_obj.sheet_names:
            raise ValueError(f'spreadsheet does not contain {link.target} sheet. Possible names {sorted(spreadsheet_obj.sheet_names)}')
        target = spreadsheet_obj.parse(link.target)
        
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
        
        # print(f'record count: original {len(worksheet)}, joined {len(result)}')
        if len(result.index) == 0:
            raise RuntimeError('problem joining [{link.source}] to [{link.target}] using fields [{source_field}] and [{target_field}]: join resulted in zero rows')
        
    except KeyError as e:
        err_msg = f'problem joining [{link.source}] to [{link.target}] using fields [{source_field}] and [{target_field}]: {e}'
        raise RuntimeError(err_msg) from e
    return result


def flatten_spreadsheet(spreadsheet_obj, report_entity, links):
    if report_entity not in spreadsheet_obj.sheet_names:
        raise ValueError(f'spreadsheet does not contain {report_entity} sheet')
    report_sheet = spreadsheet_obj.parse(report_entity)
    report_sheet = prefix_columns(report_sheet, prefix=report_entity)
    report_sheet = remove_field_desc_lines(report_sheet)
    flattened = reduce(partial(join_worksheet, spreadsheet_obj=spreadsheet_obj),
                       links,
                       report_sheet)
    return flattened


def check_merge_conflict(df, column1, column2):
    return df[column1].notna() & df[column2].notna() & (df[column1] != df[column2])


def append_merge_conflicts(df, column1, column2, merge_conflict):
    df.loc[merge_conflict, column1] = df.loc[merge_conflict, [column1, column2]].apply(lambda x: '||'.join(x.astype(str)), axis=1)
    return df


def collapse_values(series):
    return "||".join(series.dropna().unique().astype(str))


def main(spreadsheet_filename: str, input_dir: str, output_dir: str, 
         group_field: str = 'specimen_from_organism.biomaterial_core.biomaterial_id'):
    spreadsheet = f'{input_dir}/{spreadsheet_filename}'
    # open excel with write only to remove empty tabs & fields & unnamed columns
    spreadsheet_obj = pd.ExcelFile(spreadsheet, engine_kwargs={'read_only': False})
    spreadsheet_obj = remove_empty_tabs_and_fields(spreadsheet_obj)
    spreadsheet_obj = rename_vague_friendly_names(spreadsheet_obj)
    spreadsheet_obj.book.save(spreadsheet)
    report_entities = [entity for entity in ['Analysis file', 'Sequence file', 'Image file'] if entity in spreadsheet_obj.sheet_names]
        
    flattened_list = []
    for report_entity in report_entities:
        # Modify links to include only relevant to this report entity
        _, links_filt = derive_exprimental_design(report_entity, spreadsheet_obj)
        flattened_list.append(flatten_spreadsheet(spreadsheet_obj, report_entity, links_filt))
    flattened = pd.concat(flattened_list, axis=0, ignore_index=True)
    
    # remove empty columns
    flattened.dropna(axis='columns', how='all', inplace=True)
    
    # add project label
    project_fields = ['PROJECT LABEL (Required)', 'PROJECT TITLE (Required)', 'INSDC PROJECT ACCESSION', 'GEO SERIES ACCESSION', 'ARRAYEXPRESS ACCESSION',
                      'INSDC STUDY ACCESSION', 'BIOSTUDIES ACCESSION', 'EGA Study/Dataset Accession(s)', 'dbGap Study Accession(s)', 'PUBLICATION TITLE (Required)', 'PUBLICATION DOI']
    project_df = extract_project_info(spreadsheet_obj, project_fields)
    project_df = pd.concat([project_df, extract_pi(spreadsheet_obj).reset_index(drop=True)], axis=1)
    project_df = project_df.loc[project_df.index.repeat(len(flattened))].reset_index(drop=True)
    flattened = pd.concat([flattened, project_df], axis=1)

    # use ingest attribute names as columns
    for column in flattened.columns:
        tab, original_column = column.split('_')
        if tab not in spreadsheet_obj.sheet_names:
            print(f'Skipping {column} since {tab} not in spreadsheet.')
            continue
        tab_df = spreadsheet_obj.parse(tab)
        data_row_idx = 2
        ingest_attribute_name = tab_df[original_column][data_row_idx]
        if ingest_attribute_name not in flattened.columns:
            flattened.rename(columns={column:ingest_attribute_name}, inplace=True)
        else:
            # TODO: Add exception for process.location for `institute` & `sample_collection_site`
            merge_conflict = check_merge_conflict(flattened, ingest_attribute_name, column)
            if merge_conflict.any():
                print(f"Conflicting metadata merging {column} into {ingest_attribute_name}. Appending all values with || separator.")
                flattened = append_merge_conflicts(flattened, ingest_attribute_name, column, merge_conflict)
            flattened[ingest_attribute_name] = flattened[ingest_attribute_name].combine_first(flattened[column])
            flattened.drop(labels=column, axis='columns', inplace=True)


    if group_field not in flattened:
        print(f'Group field provided not in spreadsheet: {group_field}')
        return
    flattened_grouped = flattened.groupby(group_field).agg(collapse_values).dropna(axis=1, how='all')
    
    flattened.to_csv(f"{output_dir}/{spreadsheet_filename.replace('.xlsx', '_denormalised.csv')}", index=False)
    flattened_grouped.to_csv(f"{output_dir}/{spreadsheet_filename.replace('.xlsx', '_grouped.csv')}", index=True)


if __name__ == "__main__":
    args = define_parser().parse_args()

    main(spreadsheet_filename=args.spreadsheet_filename,
         input_dir=args.input_dir, output_dir=args.output_dir,
         group_field=args.group_field)
