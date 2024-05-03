import yaml

class api_data_model:
    def __init__(self):
        self.api_data = {}

    def merge_api_data(api_files):
        merged_data = {}
        for api_file in api_files:
            api_data = load_yaml_from_file(api_file)
            for key, value in api_data.items():
                if key in merged_data:
                    if isinstance(merged_data[key], dict) and isinstance(value, dict):
                        merged_data[key].update(value)
                    elif isinstance(merged_data[key], list) and isinstance(value, list):
                        # Extend the list with unique items
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

def find_definitions_differences(polish_api_data, santander_api_data):
    polish_definitions = polish_api_data.get('definitions', {})
    santander_definitions = santander_api_data.get('definitions', {})
    return find_differences(polish_definitions, santander_definitions)

def categorize_paths(paths, api_sections):
    categorized_paths = {section: {} for section in api_sections}
    for path, details in paths.items():
        for section, pattern in api_sections.items():
            if path.startswith(pattern):
                categorized_paths[section][path] = details
                break
    return categorized_paths

def find_differences_by_section(polish_api_data, santander_api_data, api_sections):
    differences_by_section = {section: {} for section in api_sections}

    polish_categorized = categorize_paths(polish_api_data.get('paths', {}), api_sections)
    santander_categorized = categorize_paths(santander_api_data.get('paths', {}), api_sections)

    for section in api_sections:
        differences_by_section[section] = find_differences(
            polish_categorized[section], 
            santander_categorized[section]
        )

    return differences_by_section

def find_differences(dict1, dict2, base_path=''):
    differences = {}
    for key in dict1:
        if key not in dict2:
            # Check if dict1[key] is not just an empty placeholder
            if dict1[key]:
                differences[base_path + key] = {'left': dict1[key], 'right': None}
        elif dict1[key] != dict2[key]:
            if isinstance(dict1[key], dict) and isinstance(dict2[key], dict):
                sub_diffs = find_differences(dict1[key], dict2[key], base_path + key + '.')
                if sub_diffs:  # Only add sub-differences if there are any
                    differences.update(sub_diffs)
            elif dict1[key] or dict2[key]:  # Check if at least one side has a meaningful value
                differences[base_path + key] = {'left': dict1[key], 'right': dict2[key]}
    for key in dict2:
        if key not in dict1 and dict2[key]:  # Check if dict2[key] is not just an empty placeholder
            differences[base_path + key] = {'left': None, 'right': dict2[key]}
    return differences