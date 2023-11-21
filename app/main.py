from flask import Flask, render_template, request, redirect, url_for
import yaml

app = Flask(__name__)

# Temporary storage for uploaded file contents
polish_api_data = None
santander_api_data = []

@app.route('/', methods=['GET', 'POST'])
def index():
    global polish_api_data, santander_api_data
    if request.method == 'POST':
        # Handle Polish API file upload
        polish_api_file = request.files.get('polishapi_file')
        if polish_api_file and polish_api_file.filename.endswith('.yaml'):
            polish_api_data = yaml.safe_load(polish_api_file)

        # Handle Santander files upload
        santander_files = request.files.getlist('santander_files')
        for file in santander_files:
            if file and file.filename.endswith('.yaml'):
                santander_api_data.append(yaml.safe_load(file))

        return redirect(url_for('display'))

    return render_template('upload.html')

@app.route('/display')
def display():
    # Convert YAML data to string for display
    polish_api_str = yaml.dump(polish_api_data, default_flow_style=False)
    santander_api_str = [yaml.dump(data, default_flow_style=False) for data in santander_api_data]
    return render_template('display.html', polish_api=polish_api_str, santander_api=santander_api_str)

if __name__ == '__main__':
    app.run(debug=True)




