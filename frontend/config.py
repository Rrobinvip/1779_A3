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
    DB_CONFIG = {
        "user":"admin",
        "password":"ece1779pass",
        "host":"database-a2.cs1fu79ctxla.us-east-1.rds.amazonaws.com",
        "database":"cloudcomputing"
    }
    # DB_CONFIG = {
    #     "user":"root",
    #     "password":"19970808",
    #     "host":"localhost",
    #     "database":"memcache_test_1"
    # }
    INSTANCE_ID = [
        'i-0522fc067719b7e7b',
        'i-0004e5771db2385a4',
        'i-0c7bc72034eca6538',
        'i-0deec7aa32d788514',
        'i-0ab55e23171dd000d',
        'i-001617701b24b9f15',
        'i-0396c8e9d90a99bf8',
        'i-00919b1cebd5badef'
    ]
    MASTER_INSTANCE_ID = 'i-01e24b43881322f78'
    BUCKET_NAME = '1779-g17-test-1'