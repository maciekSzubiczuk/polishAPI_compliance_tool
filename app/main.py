from flask import Flask, render_template, request
import os
import yaml

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'No file part'
    file = request.files['file']
    if file.filename == '':
        return 'No selected file'
    if file and file.filename.endswith('.yaml'):
        # Read and parse the YAML file
        content = yaml.safe_load(file)
        # Pass the parsed content to a new template
        return render_template('display.html', content=content)
    else:
        return 'Invalid file format'

if __name__ == '__main__':
    app.run(debug=True)
