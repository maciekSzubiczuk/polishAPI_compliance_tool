

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
            if dict1[key]:
                differences[base_path + key] = {'left': dict1[key], 'right': None}
        elif dict1[key] != dict2[key]:
            if isinstance(dict1[key], dict) and isinstance(dict2[key], dict):
                sub_diffs = find_differences(dict1[key], dict2[key], base_path + key + '.')
                if sub_diffs:
                    differences.update(sub_diffs)
            elif dict1[key] or dict2[key]:
                differences[base_path + key] = {'left': dict1[key], 'right': dict2[key]}
    for key in dict2:
        if key not in dict1 and dict2[key]:
            differences[base_path + key] = {'left': None, 'right': dict2[key]}
    return differences
