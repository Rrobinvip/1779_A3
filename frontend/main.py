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

# Data model
from frontend.data import Data

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
from manager_app.config import Config

# Hash Mapper
from frontend.pool_hashing import PoolHashingAllocator

# Get master ip
from ec2_metadata import ec2_metadata

# Get cloudwatch client
from auto_scaler.cloudwatch import CloudWatch
cloudwatch = CloudWatch()

'''
**IMPORTANT!** instances doesn't updat their status automatically. Call `aws_controller.reload_instance_status()` every time befroe any
operations on instance. Also updating running_instance with `aws_controller.get_ip_address` is mandetory. 
'''
aws_controller = AWSController()
sql_connection = Data()

running_instance = aws_controller.get_ip_address()
hash_mapper = PoolHashingAllocator(len(running_instance))
            
@app.route('/')
def main():
    return redirect(url_for("upload_picture"))

@app.route('/go_manager')
def go_manager():
    return redirect('/manager')

#This function is front back call example
@app.route('/test')
def test():
    # It's probably not working. 
    #call the backend url
    request = requests.get("http://127.0.0.1:5000/backend/test",timeout = 5)
    #parse the json file
    result = request.json()
    #access content in json file
    print(result["success"])
    print(result["status"])
    print(result["message"])
    return "This is front end test"
    
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

    running_instance = aws_controller.get_ip_address()
    hash_mapper.set_number_nodes(len(running_instance))

    result = None

    if request.method == "POST" and picture_form.validate_on_submit():
        print(" * Upload init...")
        filename = pictures.save(picture_form.pictures.data)

        # # Make filename unique
        # date_prefix = current_datetime()
        # filename = date_prefix+filename

        key = picture_form.key.data

        instance_index_to_assign_key_value, partition = hash_mapper.get_hash_region(key)

        # Upload the file to s3.
        aws_controller.add_file_s3(filename)

        # Frontend will encode the image into a string, and pass it to backend as a value. 
        value = image_encoder(filename, 'uploads')
        upload_time = current_datetime()
        parms = {"key":key, "value":value, "upload_time":upload_time}

        # result = api_call("POST", "put", parms)
        # Test locally with above, with nodes with below.
        if instance_index_to_assign_key_value != -1:
            print(" - Frontend.main.upload : index of instance to upload at {} in {}, partition {}".format(instance_index_to_assign_key_value, running_instance, partition))

            running_instance_ips = list(running_instance.values())
            connection_test_result = api_call_ipv4(running_instance_ips[instance_index_to_assign_key_value]+":5000", "GET", "test")
            if connection_test_result != None and connection_test_result.status_code == 200:
                print(" - Frontend.main.upload_picture : connection to desire instance at {} success, start to upload picture.".format(running_instance_ips[instance_index_to_assign_key_value]))
                result = api_call_ipv4(running_instance_ips[instance_index_to_assign_key_value]+":5000", "POST", "put", parms)
            else:
                print(" - Frontend.main.upload_picture : Cannot establish connection to {}, abort.".format(running_instance_ips[instance_index_to_assign_key_value]))
        else:
            print(" - Frontend.main.upload_picture : No running instances. Image will go to S3. # running instance: {}".format(len(running_instance)))

        if result != None and result.status_code == 200:
            print(" - Frontend.main.upload_picture : backend stores image into memcache.")
        else:
            print(" - Frontend.main.upload_picture : memcache failed to store image for some reason. Check message from 'backend.memcache.*' for more help. Image will still be stored in S3. ")

        # After update it with the memcache, frontend will add filename and key into db. Upload is always success because it will go to S3 eventually. 
        flash("Upload success")
        print(filename, key)
        sql_connection.add_entry(key, filename)

        # Remove file from s3
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
    cache_flag = False

    running_instance = aws_controller.get_ip_address()
    hash_mapper.set_number_nodes(len(running_instance))
    instance_index_to_search = None

    data = None
    connection_test_result = None

    print(" * Search init...")
 
    # Get key through different approaches. 
    if (request.method == "GET" and "key" in request.args):
        key = escape(request.args.get("key"))
        # Call backend
    elif request.method == "POST" and search_form.validate_on_submit():
        key = search_form.key.data
    
    if key != None:
        print(" - Frontend.main.search_key : Searching in memcache..")
        instance_index_to_search, partition = hash_mapper.get_hash_region(key)

        # data = api_call("GET", "get", {"key":key})
        if instance_index_to_search != -1:
            running_instance_ips = list(running_instance.values())
            print(" - Frontend.main.search : index of instance to search at {} in {}, partition {}".format(instance_index_to_search, running_instance, partition))
            connection_test_result = api_call_ipv4(running_instance_ips[instance_index_to_search]+":5000", "GET", "test")
            if connection_test_result.status_code == 200:
                print(" - Frontend.main.search : connection to desire instance at {} success, start to search picture.".format(running_instance_ips[instance_index_to_search]))
                data = api_call_ipv4(running_instance_ips[instance_index_to_search]+":5000", "GET", "get", {"key":key})
            else:
                print(" - Frontend.main.search : Cannot establish connection to {}, abort.".format(running_instance_ips[instance_index_to_search]))
        else:
            print(" - Frontend.main.search: No running instances, search in DB only.")
        # To use nodes.
        # data = api_call_ipv4(running_instance[instance_index_to_search], "GET", "get", {"key":key})

        # If the backend misses, look up the database. If the backend hits, decrypt the image and store it
        if data != None and data.status_code == 400:
            print("\t Backend doesn't hold this value, try search in DB..")
            data = sql_connection.search_key(key)
            if len(data) == 0:
                print("\t DB doesn't hold this value. Search end.")
                flash("No image with this key.")
                if request.method == "GET" and "flag" in request.args:
                    return jsonify({"value":None}), 400
            else:
                filename = data[0][2]
                upload_time = data[0][3]
                print("Filename: {} upload_time: {}".format(filename, upload_time))

                aws_controller.download_file(filename)

                # When data is retrieved from DB, add it to memcache.
                value = image_encoder(filename, 's3')
                parms = {"key":key, "value":value, "upload_time":upload_time}
                result = api_call_ipv4(running_instance_ips[instance_index_to_search]+":5000", "POST", "put", parms)
                
                remove_s3_cache(filename)
                
                filename = 'https://{}.s3.amazonaws.com/{}'.format(Config.BUCKET_NAME, filename)
                
                if request.method == "GET" and "flag" in request.args:
                    return jsonify({"value":filename}), 200

                if result != None and result.status_code == 200:
                    print(" - Frontend: backend stores image into memcache.")
                else:
                    print(" - Frontend: memcache failed to store image for some reason. Check message from 'backend.memcache.*' for more help. Image will still be stored locally. ")

        # In case of no running instance, directly search in DB. 
        elif data == None:
            print("\t No instance running, try search in DB..")
            data = sql_connection.search_key(key)

            if len(data) == 0:
                print("\t DB doesn't hold this value. Search end.")
                flash("No image with this key.")
                if request.method == "GET" and "flag" in request.args:
                    return jsonify({"value":None}), 400
            else:
                filename = data[0][2]
                upload_time = data[0][3]
                print("Filename: {} upload_time: {}".format(filename, upload_time))
                filename = 'https://{}.s3.amazonaws.com/{}'.format(Config.BUCKET_NAME, filename)
                
                if request.method == "GET" and "flag" in request.args:
                    return jsonify({"value":filename}), 200

        elif data != None and data.status_code == 200:
            data = data.json()
            value = data["value"]
            upload_time = data["upload_time"]
            
            if request.method == "GET" and "flag" in request.args:
                    return jsonify({"value":value}), 200

            # Add datetime prefix to image cache file.
            date_prefix = current_datetime()
            print(" - Frontend.main.search_key v:data_prefix ",date_prefix)
            filename = "image_local_"+key+"_"+date_prefix+".png"

            write_img_local(filename, value)
            cache_flag = True
            print(" - Frontend.main.search_key: v:Filename: {} v:upload_time: {}".format(filename, upload_time))
    
    return render_template("search.html", 
                           form = search_form, 
                           tag1_selected=True, 
                           filename=filename, 
                           upload_time=upload_time,
                           key=key,
                           cache_flag=cache_flag)

@app.route("/allpairs")
def all_pairs():
    '''
    Show all pairs. 
    '''
    data = sql_connection.inspect_all_entries()

    image_url = []

    for i,item in enumerate(data):
        image_url.append('https://{}.s3.amazonaws.com/{}'.format(Config.BUCKET_NAME, data[i][2]))

    return render_template("all_pairs.html", items=data, tag2_selected=True, url_list=image_url)


@app.route("/config", methods=["GET", "POST"])
def memcache_config():
    '''
    This function basically has two parts. First for updating memcache size and replacement policy, another for clear the memcache. 

    Two parts are triggered with different form. 
    '''
    config_form = ConfigForm()
    clear_form = ClearForm()

    # Give a default memcache size and replacement_policy, just in case database has nothing. 
    size = 100.0
    choice = 1

    if request.method == "GET" and "size" in request.args and "policy" in request.args:
        size = escape(request.args.get("size"))
        choice = escape(request.args.get("choice", type=int))
        parms = {"size":size, "replacement_policy":choice}
        result = api_call("GET", "config", parms)

        if result.status_code == 200:
            flash("Update success")
        else: 
            flash("Update failed")
        return redirect(url_for("memcache_config"))


    elif request.method == "POST" and config_form.validate_on_submit():
        size = config_form.size.data
        choice = config_form.replacement_policy.data

        parms = {"size":size, "replacement_policy":choice}
        result = api_call("GET", "config", parms)

        if result.status_code == 200:
            flash("Update success")
        else: 
            flash("Update failed")
        return redirect(url_for("memcache_config"))

    if request.method == "POST" and clear_form.validate_on_submit():
        result = api_call("GET", "clear")

        if result.status_code == 200:
            flash("memcache cleared")
        else: 
            flash("Update failed")
        return redirect(url_for("memcache_config"))
        
    return render_template("config.html", form1=config_form, form2=clear_form, tag3_selected=True)

@app.route("/status")
def memcache_status():
    '''
    Get all memcache status. 

    If data is empty, a dummy data will be given.
    '''
    data = sql_connection.get_stat_data()
    if data == None:
        data = [[0,0,0,0,0,0]]

    return render_template("status.html", items=data, tag4_selected=True)

@app.route('/api/pool_size_notify', methods=['GET'])
def pool_size_update():
    '''
    This method allows frontend to be notified when pool size changed. 
    '''
    print(" - Frontend.main : pools_size_update called.")
    # print(" - Frontend.main : pool_size_update, current running ips:{}".format(aws_controller.get_ip_address()))

    if request.method == 'GET' and 'size' in request.args:
        size = int(request.args.get('size'))
        if size < 0 or size > 8:
            print(" - Frontend.main : Incoming size incorrect")
            return jsonify({"Message":"Operation failed"}), 400
        
        # Obtain a new list of running instance is ignored here because instance doesn't boot or stop that quick.
        # Pending instances will not be counted as running instances.
        hash_mapper.set_number_nodes(size)
        return jsonify({"Message":"Size updated"}), 200

    return jsonify({"Message":"Operation failed"}), 400

@app.route("/api/list_keys", methods= ['POST'])
def api_list_keys():
    '''
    This function is for api test
    It will list all keys in the databases
    '''
    keys = sql_connection.get_keys()
    key_list = []
    if keys:
        for key in keys:
            key_list.append(key[0])
    return jsonify({
        "success":"true",
        "keys":key_list
    })

@app.route("/api/key/<key_value>", methods = ['POST'])
def api_key_search(key_value):
    #call backend
    print(" - Frontend.api_key_search: v:key_value", key_value)
    
    data = api_call_ipv4("127.0.0.1:5000/", "GET", "search", {"key":key_value, "flag":1}, timeout=2)

    #If the backend misses, look up the database
    if data == None or (data != None and data.status_code) == 400:
        result = sql_connection.search_key(key_value)
        #if the key does not exist in database, return error message
        if len(result) == 0:
            return jsonify({
                "success":"false",
                "error":{
                    "code":400,
                    "message":"Unknown Key Value"
                }
            })
        #if the key exists in database, retrive it from local file system
        else:
            filename = result[0][2]

            # Download file from s3.
            aws_controller.download_file(filename)

            content = image_encoder(filename, 's3')
            content = content.decode()
            return jsonify({
                "success":"true",
                "content":content
            })
    elif data.status_code == 200:
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

@app.route("/api/upload",methods = ['POST'])
def api_upload():
    key = request.form.get('key')
    file = request.files['file']
    filename = file.filename
    #if the request does not give file then return error code and message
    if filename == '':
        return jsonify({
            "success":"false",
            "error":{
                "code":400,
                "message":"No file given"
            }
        })
    
    if file and allowed_file(filename):
    #if we have the file then store the file to local
        api_image_store(file,filename)
        
        #front will encode the image and pass it to backend
        value = image_encoder(filename, 'uploads')
        upload_time = current_datetime()
        parms = {"key":key,"value":value,"upload_time":upload_time}
        
        running_instance = aws_controller.get_ip_address()
        hash_mapper.set_number_nodes(len(running_instance))
        
        instance_index_to_assign_key_value, partition = hash_mapper.get_hash_region(key)

        # Upload the file to s3.
        aws_controller.add_file_s3(filename)
        
        if instance_index_to_assign_key_value != -1:
            print(" - Frontend.main.upload api : index of instance to upload at {} in {}, partition {}".format(instance_index_to_assign_key_value, running_instance, partition))

            running_instance_ips = list(running_instance.values())
            connection_test_result = api_call_ipv4(running_instance_ips[instance_index_to_assign_key_value]+":5000", "GET", "test")
            if connection_test_result != None and connection_test_result.status_code == 200:
                print(" - Frontend.main.upload_picture api : connection to desire instance at {} success, start to upload picture.".format(running_instance_ips[instance_index_to_assign_key_value]))
                result = api_call_ipv4(running_instance_ips[instance_index_to_assign_key_value]+":5000", "POST", "put", parms)
            else:
                print(" - Frontend.main.upload_picture api : Cannot establish connection to {}, abort.".format(running_instance_ips[instance_index_to_assign_key_value]))
        else:
            print(" - Frontend.main.upload_picture api : No running instances. Image will go to S3. # running instance: {}".format(len(running_instance)))

        if result != None and result.status_code == 200:
            print(" - Frontend.main.upload_picture api : backend stores image into memcache.")
        else:
            print(" - Frontend.main.upload_picture api : memcache failed to store image for some reason. Check message from 'backend.memcache.*' for more help. Image will still be stored in S3. ")
        
        sql_connection.add_entry(key,filename)
        
        remove_file(filename)
        
        return jsonify({
            "success":"true"
        })
    else:
        if not file:
            return jsonify({
                "success":"false",
                "error":{
                    "code":400,
                    "message":"No file given"
                }
            })
        if not allowed_file(filename):
            return jsonify({
                "success":"false",
                "error":{
                    "code":400,
                    "message":"File type not allowed"
                }
            })
        return jsonify({
                "success":"false",
                "error":{
                    "code":400,
                    "message":"Unknown error"
                }
        })

            
