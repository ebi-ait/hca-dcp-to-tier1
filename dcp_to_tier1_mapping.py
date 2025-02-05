"""
DCP_TIER1_MAP: dictionary with mapping between DCP and Tier 1 fields
tier1: tier 1 v1 list
for updated mapping:
https://docs.google.com/spreadsheets/d/13oqRLh1awe7bClpX617_HQaoS8XPZV5JKPtPEff8-p4/
"""

DCP_TIER1_MAP = {
    'project.project_core.project_title': 'title',
    'project.contributors.name': 'study_pi',
    # none: 'batch_condition',
    # none: 'default_embedding',
    # none: 'comments',
    # 'specimen_from_organism.biomaterial_core.biomaterial_id': 'sample_id',
    'donor_organism.biomaterial_core.biomaterial_id': 'donor_id',
    'library_preparation_protocol.protocol_core.protocols_io_doi': 'protocol_url',
    # 'project.contributors.institute': 'institute',
    # 'sample_collection_site': 'sample_collection_site',
    # 'specimen_from_organism.biomaterial_core.timecourse.value': 'sample_collection_relative_time_point',
    'cell_suspension.biomaterial_core.biomaterial_id': 'library_id',
    'donor_organism.genus_species.ontology': 'organism_ontology_term_id',
    # 'donor_organism.death.hardy_scale': 'manner_of_death',
    # 'donor_organism.is_living': 'sample_source',
    # 'specimen_from_organism.transplant_organ': 'sample_source',
    # 'donor_organism.sex': 'sex_ontology_term_id',
    'collection_protocol.method.ontology_label': 'sample_collection_method',
    # none: 'tissue_type',
    # 'donor_organism.diseases.ontology_label': 'sampled_site_condition_donor',
    # 'specimen_from_organism.diseases.ontology_label': 'sampled_site_condition_specimen',
    'specimen_from_organism.organ.ontology': 'tissue_ontology_term_id',
    'specimen_from_organism.organ.ontology_label': 'tissue_ontology_term',
    # 'specimen_from_organism.organ.text': 'tissue_free_text',
    # 'specimen_from_organism.organ.ontology_label': 'tissue_free_text_label',
    # 'specimen_from_organism.organ_parts.text': 'tissue_free_text_parts',
    # 'specimen_from_organism.organ_parts.ontology': 'tissue_ontology_term_id_parts',
    # 'specimen_from_organism.organ_parts.ontology_label': 'tissue_free_text_label_parts',
    'specimen_from_organism.preservation_storage.storage_method': 'sample_preservation_method',
    # 'library_preparation_protocol.nucleic_acid_source': 'suspension_type',
    # 'enrichment_protocol.markers': 'cell_enrichment',
    'cell_suspension.cell_morphology.percent_cell_viability': 'cell_viability_percentage',
    'cell_suspension.estimated_cell_count': 'cell_number_loaded',
    'specimen_from_organism.collection_time': 'sample_collection_year',
    'library_preparation_protocol.library_construction_method.ontology': 'assay_ontology_term_id',
    'library_preparation_protocol.library_construction_method.ontology_label': 'assay_ontology_term',
    'sequence_file.library_prep_id': 'library_preparation_batch',
    'library_sequencing_run': 'library_sequencing_run',
    # 'library_preparation_protocol.end_bias': 'sequenced_fragment',
    'sequencing_protocol.instrument_manufacturer_model.text': 'sequencing_platform',
    # none: 'is_primary_data',
    # 'analysis_file.genome_assembly_version': 'reference_genome',
    'analysis_protocol.gene_annotation_version': 'gene_annotation_version',
    # 'analysis_protocol.alignment_software': 'alignment_software',
    'analysis_protocol.intron_inclusion': 'intron_inclusion',
    # none: 'author_cell_type',
    # none: 'cell_type_ontology_term_id',
    # 'donor_organism.diseases.ontology': 'disease_ontology_term_id',
    # 'donor_organism.human_specific.ethnicity.ontology': 'self_reported_ethnicity_ontology_term_id'
    # 'donor_organism.organism_age': 'development_stage_ontology_term_id'
}
TIER1 = {'uns': ['title', 'study_pi', 'batch_condition', 'default_embedding', 'comments'],
         'obs': ['sample_id', 'donor_id', 'protocol_url', 'institute', 'sample_collection_site',
                 'sample_collection_relative_time_point', 'library_id', 'library_id_repository',
                 'author_batch_notes', 'organism_ontology_term_id', 'manner_of_death',
                 'sample_source', 'sex_ontology_term_id', 'sex_ontology_term'
                 'sample_collection_method', 'tissue_type', 'sampled_site_condition', 
				 'tissue_ontology_term_id', 'tissue_ontology_term', 'tissue_free_text', 
				 'sample_preservation_method', 'suspension_type', 'cell_enrichment', 
				 'cell_viability_percentage', 'cell_number_loaded', 'sample_collection_year', 
				 'assay_ontology_term_id', 'assay_ontology_term', 'library_preparation_batch',
                 'library_sequencing_run', 'sequenced_fragment', 'sequencing_platform',
                 'is_primary_data', 'reference_genome', 'gene_annotation_version',
                 'alignment_software', 'intron_inclusion', 'author_cell_type',
                 'cell_type_ontology_term_id', 'disease_ontology_term_id',
                 'self_reported_ethnicity_ontology_term_id', 'development_stage_ontology_term_id',
                 # helper fields
                 # 'manner_of_death_string', 'library_id_repository_name', 'library_id_repository_description',
                 # 'sample_id_name', 'sample_id_description', 'donor_id_name', 'donor_id_description'
                 ]
         }
HSAP_AGE_TO_DEV_DICT = {
    # Embryonic stage = A term from the set of Carnegie stages 1-23 = (up to 8 weeks after conception; e.g. HsapDv:0000003)
    # Fetal development = A term from the set of 9 to 38 week post-fertilization human stages = (9 weeks after conception and before birth; e.g. HsapDv:0000046)
    (0, 14): 'HsapDv:0000264',
    (15, 19): 'HsapDv:0000268',
    (20, 29): 'HsapDv:0000237',
    (30, 39): 'HsapDv:0000238',
    (40, 49): 'HsapDv:0000239',
    (50, 59): 'HsapDv:0000240',
    (60, 69): 'HsapDv:0000241',
    (70, 79): 'HsapDv:0000242',
    (80, 89): 'HsapDv:0000243',
    (90, 199): 'HsapDv:0000274'
}
