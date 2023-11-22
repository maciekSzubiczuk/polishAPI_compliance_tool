from flask import Flask, render_template, request, redirect, url_for
import yaml
from deepdiff import DeepDiff

app = Flask(__name__)

# Temporary storage for uploaded file contents
polish_api_data = None
santander_api_data = []

api_sections = {
    'PIS': '/v2_1_1.1/payments',
    'CAF': '/v2_1_1.1/confirmation',
    'AIS': '/v2_1_1.1/accounts',
    'AS': '/v2_1_1.1/auth'
}


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
                    merged_data[key].extend(value)
                else:
                    # Handle other types or conflicts according to your needs
                    pass
            else:
                merged_data[key] = value
    return merged_data



def load_yaml_from_file(file):
    if file:
        return yaml.safe_load(file)

def generate_summary(change):
    summary = []

    def format_value(value, indent=0):
        if isinstance(value, dict):
            return format_dict(value, indent)
        elif isinstance(value, list):
            return format_list(value, indent)
        else:
            return ' ' * indent + str(value)

    def format_dict(d, indent=0):
        formatted = []
        for key, value in d.items():
            formatted.append(' ' * indent + f"{key}:")
            formatted.append(format_value(value, indent + 2))
        return '\n'.join(formatted)

    def format_list(l, indent=0):
        return '\n'.join([' ' * indent + f"- {format_value(item, indent + 2)}" for item in l])

    if 'left' in change and change['left'] is None:
        summary.append('Added:\n' + format_value(change['right']))
    elif 'right' in change and change['right'] is None:
        summary.append('Deleted:\n' + format_value(change['left']))
    else:
        summary.append('Modified:\nFrom:\n' + format_value(change['left']) + '\nTo:\n' + format_value(change['right']))

    return summary

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

    differences_by_section = find_differences_by_section(polish_api_data, santander_api_data, api_sections)
    formatted_diffs_by_section = {}
    for section, diffs in differences_by_section.items():
        formatted_diffs = {}
        for path, change in diffs.items():
            summary = generate_summary(change)
            formatted_diffs[path] = {
                'left': yaml.dump(change['left'], default_flow_style=False, sort_keys=False) if change['left'] else '',
                'right': yaml.dump(change['right'], default_flow_style=False, sort_keys=False) if change['right'] else '',
                'summary': summary
            }
        formatted_diffs_by_section[section] = formatted_diffs

    return render_template('display.html', differences_by_section=formatted_diffs_by_section)


if __name__ == '__main__':
    app.run(debug=True)






