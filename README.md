# HCA - DCP to Tier 1
Convert Human Cell Atlas DCP metadata from a provided dcp metadata [spreadsheet](https://github.com/ebi-ait/geo_to_hca/tree/master/template),into [HCA Tier 1 schema](https://docs.google.com/spreadsheets/d/13oqRLh1awe7bClpX617_HQaoS8XPZV5JKPtPEff8-p4/edit?gid=1404414727#gid=1404414727) spreadsheet. The vice versa conversion is done with https://github.com/ebi-ait/hca-tier1-to-dcp

## Algorithm
This convertion is done in the following steps.
1. Flatten (denormalise) dcp metadata [flatten_dcp.py](flatten_dcp.py)
    1. Edit friendly filenames to add consistent headers in `dcp_spreadsheet`
    1. Derive all experimental design paths (`links_filt`), starting from all available file entities (`report_entities`: `Analysis file`, `Sequence file`, `Image file`)
    1. Join worksheets for each of the `report_entity` present in spreadsheet
    1. Append all joined worksheets to `flatten` data frame.
    1. Add project metadata
    1. Rename headers to ingest programmatic names
    1. Export flat denormalised and grouped csv files
1. Convert to Tier 1 spreadsheet [dcp_to_tier1.py](dcp_to_tier_1.py)
    1. Open denormalised spreadsheet
    1. Edit all conditinally mapped tier 1 fields
    1. Using the [mapping dictionary](dcp_to_tier1_mapping.py) convert all other available Tier 1 metadata
    1. Export to `uns` and `obs` csv files 


## Usage
Tested in python3.9. To run scripts you can run:
```bash
python3 -m pip install -r requirements.txt
python3 flatten_dcp.py -s <spreadsheet_filename> -i <input_dir> -o <output_dir>
python3 dcp_to_tier1.py -s <flat_spreadsheet_filename> -i <input_dir> -o <output_dir>
```
For example: 
```bash
python3 flatten_dcp.py -s AscAdiposeProgenitor_ontologies.xlsx
python3 dcp_to_tier1.py -s AscAdiposeProgenitor_ontologies_grouped.csv
```

### flatten_dcp.py arguments
- `--spreadsheet_filename` or `-s`: DCP metadata spreadsheet filename
    - i.e. `AscAdiposeProgenitor_ontologies.xlsx`, `IGFBP2InhibitsAdipogenesis_ontologies.xlsx`
- `--input_dir` or `-i`: Optional input directory that contains the provided dcp spreadsheet
    - i.e. `dcp_spreadsheet`
- `--output_dir` or `-o`: Optional output directory to generate the flat dcp file
    - i.e. `denormalised_spreadsheet`

### dcp_to_tier1.py arguments
- `--flat_filename` or `-s`: DCP metadata spreadsheet filename
    - i.e. `AscAdiposeProgenitor_ontologies_grouped.csv`, `IGFBP2InhibitsAdipogenesis_ontologies_grouped.csv`
- `--input_dir` or `-i`: Optional input directory that contains the generated flat dcp spreadsheet
    - i.e. `denormalised_spreadsheet`
- `--output_dir` or `-o`: Optional output directory to generate the flat tier1 file
    - i.e. `tier1_output`

### TODO
- Record process location to extract `institute` & `sample_collection_site` in [flatten_dcp.py](flatten_dcp.py)