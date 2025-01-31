from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
import os
import json
import pyshark

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a secure secret key

# Configure upload and converted folders
UPLOAD_FOLDER = './uploads'
CONVERTED_FOLDER = './converted_json'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['CONVERTED_FOLDER'] = CONVERTED_FOLDER

# Ensure the folders exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CONVERTED_FOLDER, exist_ok=True)

# MongoDB connection
from pymongo import MongoClient

client = MongoClient('mongodb://localhost:27017')
db = client['template_db']  # Ensure you're using the correct database

# Change the collection name to 'templates' (instead of 'temp')
templates_collection = db['templates']

# Insert a template (for testing purposes)
template_data = {
    'template_name': 'Test Template',
    'keyValuePairs': [
        {'key': 'key1', 'value': 'value1'},
        {'key': 'key2', 'value': 'value2'}
    ],
    'createdAt': '07-01-2025'
}

# templates_collection.insert_one(template_data)

@app.route('/save_template', methods=['POST'])
def save_template():
    # This is just an example of saving a template
    template_name = 'Test Template'
    key_value_pairs = [
        {'key': 'key1', 'value': 'value1'},
        {'key': 'key2', 'value': 'value2'}
    ]

    template_data = {
        'template_name': template_name,
        'keyValuePairs': key_value_pairs,
        'createdAt': '2024-12-29'  # You can use a timestamp here
    }

    # Insert into the 'templates' collection
    try:
        result = templates_collection.insert_one(template_data)
        return jsonify({'message': 'Template saved successfully', 'id': str(result.inserted_id)}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@app.route('/save_configuration', methods=['POST'])
def save_configuration():
    # Retrieve the template name
    template_name = request.form.get('template_name')

    # Retrieve key-value pairs
    key_value_pairs = []
    key = request.form.get('key')
    value = request.form.get('value')
    if key and value:
        key_value_pairs.append({'key': key, 'value': value})

    # Prepare the data to be saved
    template_data = {
        'template_name': template_name,
        'keyValuePairs': key_value_pairs,
        'createdAt': datetime.now()  # Use current date and time
    }

    # Save to MongoDB
    try:
        templates_collection.insert_one(template_data)
        flash('Configuration saved successfully!', 'success')
        return redirect(url_for('some_route'))  # Redirect to a relevant page
    except Exception as e:
        flash(f'Error saving configuration: {e}', 'error')
        return redirect(url_for('validate'))  # Redirect back to the validate page
@app.route('/')
def upload_form():
    return render_template('upload.html')

# 
@app.route('/', methods=['POST'])
def upload_file():
    username = request.form['username']
    file = request.files['file']

    if file and file.filename.endswith('.pcap'):
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)

        # Convert PCAP to JSON
        json_filename = f"{username}_{file.filename.replace('.pcap', '.json')}"
        json_filepath = os.path.join(app.config['CONVERTED_FOLDER'], json_filename)

        try:
            # Convert file synchronously on the main thread
            convert_pcap_to_json(file_path, json_filepath)
            flash('File uploaded and converted successfully', 'success')
        except Exception as e:
            flash(f'Error during conversion: {e}', 'error')
            return redirect(url_for('upload_form'))

        session['success_message'] = 'File uploaded and converted successfully'
        session['selected_file'] = json_filename
        
        # Redirect directly to search_results with the converted file
        return redirect(url_for('search_results', filename=json_filename))

    flash('Invalid file type, only .pcap files are allowed', 'error')
    return redirect(url_for('upload_form'))

# Modify the search_results route to use the filename directly from the URL
@app.route('/search_results/<filename>')
def search_results(filename):
    file_path = os.path.join(app.config['CONVERTED_FOLDER'], filename)

    if not os.path.exists(file_path):
        flash('File not found!', 'error')
        return redirect(url_for('upload_form'))  # Redirect back to upload if file doesn't exist

    with open(file_path) as f:
        file_data = json.load(f)

    # Retrieve template_name from session or set a default
    template_name = session.get('template_name', f"Template_{filename}")
    session['template_name'] = template_name

    return render_template('search_results.html', filename=filename, json_data=file_data, template_name=template_name)


# @app.route('/view_files', methods=['GET', 'POST'])
# def view_files():
#     converted_files = [
#         file for file in os.listdir(app.config['CONVERTED_FOLDER']) if file.endswith('.json')
#     ]

#     if request.method == 'POST':
#         selected_file = request.form.get('selected_file')
#         session['selected_file'] = selected_file
#         return redirect(url_for('search_results', filename=selected_file))

#     return render_template('view_files.html', files=converted_files)

# @app.route('/search_results/<filename>')
# def search_results(filename):
#     file_path = os.path.join(app.config['CONVERTED_FOLDER'], filename)

#     if not os.path.exists(file_path):
#         flash('File not found!', 'error')
#         return redirect(url_for('view_files'))

#     with open(file_path) as f:
#         file_data = json.load(f)

#     # Retrieve template_name from session or set a default
#     template_name = session.get('template_name', f"Template_{filename}")
#     session['template_name'] = template_name

#     return render_template('search_results.html', filename=filename, json_data=file_data, template_name=template_name)



@app.route('/api/search_keys', methods=['GET'])
def search_keys():
    query = request.args.get('q', '').lower()
    filename = session.get('selected_file')
    file_path = os.path.join(app.config['CONVERTED_FOLDER'], filename)


    if not os.path.exists(file_path):
        return jsonify([])

    with open(file_path) as f:
        file_data = json.load(f)

    suggestions = search_json(file_data, query)
    return jsonify(suggestions)

@app.route('/api/search_suggestions', methods=['GET'])
def search_suggestions():
    query = request.args.get('q', '').lower()
    files = [file for file in os.listdir(app.config['CONVERTED_FOLDER']) if file.endswith('.json')]

    suggestions = []
    for file in files:
        if query in file.lower():
            suggestions.append({"filename": file})

    return jsonify(suggestions)

def search_json(data, query):
    matches = []
    if isinstance(data, dict):
        for key, value in data.items():
            if query in key.lower():
                matches.append({"key": key, "value": value})
            if isinstance(value, (dict, list)):
                matches.extend(search_json(value, query))
    elif isinstance(data, list):
        for item in data:
            matches.extend(search_json(item, query))
    return matches

def convert_pcap_to_json(input_pcap_path, output_json_path):
    """Convert a PCAP file to a JSON file using PyShark."""
    packets = pyshark.FileCapture(input_pcap_path)
    data = []

    # Extract packet details
    for packet in packets:
        packet_dict = {}
        for layer in packet.layers:
            packet_dict[layer.layer_name] = layer._all_fields
        data.append(packet_dict)

    with open(output_json_path, 'w') as json_file:
        json.dump(data, json_file, indent=4)

    packets.close()

@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, post-check=0, pre-check=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.before_request
def initialize_session():
    if 'validated_pairs' not in session:
        session['validated_pairs'] = []
    else:
        try:
            session['validated_pairs'] = json.loads(json.dumps(session['validated_pairs']))
        except json.JSONDecodeError:
            session['validated_pairs'] = []

@app.route('/validate', methods=['GET'])
def validate():
    key = request.args.get('key')
    value = request.args.get('value')
    session['validated_pairs'] = session.get('validated_pairs', []) + [{'key': key, 'value': value}]
    app.logger.debug(f"Validated pairs: {session['validated_pairs']}")
    return render_template('Validate.html', key=key, value=value)


@app.route('/delete', methods=['POST'])
def delete_entry():
    if 'selected_pairs' in session:
        selected_pairs = session['selected_pairs']
        index = int(request.form.get('index')) - 1  # Convert index to 0-based
        if 0 <= index < len(selected_pairs):
            del selected_pairs[index]
            session['selected_pairs'] = selected_pairs  # Save back to session
            flash('Pair deleted successfully!', 'success')
        else:
            flash('Invalid index!', 'error')

    return redirect(url_for('validate'))

@app.route('/template_structure', methods=['GET', 'POST'])
def template_structure():
    
    templates_folder = './templates_storage'
    os.makedirs(templates_folder, exist_ok=True)
    

    # Initialize templates variable
    templates = []

    if request.method == 'POST':
    
        template_name = session.get('template_name')
        
        validated_pairs = session.get('validated_pairs', [])

        # Debugging: Check the session data
        app.logger.debug(f"Template Name: {template_name}")
    
        app.logger.debug(f"Validated Pairs: {validated_pairs}")

        if not template_name:
            flash('Template name is missing!', 'error')
            print(6)
            return redirect(url_for('template_structure'))
        print(7)
        if not validated_pairs:
            print(8)
            flash('No validated pairs found!', 'error')
            return redirect(url_for('template_structure'))
# print(8)
        # Save the template data to MongoDB
        template_data = {'name': template_name, 'data': validated_pairs}
        try:
            
            # Insert into MongoDB (template_db -> templates collection)
          templates_collection.insert_one(template_data)
    
          flash('Template saved successfully in MongoDB!', 'success')
          app.logger.debug(f"Template saved to MongoDB: {template_data}")
        except Exception as e:
            flash(f'Error saving template to MongoDB: {e}', 'error')
            app.logger.error(f"Error saving template to MongoDB: {e}")

    # Load templates for display from MongoDB
    try:
        templates = list(templates_collection.find())
    except Exception as e:
        flash(f'Error loading templates from MongoDB: {e}', 'error')
        app.logger.error(f'Error loading templates: {e}')

    return render_template('template_structure.html', templates=templates)



   
@app.route('/delete_template', methods=['POST'])
def delete_template():
    template_name = request.form.get('template_name')
    template_folder = './templates_storage'
    templates = []
    for file_name in os.listdir(template_folder):
        if file_name.endswith('.json'): 
            try:
                with open(os.path.join(template_folder, file_name)) as f:
                    templates.append(json.load(f))
            except json.JSONDecodeError:
                flash(f'Error loading template: {file_name}', 'error')

    templates = [t for t in templates if t['name'] != template_name]
    flash('Template deleted successfully!', 'success')
    return redirect(url_for('template_structure'))

@app.route('/templates', methods=['GET'])
def get_templates():
    return jsonify(templates)


  # Store in session
        # Existing code...
# @app.route('/save_test', methods=['GET', 'POST'])
# def save_test():
#     if request.method == 'POST':
#         template_data = {'name': 'Test Template', 'data': [{'key': 'testKey', 'value': 'testValue'}]}
#         template_path = './templates_storage/Test_Template.json'
#         try:
#             with open(template_path, 'w') as f:
#                 json.dump(template_data, f, indent=4)
#             flash('Test template saved successfully!', 'success')
#         except Exception as e:
#             flash(f'Error saving test template: {e}', 'error')
#         return redirect(url_for('template_structure'))
    
#     return render_template('template_structure.html')


#   @app.route('/save_test', methods=['GET', 'POST'])
# def save_test():
#     print("Save Test Route Triggered")  # Debug line to confirm route is accessed
#     if request.method == 'POST':
#         template_data = {'name': 'Test Template', 'data': [{'key': 'testKey', 'value': 'testValue'}]}
        
#         # Full absolute path
#         template_path = os.path.abspath('./templates_storage/Test_Template.json')
#         print(f"Saving template at: {template_path}")
        
#         try:
#             with open(template_path, 'w') as f:
#                 json.dump(template_data, f, indent=4)
#             flash('Test template saved successfully!', 'success')
#         except Exception as e:
#             flash(f'Error saving test template: {e}', 'error')
        
#         return redirect(url_for('template_structure'))
    
#     return render_template('template_structure.html')



    # Existing code...
if __name__ == '__main__':
    app.run(debug=True, )
