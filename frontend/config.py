import os

TEMPLATE_DIR = os.path.abspath("./frontend/templates")
STATIC_DIR = os.path.abspath("./frontend/static")
LOCAL_CACHE_DIR = os.path.abspath("./frontend/static/local_cache")
LOCAL_UPLOADS_DIR = os.path.abspath("./frontend/static/uploads")
LOCAL_S3_DL_DIR = os.path.abspath("./frontend/static/s3_download")
ALLOWED_EXTENSIONS = {'jpg', 'jpe', 'jpeg', 'png', 'gif', 'svg', 'bmp', 'webp'}

class Config(object):
    SECRET_KEY = "teeesssttt"
    UPLOADED_PHOTOS_DEST = "./frontend/static/uploads"
    MASTER_INSTANCE_ID = 'i-01e24b43881322f78'
    BUCKET_NAME = '1779-g17-test-1'
    DYNAMODB_NAME = '1779_a3_dev_1'
    LAMBDA_API = {
        'label_detection':'https://ooax7ms080.execute-api.us-east-1.amazonaws.com/imageDetection?filename=',
        'facial_analysis':'https://ovss37g82h.execute-api.us-east-1.amazonaws.com/facialAnalysis?filename='
    }