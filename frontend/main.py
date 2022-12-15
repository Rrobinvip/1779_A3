# from crypt import methods
# from fileinput import filename
# from stat import filemode
# from telnetlib import SE
# from traceback import clear_frames

from glob import escape
from tkinter.messagebox import NO
from flask import render_template, url_for, request, redirect
from flask import flash, jsonify
from frontend import app
import requests
import logging
from datetime import datetime
import time
import threading

# Picture upload form
from frontend.form import UploadForm, pictures

# Search form
from frontend.form import SearchForm

# Config form 
from frontend.form import ConfigForm
from frontend.form import ClearForm

# Helper
from frontend.helper import api_call, api_image_store, allowed_file, remove_file, api_call_ipv4, remove_s3_cache

# Encode and decode img
from frontend.helper import write_img_local, image_encoder, current_datetime

# AWS Controller
from frontend.aws import AWSController

# Config
from frontend.config import Config

# Image action form
from frontend.form import ImageActionForm


'''
**IMPORTANT!** instances doesn't updat their status automatically. Call `aws_controller.reload_instance_status()` every time befroe any
operations on instance. Also updating running_instance with `aws_controller.get_ip_address` is mandetory. 
'''
aws_controller = AWSController()
            
@app.route('/')
def main():
    return redirect(url_for("upload_picture"))

@app.route('/upload', methods=["GET", "POST"])
def upload_picture():
    '''
    This function allows user to upload images. 
    It will first save the image to local file system. Then it will encode the image with base64. After encoding, it 
    will post reletive data to memcache for quick access. Image stores in different systems in following methods:
    ### SQL:
        * key
        * filename
        * upload_time

    ### memcache:
        * key
        * base64 encoded value of image
        * upload_time

    If no running instances, all image will only go S3.
    '''
    picture_form = UploadForm()
    filename = None
    key = None
    
    if request.method == "POST" and picture_form.validate_on_submit():
        print(" * Upload init...")
        filename = pictures.save(picture_form.pictures.data)
        key = picture_form.key.data
        
        current_time = current_datetime()
        
        result_s3 = aws_controller.add_file_s3(filename)
        result_ddb = aws_controller.put_item_dynamo(key, filename)
        
        if not result_s3 and not result_ddb:
            print(" - Frontend.main.upload: Upload failed. Abort.")
            flash("Upload failed.")
            # Remove download cache.
            remove_file(filename)
            return redirect(url_for("upload_picture"))
        else:
            print(" - Frontend.main.upload: Upload success.")
            flash("Uplaod success.")
            remove_file(filename)
            return redirect(url_for("upload_picture"))
    
    return render_template("upload.html", form=picture_form)
            
@app.route("/search", methods=["GET", "POST"])
def search_key():
    '''
    This function is used to search for the key entered by the user.

    Workflow: The frontend will first initiate a search with the back end, if the backend returns an error code 400, 
    the frontend will initiate a search to the database. If the backend returns code 200, the frontend will decode the 
    backend image and store it in the local cache. No matter what the result is, if there is an image matching the user's 
    search key, it will be displayed on the web page.

    Image from SQL (filename) will be directly retrieved from `/static/uploads`, image from memcache will be decoded and stored in 
    `/static/local_cache`. Image must be cached locally to be rendered in HTML. 

    If no running instances, all image will be searched in RDS. 
    '''
    search_form = SearchForm()
    filename = None
    upload_time = None
    key = None
    
    print(" * Search init...")
    
    if (request.method == "GET" and "key" in request.args):
        key = escape(request.args.get("key"))
        # Call backend
    elif request.method == "POST" and search_form.validate_on_submit():
        key = search_form.key.data
        
    if key != None:
        filename, upload_time = aws_controller.get_item_dynamo(key)
        if filename == None and upload_time == None:
                flash("No image with this key.")
                if request.method == "GET" and "flag" in request.args:
                    return jsonify({"status":400, "value":None})
        else:
            if request.method == "GET" and "flag" in request.args:
                file_url = 'https://{}.s3.amazonaws.com/{}'.format(Config.BUCKET_NAME, filename)
                return jsonify({"status":200, "value":file_url})
            filename = 'https://{}.s3.amazonaws.com/{}'.format(Config.BUCKET_NAME, filename)
            
        
    return render_template("search.html", 
                        form = search_form, 
                        tag1_selected=True, 
                        filename=filename, 
                        upload_time=upload_time,
                        key=key)
            
@app.route("/allpairs")
def all_pairs():
    '''
    Show all pairs. 
    '''
    data = aws_controller.get_all_item_dynamo()

    image_url = []

    if data:
        for i,item in enumerate(data):
            image_url.append('https://{}.s3.amazonaws.com/{}'.format(Config.BUCKET_NAME, item['filename']['S']))

    return render_template("all_pairs.html", items=data, tag2_selected=True, url_list=image_url)

@app.route("/delete")
def delete_all():
    delete_form = ClearForm()
    
    if delete_form.validate_on_submit():
        aws_controller.delete_all_dynamo()
        aws_controller.clear_s3()
        flash("All data deleted.")
    
    return render_template("delete.html", form2 = delete_form, tag3_selected=True)
    
@app.route("/image/<key>", methods=['GET', 'POST'])
def image_action(key):
    image_action_form = ImageActionForm()
    key = key
    filename = None
    upload_time = None
    result_label = None
    result_facial = None
        
    if key == None:
        return render_template('404.html')
    else:
        filename, upload_time = aws_controller.get_item_dynamo(key)
        if filename == None and upload_time == None:
            return render_template('404.html')
        filename_s3 = 'https://{}.s3.amazonaws.com/{}'.format(Config.BUCKET_NAME, filename)
        
    if image_action_form.validate_on_submit():
        if image_action_form.label.data:
            response_label = aws_controller.get_image_label(filename)
            result_label = aws_controller.unpack_rekognition_response('label', response_label)
            if len(result_label) == 0:
                flash("No labels detected.")
                return redirect(url_for('image_action', key=key))
        else:
            response_facial = aws_controller.get_facial_analysis(filename)
            result_facial = aws_controller.unpack_rekognition_response('facial', response_facial)
            if len(result_facial) == 0:
                flash("Can't apply facial analysis, maybe there has no faces.")
                return redirect(url_for('image_action', key=key))
            
    
    return render_template("image_action.html", 
                           key=key, 
                           filename=filename_s3, 
                           upload_time=upload_time,
                           form = image_action_form,
                           label = result_label,
                           facial = result_facial)
    

@app.route("/api/list_keys", methods= ['POST'])
def api_list_keys():
    '''
    This function is for api test
    It will list all keys in the databases
    '''
    keys = aws_controller.get_all_item_dynamo()
    key_list = []
    if keys:
        for key in keys:
            key_list.append(key['imageKey'])
    return jsonify({
        "status":200,
        "success":"true",
        "keys":key_list
    })

@app.route("/api/key/<key_value>", methods = ['POST'])
def api_key_search(key_value):
    print(" - Frontend.api_key_search: v:key_value", key_value)
    
    data = api_call_ipv4("127.0.0.1:5000/", "GET", "search", {"key":key_value, "flag":1}, timeout=2)

    if data:
        data = data.json()
        value = data["value"]
        return jsonify({
            "success":"true",
            "content":value
        })
    else:
        return jsonify({
            "Success":"false",
            "error":{
                "code":201,
                "message":"Unkown Error"
            }
        })

# @app.route("/api/upload",methods = ['POST'])
# def api_upload():
#     key = request.form.get('key')
#     file = request.files['file']
#     filename = file.filename
