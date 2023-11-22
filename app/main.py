from flask import Flask, render_template, request, redirect, url_for
import yaml
from deepdiff import DeepDiff

app = Flask(__name__)

# Temporary storage for uploaded file contents
polish_api_data = None
santander_api_data = []

def load_yaml_from_file(file):
    if file:
        return yaml.safe_load(file)

def generate_summary(change):
    summary = []

    def format_list(value):
        return '\n- ' + '\n- '.join([str(item) for item in value])

    if 'left' in change and change['left'] is None:
        if isinstance(change['right'], list):
            summary.append('Added:\n' + format_list(change['right']))
        else:
            summary.append('Added:\n- ' + str(change['right']))
    elif 'right' in change and change['right'] is None:
        if isinstance(change['left'], list):
            summary.append('Deleted:\n' + format_list(change['left']))
        else:
            summary.append('Deleted:\n- ' + str(change['left']))
    else:
        left = format_list(change['left']) if isinstance(change['left'], list) else '- ' + str(change['left'])
        right = format_list(change['right']) if isinstance(change['right'], list) else '- ' + str(change['right'])
        summary.append('Modified:\nFrom:' + left + '\nTo:' + right)
    
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

        santander_api_data.clear()
        for file in santander_files:
            if file:
                santander_api_data.append(load_yaml_from_file(file))

        return redirect(url_for('display'))

    return render_template('upload.html')

@app.route('/display')
def display():
    all_differences = []
    for santander_api in santander_api_data:
        diffs = find_differences(polish_api_data, santander_api)
        formatted_diffs = {}
        for path, change in diffs.items():
            summary = generate_summary(change)
            formatted_diffs[path] = {
                'left': yaml.dump(change['left'], default_flow_style=False, sort_keys=False) if change['left'] else '',
                'right': yaml.dump(change['right'], default_flow_style=False, sort_keys=False) if change['right'] else '',
                'summary': summary
            }
        all_differences.append(formatted_diffs)

    return render_template('display.html', differences=all_differences)

if __name__ == '__main__':
    app.run(debug=True)






