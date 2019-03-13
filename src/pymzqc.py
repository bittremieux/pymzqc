import json
import os
import urllib.request
from typing import Dict, List, Union

import jsonschema
import pronto
from jsonschema.exceptions import ValidationError


def _get_cv_parameters(val: Union[Dict, List, float, int, str]):
    if hasattr(val, 'items'):
        if 'cvRef' in val:
            yield val
        for k, v in val.items():
            if isinstance(v, dict):
                yield from _get_cv_parameters(v)
            elif isinstance(v, list):
                for d in v:
                    yield from _get_cv_parameters(d)


def validate(filename: str):
    with open(filename) as json_in:
        # Syntactic validation of the mzQC file against the JSON schema.
        instance = json.load(json_in)
        version = instance['mzQC']['version'].replace('.', '_')
        schema_url = f'https://raw.githubusercontent.com/HUPO-PSI/mzQC/' \
            f'master/schema/v{version}/mzqc_{version}.schema.json'
        with urllib.request.urlopen(schema_url, timeout=2) as schema_in:
            schema = json.loads(schema_in.read().decode())
            jsonschema.validate(instance, schema,
                                format_checker=jsonschema.FormatChecker())

        # Semantic validation of the JSON file.
        # Verify that cvRefs are valid.
        cv_refs = instance['mzQC']['cv'].keys()
        for cv_parameter in _get_cv_parameters(instance['mzQC']):
            if cv_parameter['cvRef'] not in cv_refs:
                raise ValidationError(f'Unknown CV reference '
                                      f'<{cv_parameter["cvRef"]}>')
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
        # Verify that all references to terms in the CVs are correct.
        cvs = {cv_ref: pronto.Ontology(cv['uri'], False)
               for cv_ref, cv in instance['mzQC']['cv'].items()}
        for cv_parameter in _get_cv_parameters(instance):
            # Verify that the term exists in the CV.
            cv_term = cvs[cv_parameter['cvRef']].get(cv_parameter['accession'])
            if cv_term is None:
                raise ValidationError(f'Term {cv_parameter["accession"]} not '
                                      f'found in CV <{cv_parameter["cvRef"]}>')
            # Verify that the term name is correct.
            elif cv_parameter['name'] != cv_term.name:
                raise ValidationError(
                    f'Incorrect name for CV term {cv_parameter["accession"]}: '
                    f'"{cv_parameter["name"]}" != "{cv_term.name}"')
