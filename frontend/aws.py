import boto3
from frontend.config import Config
from frontend.config import LOCAL_UPLOADS_DIR, LOCAL_CACHE_DIR, LOCAL_S3_DL_DIR
from frontend.helper import current_datetime, api_call_lambda
import requests
import os

class AWSController:
    ec2_resource = None
    ec2_client = None
    instance_list = None

    s3_resource = None
    s3_client = None
    bucket = None
    
    dynamo_db = None

    master_instance = None

    def __init__(self):
        '''
        instance_active_index: 2 for running, 1 for pending, 0 for stopped. 
        instance_active_status: index 0 for # of running instances, index 1 for # of pending instances, index 2 for # of stopped instances.
        '''
        self.ec2_resource = boto3.resource('ec2', region_name='us-east-1')
        self.ec2_client = boto3.client('ec2', region_name='us-east-1')

        self.s3_resource = boto3.resource('s3', region_name='us-east-1')
        self.s3_client = boto3.client('s3', region_name='us-east-1')
        self.bucket = self.s3_resource.Bucket(Config.BUCKET_NAME)
        self.dynamo_db = boto3.client('dynamodb')

    def clear_s3(self):
        s3_bucket = self.s3_resource.Bucket('1779-g17-test-1')
        bucket_versioning = self.s3_resource.BucketVersioning('1779-g17-test-1')
        if bucket_versioning.status == 'Enabled':
            s3_bucket.object_versions.delete()
        else:
            s3_bucket.objects.all().delete()

        return 1

    def add_file_s3(self, filename):
        final_path = os.path.join(LOCAL_UPLOADS_DIR, filename)
        try:
            self.s3_client.upload_file(final_path, Config.BUCKET_NAME, filename)
            return True
        except Exception as e:
            print(' - Frontend.aws.add_file_s3: Failed to add item to the s3!')
            return False
        
    def download_file(self, filename):
        final_path = os.path.join(LOCAL_S3_DL_DIR, filename)
        try:
            self.s3_client.download_file(Config.BUCKET_NAME, filename, final_path)
            return True
        except Exception as e:
            print(' - Frontend.aws.download_file: Failed to add item to the s3!')
            return False            
        
    def put_item_dynamo(self, key, filename):
        '''
        Put a item into dynamo table. Require key and filename. 
        
        ### Return
        True - If put success.
        
        False - If put fails.
        '''
        date = current_datetime()
        response = self.dynamo_db.put_item(
            TableName=Config.DYNAMODB_NAME,
            Item={
                'imageKey': {'S': key},
                'time': {'S': date},
                'filename': {'S': filename},
            }
        )
        
        # Check the response
        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
            print(' - Frontend.aws.put_item_dynamo: Successfully added item to the table!')
            return True
        else:
            print(' - Frontend.aws.put_item_dynamo: Failed to add item to the table!')
            return False
        
    def get_item_dynamo(self, key):
        '''
        Search a item in dynamo DB. 
        
        ### Return 
        filename, time as string, if success.
        
        None, if fails.
        '''
        response = self.dynamo_db.get_item(
            TableName=Config.DYNAMODB_NAME,
            Key={
                'imageKey': {'S': key},
            }
        )
        
        # Check the response
        if 'Item' in response:
            item = response['Item']
            print(' - Frontend.aws.get_item_dynamo: Successfully retrieved item with key{}'.format(key))
            return item['filename']['S'], item['time']['S']
        else:
            print(' - Frontend.aws.get_item_dynamo: Failed to retrieve item from the table!')
            return None, None
        
    def get_all_item_dynamo(self):
        '''
        Get all items from dynamo DB.
        
        ### Return 
        All items.
        '''
        response = self.dynamo_db.scan(
            TableName=Config.DYNAMODB_NAME,
            ScanFilter={}
        )
        
        return response['Items']
    
    def delete_all_dynamo(self):
        response = self.dynamo_db.scan(
            TableName=Config.DYNAMODB_NAME
        )

        # Get the items returned by the scan
        items = response['Items']

        # Iterate through the items and delete them one by one
        for item in items:
            self.dynamo_db.delete_item(
                TableName=Config.DYNAMODB_NAME,
                Key={
                    'imageKey': item['imageKey']
                }
            )
            
    def get_image_label(self, filename):
        '''
        This function will call lambda to detect labels of an image.
        
        ### Return
        response from lambda. None if something wrong.
        '''
        response = api_call_lambda(filename, 'label_detection')
        if response != None:
            return response
        else:
            return None
        
    def get_facial_analysis(self, filename):
        '''
        This function will call lambda to analysis a face.
        
        ### Return
        response from lambda. None if something wrong.
        '''
        response = api_call_lambda(filename, 'facial_analysis')
        if response != None:
            return response
        else:
            return None
        
        
        