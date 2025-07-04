from flask import Flask, request, send_file
from werkzeug.utils import secure_filename
import os
import random
import string
import csv
from datetime import datetime
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'processed'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Convert special characters (excluding hyphen) to space
def scramble_special_char(c):
    if c in string.ascii_letters or c.isdigit() or c == '-':
        return c
    return ' '

# Simple Replacement with user-defined repChar and repDig
def simple_replacement(text, data_type, repChar, repDig):
    result = ''
    for c in text:
        if c.isalpha() and data_type in ['String', 'Both']:
            result += repChar
        elif c.isdigit() and data_type in ['Number', 'Both']:
            result += repDig
        elif c != '-' and not c.isalnum():
            result += scramble_special_char(c)
        else:
            result += c
    return result

# Random Character Replacement
def random_char_replacement(text, data_type):
    result = ''
    for c in text:
        if c.isalpha() and data_type in ['String', 'Both']:
            result += random.choice(string.ascii_letters)
        elif c.isdigit() and data_type in ['Number', 'Both']:
            result += random.choice(string.digits)
        elif c != '-' and not c.isalnum():
            result += scramble_special_char(c)
        else:
            result += c
    return result

# Incremental Number Scramble
def incremental_scramble(text, data_type):
    result = ''
    for c in text:
        if c.isdigit() and data_type in ['Number', 'Both']:
            result += str((int(c) + random.randint(1, 9)) % 10)
        elif c != '-' and not c.isalnum():
            result += scramble_special_char(c)
        else:
            result += c
    return result

# File Processing Function
def scramble_file(uploaded_file, filetype, start_pos, end_pos, data_type, scramble_func, has_header=False):
    filename = secure_filename(uploaded_file.filename)
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    uploaded_file.save(file_path)

    now = datetime.now()
    out_filename = f"{os.path.splitext(filename)[0]}_{now.strftime('%Y%m%d_%H%M%S')}_PROCESSED.{filetype.lower()}"
    out_path = os.path.join(OUTPUT_FOLDER, out_filename)

    if filetype == 'TXT':
        with open(file_path, 'r', encoding='utf-8') as fin, open(out_path, 'w', encoding='utf-8') as fout:
            for i, line in enumerate(fin):
                line = line.rstrip('\n')

                # Skip scrambling for first line if header is True
                if i == 0 and has_header:
                    fout.write(line + '\n')
                    continue

                # Continue if line is shorter than start position
                if len(line) < start_pos:
                    fout.write(line + '\n')
                    continue

                actual_end = end_pos if end_pos is not None else len(line)
                actual_end = min(actual_end, len(line))
                scrambled = (
                    line[:start_pos - 1] +
                    scramble_func(line[start_pos - 1:actual_end], data_type) +
                    line[actual_end:]
                )
                fout.write(scrambled + '\n')

    elif filetype == 'CSV':
        column_index = start_pos - 1
        with open(file_path, 'r', newline='', encoding='utf-8') as fin, open(out_path, 'w', newline='', encoding='utf-8') as fout:
            reader = csv.reader(fin)
            writer = csv.writer(fout)
            for row_index, row in enumerate(reader):

                # Skip scrambling for first row if header is True
                if has_header and row_index == 0:
                    writer.writerow(row)
                    continue
                
                if len(row) > column_index:
                    row[column_index] = scramble_func(row[column_index], data_type)
                writer.writerow(row)

    return out_path


@app.route('/')
def index():
    return {"error": "empty api endpoint"}, 400


@app.route('/scramble/<method>', methods=['POST'])
def scramble(method):
    if 'source_file' not in request.files:
        return 'Missing file input', 400

    uploaded_file = request.files['source_file']
    if uploaded_file.filename == '':
        return 'Missing file name', 400

    
    try:
        
        filetype = request.form['file_type']
        start_pos = int(request.form['start_pos'])
        end_pos = int(request.form['end_pos']) if filetype == 'TXT' and request.form.get('end_pos') else None
        data_type = request.form['data_type']
        has_header = request.form.get('contains_header', 'false').lower() == 'true'
        
        # Default placeholders for repChar and repDig in case 'simple' is selected
        repChar = request.form.get('repChar')
        repDig = request.form.get('repDig')

        # Validation
        if filetype == 'CSV' and start_pos < 1:
            return {"error": "CSV column number must be at least 1."}, 400
        if filetype == 'TXT' and end_pos is not None and start_pos > end_pos:
            return {"error": "Start position must be less than or equal to end position."}, 400
        if method == 'incremental' and data_type != 'Number':
            return {"error": "Incremental scramble supports only Number data type."}, 400

        scramble_methods = {
            'simple': lambda text, dtype: simple_replacement(text, dtype, repChar, repDig),
            'random': random_char_replacement,
            'incremental': incremental_scramble
        }
        scramble_func = scramble_methods.get(method)
        if not scramble_func:
            return {"error": f"Unknown scramble method: {method}"}, 400

        output_path = scramble_file(uploaded_file, filetype, start_pos, end_pos, data_type, scramble_func, has_header)
        return send_file(output_path, as_attachment=True)

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return f'Error processing file: {str(e)}', 500


if __name__ == '__main__':
    app.run(debug=True)