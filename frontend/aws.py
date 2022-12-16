import boto3
from frontend.config import Config
from frontend.config import LOCAL_UPLOADS_DIR, LOCAL_CACHE_DIR, LOCAL_S3_DL_DIR
from frontend.helper import current_datetime, api_call_lambda
import requests
import os
import base64

class AWSController:
    ec2_resource = None
    ec2_client = None
    instance_list = None

    s3_resource = None
    s3_client = None
    bucket = None
    
    dynamo_db = None

    master_instance = None
    
    cloud_client = None

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
        
        self.cloud_client = boto3.client(
            'cloudwatch',
            region_name = 'us-east-1'
        )

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
        
    def get_celebrity_info(self, filename):
        '''
        This function will call lambda to recognize a celebrity.
        
        ### Return
        response from lambda. None if something wrong.
        '''
        response = api_call_lambda(filename, 'celebrity_detect')
        if response != None:
            return response
        else:
            return None
        
    def unpack_rekognition_response(self, action_type, response):
        '''
        This function will unpack response returned from rekognition.
        
        :parms action_type: `label`, `facial`, or 'celebrity'. 
        
        :parms response: response from `get_image_label` and `get_facial_analysis` and `get_celebrity_info`.
        
        ### Return 
        A dict of labels and confidence. 
        '''
        if action_type == 'label':
            data = response.json()
            result = {}
            
            if len(data['Labels']) != 0:
                for i, label in enumerate(data['Labels']):
                    result.update({label['Name']:label['Confidence']})
            return result
        elif action_type == 'facial':
            data = response.json()
            result = {}

            if len(data['FaceDetails']) != 0:
                facial_data_dict = data['FaceDetails'][0]
                result.update({'AgeRange':facial_data_dict['AgeRange']})
                result.update({'Smile':facial_data_dict['Smile']})
                result.update({'Gender':facial_data_dict['Gender']})
                result.update({'Emotions':facial_data_dict['Emotions'][0]})
            return result
        else:
            data = response.json()
            result = {}
            
            if len(data['CelebrityFaces']) != 0:
                celebrity_info = data['CelebrityFaces'][0]
                result.update({'url':celebrity_info['Urls'][0]})
                result.update({'Name':celebrity_info['Name']})
                result.update({'Emotions':celebrity_info['Face']['Emotions'][0]})
                
            return result
        
    def get_metrics_image(self):
        '''
        Return 2 dict of 'id - image' paired cloudwatch image. API-gateway and lambda.
        '''
        # Get API GATEWAY data:
        result_api_gateway = {}
        api_gateway_metrice = ['DataProcessed', 'Count', 'Latency']
        
        for i in api_gateway_metrice:
            response = self.cloud_client.get_metric_widget_image(
                MetricWidget = '''
                {{
                    "view": "timeSeries",
                    "stacked": false,
                    "metrics": [
                        [ "AWS/ApiGateway", "{}", "ApiId", "qxxjxcleb1" ],
                        [ "AWS/ApiGateway", "{}", "ApiId", "ovss37g82h" ],
                        [ "AWS/ApiGateway", "{}", "ApiId", "ooax7ms080" ]
                    ],
                    "width": 1000,
                    "height": 200,
                    "start": "-PT1H",
                    "end": "P0D",
                    "timezone": "-0500"
                }}'''.format(i, i, i),
                OutputFormat='png'
            )
            string_image = base64.b64encode(response['MetricWidgetImage']).decode('utf-8')
            result_api_gateway.update({i:string_image})
            
        result_lambda = {}
        lambda_metrics = ['Errors', 'ConcurrentExecutions', 'Duration']
           
        for i in lambda_metrics:
            response = self.cloud_client.get_metric_widget_image(
                MetricWidget = '''
                {{
                    "metrics": [
                        [ "AWS/Lambda", "{}", "FunctionName", "imageDetection" ],
                        [ "AWS/Lambda", "{}", "FunctionName", "facialAnalysis" ],
                        [ "AWS/Lambda", "{}", "FunctionName", "celebritiesDetect" ]
                    ],
                    "view": "timeSeries",
                    "stacked": false,
                    "stat": "Average",
                    "period": 300,
                    "width": 1000,
                    "height": 200,
                    "start": "-PT1H",
                    "end": "P0D",
                    "timezone": "-0500"
                }}'''.format(i, i, i),
                OutputFormat='png'
            )
            string_image = base64.b64encode(response['MetricWidgetImage']).decode('utf-8')
            result_lambda.update({i:string_image})
              
        return result_api_gateway, result_lambda