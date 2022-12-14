import requests
from frontend.config import LOCAL_CACHE_DIR, LOCAL_UPLOADS_DIR, ALLOWED_EXTENSIONS
import os
import base64
from datetime import datetime

def api_call(ipv4, type, commend, params=None, timeout=0.5):
    '''
    This function is used to use the api. \n
    The flag will need to be updated in the future to accommodate different api's.
    '''
    request_url = "http://{}".format(ipv4)
    url = request_url+commend
    print(" - Manager.helper.api_call: ", url)
    if type == "GET":
        try:
            return requests.get(url, params, timeout=0.5)
        except requests.exceptions.RequestException as ce:
            return None
    elif type == "POST":
        try:
            return requests.post(url, params, timeout=0.5)
        except requests.exceptions.RequestException as ce:
            return None

def current_datetime():
    '''
    This function will return a fixed 'datetime' entry which can be inserted into sql.
    '''
    now = datetime.now()
    fixed_now = now.strftime('%Y-%m-%d %H:%M:%S')
    return fixed_now

def api_key_content(filename,decode_value):
    '''
    This function is intented for the api key test function.
    If the decode_value is not None, then it will return the decode value.
    If the decode is None, it will read the image file from the upload dir and encoded it to 64base
    '''
    if decode_value is not None:
        return decode_value
    else:
        final_path = os.path.join(LOCAL_UPLOADS_DIR,filename)
        file = open(final_path,'rb')
        encode_string = base64.b64encode(file.read())
    return encode_string

def api_image_store(file,filename):
    '''
    This function will save the image file from test api to local upload folder
    '''
    final_path = os.path.join(LOCAL_UPLOADS_DIR,filename)
    file.save(final_path)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
