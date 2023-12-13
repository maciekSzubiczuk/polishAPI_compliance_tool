from flask import Flask, render_template, request, redirect, url_for
import yaml
from deepdiff import DeepDiff

app = Flask(__name__)

# Storage for uploaded file contents
polish_api_data = None
santander_api_data = []

api_sections = {
    'PIS': '/v2_1_1.1/payments',
    'CAF': '/v2_1_1.1/confirmation',
    'AIS': '/v2_1_1.1/accounts',
    'AS': '/v2_1_1.1/auth'
}

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

def generate_summary(change):
    summary = []

    def format_yaml(value):
        if isinstance(value, (dict, list)):
            return yaml.dump(value, default_flow_style=False, sort_keys=False).strip()
        return value

    def format_change(path, value, change_type):
        if isinstance(value, dict):
            # Format each key-value pair in the dictionary
            formatted_value = "\n".join([f"  - {k}: {format_yaml(v)}" for k, v in value.items()])
        else:
            formatted_value = format_yaml(value)

        if path == 'Root':  # Avoid including 'Root' in the path
            return f"{change_type}:\n  - {formatted_value}"
        else:
            return f"{change_type}:\n  {path}\n    - {formatted_value}"

    def compare_dicts(left, right, path=''):
        keys = set(left.keys()).union(right.keys())
        for key in keys:
            left_value = left.get(key)
            right_value = right.get(key)
            new_path = f"{path}.{key}" if path else key

            if left_value is None:
                summary.append(format_change(new_path, right_value, "Added"))
            elif right_value is None:
                summary.append(format_change(new_path, left_value, "Removed"))
            elif isinstance(left_value, dict) and isinstance(right_value, dict):
                compare_dicts(left_value, right_value, new_path)
            elif isinstance(left_value, list) and isinstance(right_value, list):
                compare_lists(left_value, right_value, new_path)
            elif left_value != right_value:
                if right_value is None:
                    summary.append(format_change(new_path, left_value, "Removed"))
                else:
                    summary.append(format_change(new_path, right_value, "Added"))

    def compare_lists(left, right, path):
        added_items = [item for item in right if item not in left]
        removed_items = [item for item in left if item not in right]

        for item in added_items:
            summary.append(format_change(path, item, "Added"))
        for item in removed_items:
            summary.append(format_change(path, item, "Removed"))

    # Handling of root level differences
    if isinstance(change['left'], dict) and isinstance(change['right'], dict):
        compare_dicts(change['left'], change['right'])
    elif isinstance(change['left'], list) and isinstance(change['right'], list):
        compare_lists(change['left'], change['right'], '')
    else:
        # Handling simple types like strings at the root level
        compare_dicts({'Root': change['left']}, {'Root': change['right']}, '')

    final_summary = '\n'.join(summary)
    return final_summary



def find_differences(dict1, dict2, base_path=''):
    differences = {}
    for key in dict1:
        if key not in dict2:
            differences[base_path + key] = {'left': dict1[key], 'right': None}
        elif dict1[key] != dict2[key]:
            if isinstance(dict1[key], dict) and isinstance(dict2[key], dict):
                sub_diffs = find_differences(dict1[key], dict2[key], base_path + key + '.')
                differences.update(sub_diffs)
            else:
                differences[base_path + key] = {'left': dict1[key], 'right': dict2[key]}
    for key in dict2:
        if key not in dict1:
            differences[base_path + key] = {'left': None, 'right': dict2[key]}
    return differences

def find_pis_differences(polish_api_data, santander_api_data):
    pis_differences = {}
    polish_paths = polish_api_data.get('paths', {})
    santander_paths = santander_api_data.get('paths', {})

    # Filter for paths with 'x-swagger-router-controller: pis'
    for path, details in polish_paths.items():
        if details.get('x-swagger-router-controller') == 'pis':
            santander_details = santander_paths.get(path)
            if santander_details and details != santander_details:
                pis_differences[path] = {
                    'polish_api': details,
                    'santander_api': santander_details
                }
    
    return pis_differences

@app.route('/', methods=['GET', 'POST'])
def index():
    global polish_api_data, santander_api_data
    if request.method == 'POST':
        polish_api_file = request.files.get('polishapi_file')
        santander_files = request.files.getlist('santander_files')

        if polish_api_file:
            polish_api_data = load_yaml_from_file(polish_api_file)

        if santander_files:
            santander_api_data = merge_api_data(santander_files)

        return redirect(url_for('display'))

    return render_template('upload.html')


@app.route('/display')
def display():
    if not polish_api_data or not santander_api_data:
        return render_template('display.html', differences_by_section={})

    # Find differences by API section
    differences_by_section = find_differences_by_section(polish_api_data, santander_api_data, api_sections)

    # Find differences in definitions
    definitions_differences = find_definitions_differences(polish_api_data, santander_api_data)
    
    # Combine all differences and generate summaries
    all_differences = {}
    for section, diffs in differences_by_section.items():
        formatted_diffs = {}
        for path, change in diffs.items():
            summary = generate_summary(change)
            formatted_diffs[path] = {
                'left': yaml.dump(change['left'], default_flow_style=False, sort_keys=False) if change['left'] else '',
                'right': yaml.dump(change['right'], default_flow_style=False, sort_keys=False) if change['right'] else '',
                'summary': summary
            }
        all_differences[section] = formatted_diffs

    # Add definitions differences with summary
    formatted_definitions_diffs = {}
    for key, change in definitions_differences.items():
        summary = generate_summary(change)
        formatted_definitions_diffs[key] = {
            'left': yaml.dump(change['left'], default_flow_style=False, sort_keys=False) if change['left'] else '',
            'right': yaml.dump(change['right'], default_flow_style=False, sort_keys=False) if change['right'] else '',
            'summary': summary
        }
    all_differences['Definitions'] = formatted_definitions_diffs

    return render_template('display.html', differences_by_section=all_differences)



if __name__ == '__main__':
    app.run(debug=True)


