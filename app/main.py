from flask import Flask, render_template, request, redirect, url_for
import yaml
from deepdiff import DeepDiff

app = Flask(__name__)

# Temporary storage for uploaded file contents
polish_api_data = None
santander_api_data = []

def categorize_differences(diff):
    categorized_diff = {
        'added': [],
        'removed': [],
        'changed': []
    }

    if 'dictionary_item_added' in diff:
        categorized_diff['added'].extend([str(item) for item in diff['dictionary_item_added']])
    
    if 'dictionary_item_removed' in diff:
        categorized_diff['removed'].extend([str(item) for item in diff['dictionary_item_removed']])
    
    if 'values_changed' in diff:
        categorized_diff['changed'].extend([str(item) for item in diff['values_changed']])

    # Add more categorization as necessary based on the output of DeepDiff

    return categorized_diff


def load_yaml_from_file(file):
    if file:
        return yaml.safe_load(file)

def compare_apis(polish_api, santander_api):
    differences = DeepDiff(polish_api, santander_api, ignore_order=True)
    return differences

def json_serializable_diff(diff_dict):
    """ Recursively convert complex objects in diff_dict to serializable formats. """
    if isinstance(diff_dict, dict):
        for key, value in diff_dict.items():
            diff_dict[key] = json_serializable_diff(value)
    elif not isinstance(diff_dict, (int, float, str, list, dict, bool, type(None))):
        return str(diff_dict)  # Convert non-serializable types to string
    return diff_dict

@app.route('/', methods=['GET', 'POST'])
def index():
    global polish_api_data, santander_api_data
    if request.method == 'POST':
        polish_api_file = request.files.get('polishapi_file')
        santander_files = request.files.getlist('santander_files')

        if polish_api_file:
            polish_api_data = load_yaml_from_file(polish_api_file)

        for file in santander_files:
            if file:
                santander_api_data.append(load_yaml_from_file(file))

        return redirect(url_for('display'))

    return render_template('upload.html')

@app.route('/display')
def display():
    formatted_differences = []
    for santander_api in santander_api_data:
        diff = compare_apis(polish_api_data, santander_api)
        formatted_differences.append(categorize_differences(diff))
    print(formatted_differences)
    return render_template('display.html', differences=formatted_differences)

if __name__ == '__main__':
    app.run(debug=True)





