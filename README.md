# HCA - DCP to Tier 1
Convert Human Cell Atlas DCP metadata from a provided dcp metadata [spreadsheet](https://github.com/ebi-ait/geo_to_hca/tree/master/template),into [HCA Tier 1 schema](https://docs.google.com/spreadsheets/d/13oqRLh1awe7bClpX617_HQaoS8XPZV5JKPtPEff8-p4/edit?gid=1404414727#gid=1404414727) spreadsheet. The vice versa conversion is done with https://github.com/ebi-ait/hca-tier1-to-dcp

## Algorithm
This convertion is done in the following steps.
1. Flatten (denormalise) dcp metadata [flatten_dcp.py](flatten_dcp.py)
    1. 
1. Convert to Tier 1 spreadsheet [convert_to_tier_1.py](convert_to_tier_1.py)
    1. Using the [mapping](tier1_mapping.py) convert to dcp flat metadata file to Tier 1 fields
    1. 
1. 


## Usage
Tested in python3.9. To run scripts you can run:
```bash
python3 -m pip install -r requirements.txt
python3 flatten_dcp.py -s <spreadsheet_filename> -i <input_dir> -o <output_dir>
```
i.e. 
```bash
python3 flatten_dcp.py -s AscAdiposeProgenitor_ontologies.xlsx
```

### Arguments
- `--spreadsheet` or `-s`: DCP metadata spreadsheet. 
    - i.e. `AscAdiposeProgenitor_ontologies.xlsx`, `IGFBP2InhibitsAdipogenesis_ontologies.xlsx`
- `--input_dir` or `-i`: Optional input directory that contains the provided dcp spreadsheet
    - i.e. `dcp_spreadsheet`
- `--output_dir` or `-o`: Optional output directory to generate the flat dcp file
    - i.e. `denormalised_spreadsheet`
