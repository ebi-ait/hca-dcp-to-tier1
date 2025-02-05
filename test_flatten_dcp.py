import unittest
from io import BytesIO

import pandas as pd
import openpyxl
from flatten_dcp import remove_empty_tabs_and_fields, FIRST_DATA_LINE

SAMPLE_VALUES = {
    'Donor organism':{
        'DONOR ORGANISM ID (Required)': ['A unique ID for the donor organism.', '', 'donor_organism.biomaterial_core.biomaterial_id', '', 
                                         'donor_1', 'donor_2'],
        'BIOLOGICAL SEX (Required)': ['The biological sex of the organism.', 'For example: Should be one of: male, female, mixed, or unknown.', 'donor_organism.sex', '', 
                                      'female', 'male'],
        'DEVELOPMENT STAGE (Required)': ['The name of the development stage of the organism.', 'For example: human adult stage; Theiler stage 28', 'donor_organism.development_stage.text', '', 
                                         'human adult stage', 'human adult stage']
    },
    'Specimen from organism': {
        'SPECIMEN FROM ORGANISM ID (Required)': ['A unique ID for the specimen from organism.', '', 'specimen_from_organism.biomaterial_core.biomaterial_id', '', 
                                                 'specimen_1', 'specimen_2' , 'specimen_3'],
        'ORGAN (Required)': ['The text for the term as the user provides it.', 'For example: heart; immune system', 'specimen_from_organism.organ.text', '', 
                             'heart', 'heart', 'lung'],
        'PRESERVATION METHOD': ['The method by which a biomaterial was preserved through the use of chemicals, cold, or other means to prevent or retard biological or physical deterioration.', 'Enter \'fresh\' if not preserved. For example: cryopreservation in liquid nitrogen (dead tissue); fresh', 'specimen_from_organism.preservation_storage.preservation_method', '', 
                             'fresh', 'cryopreservation in liquid nitrogen (dead tissue)', 'cryopreservation in liquid nitrogen (dead tissue)'],
        'COLLECTION PROTOCOL ID (Required)': ['A unique ID for the protocol.', 'Protocol ID should have no spaces.', 'collection_protocol.protocol_core.protocol_id', '', 
                                              'collection_protocol', 'collection_protocol', 'collection_protocol'],
        'INPUT DONOR ORGANISM ID (Required)': ['A unique ID for the biomaterial.', '', 'donor_organism.biomaterial_core.biomaterial_id', '', 
                             'donor_1', 'donor_1', 'donor_2']
    },
    'Cell suspension': {
        'CELL SUSPENSION ID (Required)': ['A unique ID for the cell suspension.', '', 'cell_suspension.biomaterial_core.biomaterial_id', '', 
                                          'cell_suspension_1', 'cell_suspension_2', 'cell_suspension_3', 'cell_suspension_4', 'cell_suspension_5', 'cell_suspension_6'],
        'DISSOCIATION PROTOCOL (Required)': ['unique ID for the protocol', 'Protocol ID should have no spaces', 'dissociation_protocol.protocol_core.protocol_id', '', 
                                             'dissociation_1', 'dissociation_1', 'dissociation_1', 'dissociation_1', 'dissociation_2', 'dissociation_2'],
        'INPUT SPECIMEN FROM ORGANISM ID (Required)': ['A unique ID for the specimen from organism.', '', 'specimen_from_organism.biomaterial_core.biomaterial_id', '', 
                                                       'specimen_1', 'specimen_1', 'specimen_2', 'specimen_2', 'specimen_3', 'specimen_3']
    },
    'Sequence file': {
        'FILE NAME (Required)': ['The name of the file.', 'Include the file extension in the file name. For example: R1.fastq.gz; codebook.json', 'sequence_file.file_core.file_name', '', 'cell_suspension_1_S1_L001_I1_001.fastq.gz', 
                                 'cell_suspension_1_S1_L001_I1_001.fastq.gz', 'cell_suspension_2_S1_L001_I1_001.fastq.gz', 'cell_suspension_3_S1_L001_I1_001.fastq.gz',
                                 'cell_suspension_4_S1_L001_I1_001.fastq.gz', 'cell_suspension_5_S1_L001_I1_001.fastq.gz', 'cell_suspension_6_S1_L001_I1_001.fastq.gz'],
        'INPUT CELL SUSPENSION ID (Required)': ['A unique ID for the cell suspension.', '', 'cell_suspension.biomaterial_core.biomaterial_id', '', 
                                                'cell_suspension_1', 'cell_suspension_2', 'cell_suspension_3', 'cell_suspension_4', 'cell_suspension_5', 'cell_suspension_6'],
        'LIBRARY PREPARATION PROTOCOL ID (Required)': ['A unique ID for the protocol.', 'Protocol ID should have no spaces.', 'library_preparation_protocol.protocol_core.protocol_id', '', 
                                                      '10x_3_v2', '10x_3_v2', '10x_3_v2', '10x_3_v2', '10x_3_v2', '10x_3_v2'],
        'SEQUENCING PROTOCOL ID (Required)': ['A unique ID for the protocol.', 'Protocol ID should have no spaces.', 'sequencing_protocol.protocol_core.protocol_id', '', 
                                              'sequencing_protocol', 'sequencing_protocol', 'sequencing_protocol', 'sequencing_protocol', 'sequencing_protocol', 'sequencing_protocol']
    },
    'Collection protocol': {
        'COLLECTION PROTOCOL ID (Required)': ['A unique ID for the protocol.', 'Protocol ID should have no spaces.', 'collection_protocol.protocol_core.protocol_id', '', 
                                              'collection_protocol'],
        'COLLECTION METHOD': ['The name of a process type being used.', 'For example: enzymatic dissociation; blood draw', 'collection_protocol.method.text', '', 
                              'surgical resection']
    },
    'Library preparation protocol': {
        'LIBRARY PREPARATION PROTOCOL ID (Required)': ['A unique ID for the protocol.', 'Protocol ID should have no spaces.', 'library_preparation_protocol.protocol_core.protocol_id', '', 
                                                       '10x_3_v2'],
        'LIBRARY CONSTRUCTION (Required)': ['The name of a library construction approach being used.', 'For example: 10X v2 sequencing; Smart-seq2','library_preparation_protocol.library_construction_method.text', '',
                                            "10x 3' v2"]
    },                                            
    'Sequencing protocol': {
        'SEQUENCING PROTOCOL ID (Required)': ['A unique ID for the protocol.', 'Protocol ID should have no spaces.', 'sequencing_protocol.protocol_core.protocol_id', '', 
                                              'sequencing_protocol'],
        'INSTRUMENT': ['The full name of the instrument used.', 'For example: Illumina HiSeq 2500; ONT MinION', 'sequencing_protocol.instrument_manufacturer_model.text', '', 
                       'Illumina NovaSeq 6000']
    }
}

def dcp_spreadsheet(sample_values:dict, read_only=False):
    wb = openpyxl.Workbook()
    default_sheet = wb.active
    wb.remove(default_sheet)
    
    for sheet_name, columns in sample_values.items():
        ws = wb.create_sheet(title=sheet_name)
        headers = list(columns.keys())
        ws.append(headers)
        for row in zip(*columns.values()):
            ws.append(row)
    
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    return pd.ExcelFile(buffer, engine_kwargs={'read_only': read_only})


class TestMetadataSpreadsheetEditing(unittest.TestCase):

    # remove_empty_tabs_and_fields
    def test_remove_empty_tabs_len_positive(self):
        spreadsheet_obj = dcp_spreadsheet(SAMPLE_VALUES)
        cleaned_spreadsheet = remove_empty_tabs_and_fields(spreadsheet_obj, first_data_line=FIRST_DATA_LINE)
        self.assertEqual(len(SAMPLE_VALUES), len(cleaned_spreadsheet.sheet_names))
    
    def test_remove_empty_tabs_len_negative(self):
        spreadsheet_obj = dcp_spreadsheet(SAMPLE_VALUES)
        spreadsheet_obj.book['Collection protocol'].delete_rows(FIRST_DATA_LINE)
        cleaned_spreadsheet = remove_empty_tabs_and_fields(spreadsheet_obj, first_data_line=FIRST_DATA_LINE)
        self.assertNotEqual(len(SAMPLE_VALUES), len(cleaned_spreadsheet.sheet_names))

    def test_remove_unnamed_field(self):
        spreadsheet_obj = dcp_spreadsheet({'Donor organism': SAMPLE_VALUES['Donor organism']})
        spreadsheet_obj.book['Donor organism'].insert_cols(1)
        spreadsheet_obj.book['Donor organism']['A4'] = 'donor_organism.uuid'
        spreadsheet_obj.book['Donor organism']['A6'] = '00000000-0000-0000-0000-000000000000'
        spreadsheet_obj.book['Donor organism']['A7'] = '00000000-0000-0000-0000-000000000000'
        null_header_spreadsheet = remove_empty_tabs_and_fields(spreadsheet_obj, first_data_line=FIRST_DATA_LINE)
        donor_df = null_header_spreadsheet.parse('Donor organism').fillna('')
        donor_dict = {col: value.tolist() for col, value in donor_df.items()}
        self.assertDictEqual(SAMPLE_VALUES['Donor organism'], donor_dict)
        self.assertEqual(len(SAMPLE_VALUES['Donor organism']), len(donor_dict))

    def test_remove_empty_field(self):
        spreadsheet_obj = dcp_spreadsheet({'Donor organism': SAMPLE_VALUES['Donor organism']})
        spreadsheet_obj.book['Donor organism'].insert_cols(3)
        spreadsheet_obj.book['Donor organism']['C1'] = 'AGE'
        spreadsheet_obj.book['Donor organism']['C2'] = 'Age of the donor at the time of collection.'
        spreadsheet_obj.book['Donor organism']['C4'] = 'donor_organism.organism_age'
        null_values_spreadsheet = remove_empty_tabs_and_fields(spreadsheet_obj, first_data_line=FIRST_DATA_LINE)
        donor_df = null_values_spreadsheet.parse('Donor organism').fillna('')
        donor_dict = {col: value.tolist() for col, value in donor_df.items()}
        self.assertDictEqual(SAMPLE_VALUES['Donor organism'], donor_dict)
        self.assertEqual(len(SAMPLE_VALUES['Donor organism']), len(donor_dict))

    def test_remove_multiple_fields(self):
        spreadsheet_obj = dcp_spreadsheet({'Donor organism': SAMPLE_VALUES['Donor organism']})
        spreadsheet_obj.book['Donor organism'].insert_cols(1)
        spreadsheet_obj.book['Donor organism']['A4'] = 'donor_organism.uuid'
        spreadsheet_obj.book['Donor organism']['A6'] = '00000000-0000-0000-0000-000000000000'
        spreadsheet_obj.book['Donor organism']['A7'] = '00000000-0000-0000-0000-000000000000'
        spreadsheet_obj.book['Donor organism'].insert_cols(4)
        spreadsheet_obj.book['Donor organism']['D1'] = 'AGE'
        spreadsheet_obj.book['Donor organism']['D2'] = 'Age of the donor at the time of collection.'
        spreadsheet_obj.book['Donor organism']['D4'] = 'donor_organism.organism_age'
        null_col_spreadsheet = remove_empty_tabs_and_fields(spreadsheet_obj, first_data_line=FIRST_DATA_LINE)
        donor_df = null_col_spreadsheet.parse('Donor organism').fillna('')
        donor_dict = {col: value.tolist() for col, value in donor_df.items()}
        self.assertDictEqual(SAMPLE_VALUES['Donor organism'], donor_dict)
        self.assertEqual(len(SAMPLE_VALUES['Donor organism']), len(donor_dict))

if __name__ == "__main__":
    unittest.main()
