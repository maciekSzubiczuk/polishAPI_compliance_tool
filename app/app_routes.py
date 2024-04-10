from flask import Blueprint, render_template, request, redirect, url_for, send_file, session, jsonify
import yaml
import json  # Add this import at the top of your app_routes.py file
from .api_data_handler import merge_api_data, load_yaml_from_file
from .comparator import find_differences_by_section, find_definitions_differences
from .report_generator import generate_summary, generate_excel_report
import tempfile
import os
from flask import request, redirect, url_for

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
        return render_template('display.html', flattened_differences=[], counts_by_section={})

    # Prepare differences by API section and definitions
    differences_by_section = find_differences_by_section(polish_api_data, santander_api_data, api_sections)
    definitions_differences = find_definitions_differences(polish_api_data, santander_api_data)

    # Initialize counts_by_section with all sections, including "Definitions"
    counts_by_section = {section: {'additions': 0, 'deletions': 0} for section in list(api_sections.keys()) + ['Definitions']}
    
    # Flatten all differences into a single list with unique identifiers
    flattened_differences = []
    unique_id = 0  # Start an identifier to ensure each item is unique

    for section, diffs in differences_by_section.items():
        for path, change in diffs.items():
            flattened_differences.append({
                'id': unique_id,
                'section': section,
                'path': path,
                'left': yaml.dump(change['left'], default_flow_style=False, sort_keys=False) if change['left'] else '',
                'right': yaml.dump(change['right'], default_flow_style=False, sort_keys=False) if change['right'] else '',
                'summary': generate_summary(change)
            })
            # Update counts
            if change['left']: counts_by_section[section]['deletions'] += 1
            if change['right']: counts_by_section[section]['additions'] += 1
            unique_id += 1

    # Add definitions differences with unique identifiers
    for key, change in definitions_differences.items():
        flattened_differences.append({
            'id': unique_id,
            'section': 'Definitions',
            'path': key,
            'left': yaml.dump(change['left'], default_flow_style=False, sort_keys=False) if change['left'] else '',
            'right': yaml.dump(change['right'], default_flow_style=False, sort_keys=False) if change['right'] else '',
            'summary': generate_summary(change)
        })
        # Update counts for "Definitions"
        if change['left']: counts_by_section['Definitions']['deletions'] += 1
        if change['right']: counts_by_section['Definitions']['additions'] += 1
        unique_id += 1

    # Now pass this flattened list and counts to the template
    return render_template('display.html', 
                       flattened_differences=flattened_differences, 
                       counts_by_section=counts_by_section,
                       api_sections=api_sections)  # Add this line





field_mapping = {
    "include": "include",
    "status": "status",
    "section": "section",
    "path": "path",
    "left": "left",
    "right": "right",
    "summary": "summary",
}


@routes.route('/save-differences', methods=['POST'])
def save_differences():
  form_data = request.form.to_dict()
  differences_data = {}
  for key, value in form_data.items():
    if any(field_name in key for field_name in field_mapping):
      index = key.split('[')[1].rstrip(']')
      if index not in differences_data:
        differences_data[index] = {field: '' for field in field_mapping.values()}
      differences_data[index][field_mapping[key.split('[')[0]]] = value


  # Filter included differences
  included_differences = []
  for data in differences_data.values():
    if 'include' in data and data['include'] == 'on':
        included_differences.append(data)


  # Create temporary file and write JSON data
  with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
    json.dump(included_differences, temp_file)
    temp_file_path = temp_file.name  # Store the temporary file path

  # No need to store data in session (commented out)
  # session['included_differences'] = json.dumps(included_differences)  

  # Redirect to download route with temporary file path as argument
  return redirect(url_for('routes.download_xlsx', temp_file_path=temp_file_path))




@routes.route('/download-xlsx')
def download_xlsx():
  # Retrieve temporary file path from request argument
  temp_file_path = request.args.get('temp_file_path')

  # Check if data is present
  if not temp_file_path or not os.path.exists(temp_file_path):
    return "No differences found for download", 404

  try:
    # Read JSON data from temporary file
    with open(temp_file_path, 'r') as temp_file:
      formatted_differences = json.load(temp_file)

    # Delete temporary file after reading
    os.remove(temp_file_path)

  except (json.JSONDecodeError, FileNotFoundError):
    # Handle potential errors (decoding or file not found)
    return "Error processing differences. Please try again.", 500

  # Pass data to Excel generation logic (assuming generate_excel_report exists)
  generate_excel_report(formatted_differences, xlsx_file_path)

  # Return the generated Excel file
  return send_file(xlsx_file_path, as_attachment=True, download_name='report.xlsx')



