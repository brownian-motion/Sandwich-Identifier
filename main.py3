import os
import tempfile
import json
import io
from google.cloud import vision
from flask import make_response

def handle_http_request(request):
    """
    Handles the actual http connection, setting Cross-Origin headers as needed.
    """
    if request.method == "OPTIONS": # this HTTP method is used to check Cross-Origin headers
        res = make_response("") # don't do any work
    else: # normal request
        res = make_response(parse_request(request))
    res.headers.set("Access-Control-Allow-Origin", "*")
    res.headers.set("Access-Control-Allow-Methods", "GET");
    res.headers.set("Access-Control-Allow-Headers", "Content-Type");
    res.headers.set("Access-Control-Max-Age", "3600");
    return res


def parse_request(request):
    """ Parses a 'multipart/form-data' upload request and executes the function.
    Args:
        request (flask.Request): The request object.
    Returns:
        The response text, or any set of values that can be turned into a
         Response object using `make_response`
        <http://flask.pocoo.org/docs/0.12/api/#flask.Flask.make_response>.
    """

    file = extract_file_parameter(request, "image")
    if file == None:
        return json.dumps({'success': False, 'message': 'Error: No image uploaded!'})

    file_path = save_temporary_file(file, "image")
    
    sandwich_labels = get_sandwich_labels(detect_labels(file_path))

    # Clear temporary directory
    os.remove(file_path)

    # get the max score for all of the sandwich, or 0 if there are no labels
    max_score = max([label['score'] for label in sandwich_labels], default=0)

    return json.dumps({'success': True, 'labels': sandwich_labels, 'score': max_score, 'message': get_confidence_message(max_score)})

def get_confidence_message(confidence):
    if confidence >= 0.8:
        return "That is a sandwich!"
    elif confidence >= 0.5:
        return "That is probably a sandwich."
    elif confidence >= 0.2:
        return "That probably is not a sandwich."
    else:
        return "That is not a sandwich."
# Helper function that computes the filepath to save files to
def get_file_path(filename):
    # Note: tempfile.gettempdir() points to an in-memory file system
    # on GCF. Thus, any files in it must fit in the instance's memory.
    file_name = secure_filename(filename)
    return os.path.join(tempfile.gettempdir(), file_name)

def secure_filename(filename):
    keepcharacters = (' ','.','_')
    return "".join(c for c in filename if c.isalnum() or c in keepcharacters).rstrip()

def save_temporary_file(file, file_name):
    file_path = get_file_path(file_name)
    file.save(file_path)
    return file_path

def extract_file_parameter(request, param_name):
    files = request.files.to_dict()
    if "image" not in files:
        return None
    return files["image"]

def detect_labels(path):
    """Detects labels in the file."""
    print('Connecting to Vision client')
    client = vision.ImageAnnotatorClient()

    print('Loading file %s' % path)
    print('    size %d' % os.stat(path).st_size)
    with io.open(path, 'rb') as image_file:
        content = image_file.read()

    image = vision.types.Image(content=content)

    print('Detecting labels')
    response = client.label_detection(image=image)
    return response.label_annotations

def get_sandwich_labels(labels):
    print('Finding "Sandwich" labels')
    return [normalize_annotation(label) for label in labels if ("sandwich" in label.description)]

def normalize_annotation(annotation):
    """Turns a complex EntityAnnotation object into something json-printable"""
    print('Normalizing annotations')
    return {'description': annotation.description, 'score': annotation.score}
