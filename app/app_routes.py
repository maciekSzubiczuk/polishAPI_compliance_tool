from flask import Blueprint, render_template, request, redirect, url_for, send_file
import yaml
from .api_data_handler import merge_api_data, load_yaml_from_file
from .comparator import find_differences_by_section, find_definitions_differences
from .report_generator import generate_summary, generate_excel_report

# Global variables
polish_api_data = None
santander_api_data = []
xlsx_file_path = 'C:\praca_inzynierska\polishAPI_compliance_tool\\reports\\report.xlsx'
api_sections = {
    'PIS': '/v2_1_1.1/payments',
    'CAF': '/v2_1_1.1/confirmation',
    'AIS': '/v2_1_1.1/accounts',
    'AS': '/v2_1_1.1/auth'
}


routes = Blueprint('routes', __name__)

@routes.route('/', methods=['GET', 'POST'])
def index():
    global polish_api_data, santander_api_data
    if request.method == 'POST':
        polish_api_file = request.files.get('polishapi_file')
        santander_files = request.files.getlist('santander_files')

        if polish_api_file:
            polish_api_data = load_yaml_from_file(polish_api_file)

        if santander_files:
            santander_api_data = merge_api_data(santander_files)

        return redirect(url_for('routes.display'))

    return render_template('upload.html')


@routes.route('/display')
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

    generate_excel_report(all_differences, xlsx_file_path)

    # Calculate counts for additions and deletions
    counts_by_section = {}
    for section, diffs in all_differences.items():
        additions = sum(1 for change in diffs.values() if not change.get('left'))
        deletions = sum(1 for change in diffs.values() if not change.get('right'))
        counts_by_section[section] = {'additions': additions, 'deletions': deletions}

    # Pass these counts along with all_differences to the template
    return render_template('display.html', differences_by_section=all_differences, counts_by_section=counts_by_section)

@routes.route('/download-xlsx')
def download_xlsx():
    return send_file(xlsx_file_path, as_attachment=True, download_name='report.xlsx')