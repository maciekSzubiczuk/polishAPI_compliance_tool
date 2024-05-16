import yaml

def merge_api_data(api_files):
    merged_data = {}
    for api_file in api_files:
        api_data = load_yaml_from_file(api_file)
        for key, value in api_data.items():
            if key in merged_data:
                if isinstance(merged_data[key], dict) and isinstance(value, dict):
                    merged_data[key].update(value)
                elif isinstance(merged_data[key], list) and isinstance(value, list):
                    for item in value:
                        if item not in merged_data[key]:
                            merged_data[key].append(item)
                else:
                    pass
            else:
                merged_data[key] = value
    return merged_data

def load_yaml_from_file(file):
    if file:
        return yaml.safe_load(file)