import json
import re

def read_json(filepath):
    with open(filepath, 'r') as file:
        data = json.load(file)

    return data


def write_json(filepath, data):
    with open(filepath, 'w') as file:
        json.dump(data, file)


def get_default_schema(type):
    schema_dir = 'component_schemas'
    filepath = f"{schema_dir}/{type}.json"

    return read_json(filepath)

def get_key_and_content(str):
    match = re.match(r'{(.*?)}(.*)', str)
    if match:
        key = match.group(1)
        text = match.group(2)
        
        return [key, text]
    else:
        return None
