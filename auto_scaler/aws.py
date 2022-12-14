import boto3
from manager_app.config import Config
from frontend.config import LOCAL_UPLOADS_DIR, LOCAL_CACHE_DIR, LOCAL_S3_DL_DIR
import os
import time

class AWSController:
    ec2_resource = None
    ec2_client = None
    instance_list = None

    s3_resource = None
    s3_client = None
    bucket = None

    master_instance = None

    def __init__(self):
        '''
        instance_active_index: 2 for running, 1 for pending, 0 for stopped. 
        instance_active_status: index 0 for # of running instances, index 1 for # of pending instances, index 2 for # of stopped instances.
        '''
        self.ec2_resource = boto3.resource('ec2', region_name='us-east-1')
        self.ec2_client = boto3.client('ec2', region_name='us-east-1')
        self.instance_list = [self.ec2_resource.Instance(i) for i in Config.INSTANCE_ID]
        self.s3_resource = boto3.resource('s3', region_name='us-east-1')
        self.s3_client = boto3.client('s3', region_name='us-east-1')
        self.bucket = self.s3_resource.Bucket(Config.BUCKET_NAME)
        self.master_instance = self.ec2_resource.Instance(Config.MASTER_INSTANCE_ID)

    def reload_instance_status(self):
        '''
        Reload instance state. This method must be executed before any operations that requires live state of the instance. Instance state doesn't automatically update. 
        '''
        for i in self.instance_list:
            i.reload()
        self.master_instance.reload()

    def get_instances_status(self):
        '''
        Instance status doesn't update by themselves. They needed to by manually updated. This function will update their status and return a up to date list. 
        '''
        self.reload_instance_status()

        result = {}

        for i in self.instance_list:
            result.update({i.id:i.state['Name']})

        return result

    def instance_operation(self, commend, flag, ratio=None):
        '''
        commend: growing or shrinking.
        flag: 1 for grow/shrink 1 instance at a time. 0 for grow/shrink based on ratio 2/0.5.

        This method will turn instance on or off based on commend and flag. 

        ### Example:

        When `flag == 1`, `commend == 'growing', method will go through all instances, find one stopped instance and start it. If there has no 
        stopped instance, method will retun operation fail.

        When `flag == 0`, `commend == 'growing', method will check if there has enough space to grow. If no enough space to grow, it will grow to max node (8 in this case.).
        Also when 'shrinking', method will make sure there has at least one instance running. 
        '''
        # Update instances status.
        self.reload_instance_status()

        if flag == 1:
            opertion_success = False
            if commend == "growing":
                for i in self.instance_list:
                    if i.state['Name'] == 'stopped':
                        i.start()
                        self.reload_instance_status()
                        opertion_success = True
                        break
            else:
                for i in self.instance_list:
                    if i.state['Name'] == 'running':
                        i.stop()
                        self.reload_instance_status()
                        opertion_success = True
                        break
            if opertion_success:
                return {"status_code":200, "operation_type":"single growing/shrinking", "message":"operation success"}
            else:
                return {"status_code":400, "operation_type":"single growing/shrinking", "message":"operation failed"}

        else:
            operation_success = False
            number_of_running_instances = 0
            number_of_stopped_instances = 0

            for i in self.instance_list:
                if i.state['Name'] == 'running':
                    number_of_running_instances+=1
                elif i.state['Name'] == 'stopped':
                    number_of_stopped_instances+=1

            if commend == 'growing':
                # conditional statement make sure there are enough space.
                executing_time = int(ratio*number_of_running_instances)
                if executing_time > len(self.instance_list):
                    executing_time = 8

                for c in range(executing_time-number_of_running_instances):
                    for i in self.instance_list:
                        if i.state['Name'] == 'stopped':
                            i.start()
                            time.sleep(1)
                            self.reload_instance_status()
                            break
                    operation_success = True
            else:
                executing_time = int(number_of_running_instances*ratio)
                if executing_time == 0:
                    return {"status_code":400, "operation_type":"ratio shrink", "message":"operation failed"}
                print(" - scaler.aws v:range :{}".format(number_of_running_instances-executing_time))
                for c in range(number_of_running_instances-executing_time):
                    print(" - scaler.aws : inside {} stopping.. ".format(c))
                    for i in self.instance_list:
                        if i.state['Name'] == 'running':
                            i.stop()
                            time.sleep(1)
                            print(" - scaler.aws : stopped one instance {}".format(i.id))
                            self.reload_instance_status()
                            break
                operation_success = True
            
            if operation_success:
                return {"status_code":200, "operation_type":"ratio growing/shrinking", "message":"operation success"}
            else:
                return {"status_code":400, "operation_type":"ratio growing/shrinking", "message":"operation failed"}

    def get_ip_address(self):
        '''
        Return a dict of **running** instances.
        '''
        self.reload_instance_status()

        result = {}

        for i in self.instance_list:
            if i.state['Name'] == 'running':
                result.update({i.id:i.public_ip_address})
        
        return result
    
    def get_ip_address_all(self):
        '''
        Return a dict of all instances.
        '''
        self.reload_instance_status()

        result = {}

        for i in self.instance_list:
            if i.state['Name'] != 'running':
                result.update({i.id:'0.0.0.0'})
            else:
                result.update({i.id:i.public_ip_address})
        
        return result

    def get_master_instance_ip_address(self):
        self.reload_instance_status()
        return self.master_instance.public_ip_address

    def clear_s3(self):
        # TODO: remove all data inside S3.
        s3_bucket = self.s3_resource.Bucket('1779-g17-test-1')
        bucket_versioning = self.s3_resource.BucketVersioning('1779-g17-test-1')
        if bucket_versioning.status == 'Enabled':
            s3_bucket.object_versions.delete()
        else:
            s3_bucket.objects.all().delete()

        return 1

    def clear_RDS(self):
        # TODO: remove all entries from RDS.
        return 1

    def add_file_s3(self, filename):
        final_path = os.path.join(LOCAL_UPLOADS_DIR, filename)
        self.s3_client.upload_file(final_path, Config.BUCKET_NAME, filename)
        
    def download_file(self, filename):
        final_path = os.path.join(LOCAL_S3_DL_DIR, filename)
        self.s3_client.download_file(Config.BUCKET_NAME, filename, final_path)

    def activate_instances(self):
        '''
        return a list of all running instances
        '''
        self.reload_instance_status()

        results = []

        for i in self.instance_list:
            if i.state['Name'] == 'running':
                results.append(i.id)
        
        return results
