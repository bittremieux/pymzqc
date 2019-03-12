import json
import os

import jsonschema


MZQC_VERSION = '0.0.11'
QCCV_VERSION = '0.1.0'


def validate(filename: str):
    # TODO: Do we want to be able to validate against
    #       older versions of the schema?
    filename_schema = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), '..', 'data',
        f'mzqc_{MZQC_VERSION.replace(".", "_")}.schema.json')
    with open(filename) as json_in, open(filename_schema) as schema_in:
        # Validate the mzQC file against the JSON schema.
        instance = json.load(json_in)
        schema = json.load(schema_in)
        jsonschema.validate(
            instance, schema, format_checker=jsonschema.draft7_format_checker)
