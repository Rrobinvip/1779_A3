from auto_scaler import app
import threading
import time
from auto_scaler.aws import AWSController
from auto_scaler.cloudwatch import CloudWatch
from auto_scaler.scaler import Scaler
from ec2_metadata import ec2_metadata
from flask import jsonify, request

aws_controller = AWSController()
cloud_watch = CloudWatch()
scaler = Scaler()

MIN_INSTANCE_LIMIT = 1
MAX_INSTANCE_LIMIT = 8
TIME_INTERVAL = 1

stop_event = threading.Event()

def cloud_watch_thread():
    iteration = 60
    while True:
        if iteration == 60:
        #Do the auto scaling every 1 min
            instances = aws_controller.activate_instances()
            result = cloud_watch.get_miss_rate(instances)
            auto_scaler_checker(result)
            iteration = 0
        iteration += 1
        if stop_event.is_set():
            print(" - scaler.main.thread : I think I should stop.")
            break
        time.sleep(TIME_INTERVAL)

def auto_scaler_checker(result):
    maxMissRateThreshold = scaler.get_max_miss_rate_threshold()
    minMissRateThreshold = scaler.get_min_miss_rate_threshold()
    expandRatio = scaler.get_expand_ratio()
    shrinkRatio = scaler.get_shrink_ratio()
    print("Current Miss Rate {}".format(result))
    print("Max Miss Rate: {}".format(maxMissRateThreshold))
    print("Min Miss Rate: {}".format(minMissRateThreshold))
    if result <= minMissRateThreshold:
        print(" scaler.main : shrinking")
        shrink(shrinkRatio)
    elif result >= maxMissRateThreshold:
        print(" scaler.main : expanding")
        expand(expandRatio)

def expand(expandRatio):
    #calculate the number to expand
    currentActiveInstances = aws_controller.activate_instances()
    currentActiveNumber = len(currentActiveInstances)
    targetActiveNumber =  int(currentActiveNumber*expandRatio)
    if targetActiveNumber > MAX_INSTANCE_LIMIT:
        targetActiveNumber = MAX_INSTANCE_LIMIT
    if targetActiveNumber < MIN_INSTANCE_LIMIT:
        targetActiveNumber = MIN_INSTANCE_LIMIT
    print(" - scaler.mian.expend: expanding..")
    print("\tBefore Expanding the number of nodes: ")
    print("\tCurrent active nodes {}".format(currentActiveNumber))
    print("\tTarget active nodes {}".format(targetActiveNumber))

    result = aws_controller.instance_operation("growing", 0, ratio=expandRatio)

    currentActiveInstances = aws_controller.activate_instances()
    currentActiveNumber = len(currentActiveInstances)
    print("\tAfter Expanding the number of nodes: ")
    print("\tCurrent active nodes {}".format(currentActiveNumber))
    print("\tTarget active nodes {}".format(targetActiveNumber))

def shrink(shrinkRatio):
    currentActiveInstances = aws_controller.activate_instances()
    currentActiveNumber = len(currentActiveInstances)
    targetActiveNumber = int(currentActiveNumber * shrinkRatio)
    if targetActiveNumber > MAX_INSTANCE_LIMIT:
        targetActiveNumber = MAX_INSTANCE_LIMIT
    if targetActiveNumber < MIN_INSTANCE_LIMIT:
        targetActiveNumber = MIN_INSTANCE_LIMIT
    
    print(" - scaler.mian.expend: shrinking..")
    print("\tBefore shrinking the number of nodes: ")
    print("\tCurrent active nodes {}".format(currentActiveNumber))
    print("\tTarget active nodes {}".format(targetActiveNumber))

    result = aws_controller.instance_operation("shrinking", 0, ratio=shrinkRatio)
    
    currentActiveInstances = aws_controller.activate_instances()
    currentActiveNumber = len(currentActiveInstances)
    print("\tAfter shrinking the number of nodes: ")
    print("\tCurrent active nodes {}".format(currentActiveNumber))
    print("\tTarget active nodes {}".format(targetActiveNumber))
    

        

cloud_watch_task = threading.Thread(target = cloud_watch_thread)


@app.route("/manual_mode", methods=['GET'])
def switch_manual_mode():
    '''
    This function switch auto scaler to manual mode
    '''
    if cloud_watch_task.is_alive():
        try:
            # cloud_watch_task.join()
            stop_event.set()
            cloud_watch_task.join()
            stop_event.clear()
            response = jsonify({
                "success":"true",
                "status":200
            })
        except:
            print("Can not terminate thread")
            response = jsonify({
                "success": "false",
                "error":{
                    "code":400,
                    "message":"Can not terminate thread"
                }
            })
    else:
        response = jsonify({
            "success":"true",
            "status":200
        })
    return response
    

@app.route("/config", methods = ['GET'])
def auto_scaler_config():
    '''
    This function switch auto scaler to auto mode and update config
    '''
    maxMissRateThreshold = None
    minMissRateThreshold = None
    expandRatio = None
    shrinkRatio = None
    if 'maxMissRateThreshold' in request.args and \
        'minMissRateThreshold' in request.args and \
        'expandRatio' in request.args and \
        'shrinkRatio' in request.args :
        maxMissRateThreshold = float(request.args.get('maxMissRateThreshold'))
        minMissRateThreshold = float(request.args.get('minMissRateThreshold'))
        expandRatio = float(request.args.get('expandRatio'))
        shrinkRatio = float(request.args.get('shrinkRatio'))
    if maxMissRateThreshold is not None and \
        minMissRateThreshold is not None and \
        expandRatio is not None and \
        shrinkRatio is not None:
        scaler.set_max_miss_rate_threshold(maxMissRateThreshold)
        scaler.set_min_miss_rate_threshold(minMissRateThreshold)
        scaler.set_expand_ratio(expandRatio)
        scaler.set_shrink_ratio(shrinkRatio)
        #start the cloud watch
        if not cloud_watch_task.is_alive():
            try:
                cloud_watch_task.start()
                response = jsonify({
                    "success":"true",
                    "status":200
                })
            except:
                print("Error when start thread")
                response = jsonify({
                    "success":"false",
                    "error":{
                        "code":400,
                        "message":"Can not start thread"
                    }
                })
        else:
            try:
                stop_event.set()
                cloud_watch_task.join()
                stop_event.clear()
                cloud_watch_task.start()
                response = jsonify({
                    "success":"true",
                    "status":200
                })
            except:
                response = jsonify({
                   "success":"false",
                   "error":{
                    "code":400,
                    "message":"Thread stop and start error"
                   } 
                })
    else:
        print("Error Parameter")
        response = jsonify({
            "success":"false",
            "error":{
                "code":400,
                "message":"Error parameters"
            }
        })
    return response


@app.route("/auto_test", methods = ["GET"])
def auto_test():
    maxMissRateThreshold = 0.5
    minMissRateThreadhold = 0.25
    expandRatio = 2.0
    shrinkRatio = 0.5
    scaler.set_max_miss_rate_threshold(maxMissRateThreshold)
    scaler.set_min_miss_rate_threshold(minMissRateThreadhold)
    scaler.set_expand_ratio(expandRatio)
    scaler.set_shrink_ratio(shrinkRatio)
    if not cloud_watch_task.is_alive():
        try:
            cloud_watch_task.start()
            response = jsonify({
                "success":"true",
                "status" : 200
            })
        except:
            response = jsonify({
                "success":"false",
                "error":{
                    "code":400,
                    "message":"Can not start thread"
                }
            })
    else:
        response = jsonify({
            "success":"true",
            "status":200
        })
    return response
