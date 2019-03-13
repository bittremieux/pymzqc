import json
import os

import jsonschema
from jsonschema.exceptions import ValidationError


MZQC_VERSION = '0.0.11'
QCCV_VERSION = '0.1.0'


def _find(key, val):
    if hasattr(val, 'items'):
        for k, v in val.items():
            if k == key:
                yield v
            elif isinstance(v, dict):
                for result in _find(key, v):
                    yield result
            elif isinstance(v, list):
                for d in v:
                    for result in _find(key, d):
                        yield result


def validate(filename: str):
    # TODO: Do we want to be able to validate against
    #       older versions of the schema?
    filename_schema = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), '..', 'data',
        f'mzqc_{MZQC_VERSION.replace(".", "_")}.schema.json')
    with open(filename) as json_in, open(filename_schema) as schema_in:
        # Syntactic validation of the mzQC file against the JSON schema.
        instance = json.load(json_in)
        schema = json.load(schema_in)
        jsonschema.validate(
            instance, schema, format_checker=jsonschema.draft7_format_checker)

        # Semantic validation of the JSON file.
        # Verify that cvRefs are valid.
        cv_refs = instance['mzQC']['cv'].keys()
        for cv_ref in _find('cvRef', instance['mzQC']):
            if cv_ref not in cv_refs:
                raise ValidationError(f'Unknown CV reference <{cv_ref}>')
        quality_lists = []
        if 'runQuality' in instance['mzQC']:
            quality_lists.extend(instance['mzQC']['runQuality'])
        if 'setQuality' in instance['mzQC']:
            quality_lists.extend(instance['mzQC']['setQuality'])
        # Verify that input files are consistent and unique.
        for quality_list in quality_lists:
            files = set()
            for input_file in quality_list['metadata']['inputFiles']:
                if input_file['name'] != os.path.splitext(
                        os.path.basename(input_file['location']))[0]:
                    raise ValidationError(f'Inconsistent file name and '
                                          f'location: {input_file["name"]} - '
                                          f'{input_file["location"]}')
                if input_file['name'] not in files:
                    files.add(input_file['name'])
                else:
                    raise ValidationError(f'Duplicate inputFile: '
                                          f'name = {input_file["name"]}')
        # Verify that qualityParameters are unique within a run/setQuality.
        for quality_list in quality_lists:
            accessions = set()
            for quality_parameter in quality_list['qualityParameters']:
                accession = quality_parameter['accession']
                if accession not in accessions:
                    accessions.add(accession)
                else:
                    raise ValidationError(f'Duplicate qualityParameter: '
                                          f'accession = {accession}')

        # Semantic validation against the QC CV.
        # TODO
