from manager_app import app
from flask import render_template, url_for, request, redirect
from flask import flash, jsonify
import requests
from glob import escape
from decimal import Decimal
import threading
import time

# Import Forms
from manager_app.form import ConfigForm, ClearForm, DeleteForm, ManualForm, AutoForm

# Import helper
from manager_app.helper import api_call, current_datetime

# Import aws controller
from manager_app.aws import AWSController
aws_controller = AWSController()

# Import SQL
from manager_app.data import Data
sql_connection = Data()

# Import Cloud Watch
from manager_app.cloudwatch import CloudWatch
cloud_watch = CloudWatch()

# Import Chart Data
from manager_app.chart import Chart, DataAggregation
chart = Chart()
data_aggregation = DataAggregation()

def get_chart_data_thread():
    while True:
        instances = aws_controller.activate_instances()
        hitRate = cloud_watch.get_hit_rate(instances)
        numberOfItem = cloud_watch.get_number_of_item(instances)
        sizeOfItem = cloud_watch.get_total_size_of_item(instances)
        numberOfRequest = cloud_watch.get_total_number_of_requests(instances)
        missRate = cloud_watch.get_miss_rate(instances)
        chart.set_missRate(missRate)
        chart.set_hitRate(hitRate)
        chart.set_number_of_item(numberOfItem)
        chart.set_total_size(sizeOfItem)
        chart.set_number_of_request(numberOfRequest)
        
        current_time = current_datetime()
        data_aggregation.add_entry([hitRate, missRate, numberOfItem, sizeOfItem, numberOfRequest, current_time])

        time.sleep(60)

chart_task = threading.Thread(target = get_chart_data_thread)
chart_task.start()
    

@app.route("/")
def manager_main():
    return redirect(url_for("status"))

@app.route('/go_upload')
def go_upload():
    return redirect('/')

@app.route("/status")
def status():
    status_dic = aws_controller.get_instances_status()
    # data = data_aggregation.get_data()
    images = cloud_watch.get_metrics_image()
    
    return render_template("status.html", tag1_selected=True, status_dic=status_dic, images=images)

# TODO: need to update config and api_call to make them call instances. 
#       1. Acquire instances ipv4 address to make call.
#       2. Read response from instance. 
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

        ip_dic = aws_controller.get_ip_address()
        for i, e in enumerate(list(ip_dic.values())):
            url = e+":5000/"
            result = api_call(url, "GET", "config", parms)
        
        sql_connection.insert_config_data(size, choice)
        
        flash("Update success")

        return redirect(url_for("memcache_config"))

    elif request.method == "POST" and config_form.validate_on_submit():
        size = config_form.size.data
        choice = config_form.replacement_policy.data

        parms = {"size":size, "replacement_policy":choice}

        ip_dic = aws_controller.get_ip_address()
        for i, e in enumerate(list(ip_dic.values())):
            url = e+":5000/"
            result = api_call(url, "GET", "config", parms)
        
        sql_connection.insert_config_data(size, choice)
        flash("Update success")

        return redirect(url_for("memcache_config"))

    if request.method == "POST" and clear_form.validate_on_submit():

        ip_dic = aws_controller.get_ip_address()
        for i, e in enumerate(list(ip_dic.values())):
            url = e+":5000/"
            result = api_call(url, "GET", "clear")
        
        flash("memcache cleared")
        return redirect(url_for("memcache_config"))
        
    return render_template("config.html", form1=config_form, form2=clear_form, tag2_selected=True)

@app.route("/manual", methods=["GET", "POST"])
def manual_resizing():
    '''
    By manually controlling instances, it will notify auto scaler to stop auto mode. 
    '''
    manual_form = ManualForm()

    status_dic = aws_controller.get_instances_status()
    result = False

    if request.method == "POST" and manual_form.validate_on_submit():
        if manual_form.refresh.data:
            return redirect(url_for("manual_resizing"))
        
        if manual_form.growing.data:
            result = aws_controller.instance_operation("growing", 1)
        else:
            result = aws_controller.instance_operation("shrinking", 1)

        if result['status_code'] == 200:
            flash("Operation success")
            api_call("127.0.0.1:5000/", "GET", "api/pool_size_notify", {"size":len(aws_controller.get_ip_address())})
            # Call scaler to exit auto mode.
            api_call("127.0.0.1:5000/scaler/", "GET", "manual_mode", timeout=2)
        else:
            flash("Operation failed.\nReasons can be either: No more intsances to stop/All instances are already running/Some pending instances. At least one running instance")
        

        return redirect(url_for("manual_resizing"))

    return render_template("manual.html", form1=manual_form, status_dic=status_dic)

@app.route("/automatic", methods=["GET", "POST"])
def automatic_resizing():
    auto_policy_form = AutoForm()

    status_dic = aws_controller.get_instances_status()

    if request.method == "POST" and auto_policy_form.validate_on_submit():
        max_tr = Decimal(auto_policy_form.max_threshold.data)
        min_tr = Decimal(auto_policy_form.min_threshold.data)
        expand_ratio = Decimal(auto_policy_form.expand_ratio.data)
        shrink_ratio = Decimal(auto_policy_form.shrink_ratio.data)
        
        print(" - Manager.automatic :{}, {}, {}, {}".format(max_tr, min_tr, expand_ratio, shrink_ratio))

        if max_tr < min_tr:
            flash("Operation failed, max threshold max greater then min threshold")
            return redirect(url_for("automatic_resizing"))
        
        parms = {
            'maxMissRateThreshold':max_tr,
            'minMissRateThreshold':min_tr,
            'expandRatio':expand_ratio,
            'shrinkRatio':shrink_ratio
        }
        # Call scaler to enter auto mode. 
        result = api_call("127.0.0.1:5000/scaler/", "GET", "config", parms)
        result = result.json()

        if result['success'] == 'true':
            flash("Operation success, now it's auto mode.")
        else:
            flash("Operation failed, it's still manual mode.")

        return redirect(url_for("automatic_resizing"))

    return render_template("auto.html", form1=auto_policy_form, status_dic=status_dic)

@app.route("/delete", methods=["GET", "POST"])
def delete_data():
    delete_form = DeleteForm()
    print(" * DELETE all data")

    if request.method == "POST" and delete_form.validate_on_submit():
        ip_address = aws_controller.get_ip_address()

        for i, e in enumerate(list(ip_address.values())):
            url = e+":5000/"
            result = api_call(url, "GET", "clear")
            print(e)
    
        aws_controller.clear_s3()
        sql_connection.delete_all_entries()

        flash("All data deleted.")

    return render_template("delete.html", form2=delete_form, tag3_selected=True)

@app.route("/clear_memcache", methods=["GET", "POST"])
def clear_memcache():
    clear_form = ClearForm()
    print(" * Clear memcache")

    if request.method == "POST" and clear_form.validate_on_submit():
        ip_address = aws_controller.get_ip_address()

        for i, e in enumerate(list(ip_address.values())):
            url = e+":5000/"
            result = api_call(url, "GET", "clear")
            print(e)
        flash("All memcache cleared.")

    return render_template("clear.html", form2=clear_form, tag4_selected=True)


# For api calls to nodes.

@app.route("/api/get_config", methods=["GET"])
def api_get_config():
    if request.method == "GET":
        print(" - Manager.main.api_get_config : received config get request. If this message pops, means the node is functioning. ")
        # TODO: manager should ask RDS for leatest config. Now just mock it up. 
        size = 100  # From RDS
        choice = 1  # From RDS
        
        config = sql_connection.get_config_data()
        try:
            size = config[0][1]
            choice = config[0][2]
        except IndexError or TypeError as e:
            size = 100  # From RDS
            choice = 1  # From RDS
        # config [0][1] for size, [0][2] policy. From database.

        return jsonify({'size':size, 'replace_policy':choice}), 200