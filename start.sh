CURRENT_PATH=$(pwd)
LOCAL_UPLOADS_DIR=${CURRENT_PATH}/frontend/static/uploads
LOCAL_CACHE_DIR=${CURRENT_PATH}/frontend/static/local_cache
LOCAL_S3_DIR = ${CURRENT_PATH}/frontend/static/s3_download

echo $LOCAL_CACHE_DIR
echo $LOCAL_UPLOADS_DIR
echo $LOCAL_S3_DIR

# Create dir for local image
echo "Creating dirs.."
mkdir -p $LOCAL_CACHE_DIR
mkdir -p $LOCAL_UPLOADS_DIR
mkdir -p $LOCAL_S3_DIR

# Check conda 
echo "Checking conda.."
if ! command -v conda &> /dev/null
then
    echo "Conda could not be found. Install conda at https://www.anaconda.com"
    exit
fi

# Check mysql
echo "Checking mysql.."
if ! command -v mysql &> /dev/null
then
    echo "Mysql could not be found. Install mysql through -sudo apt install mysql-server-"
    exit
fi

# Check if conda env exists
find_in_conda_env(){
    conda env list | grep "${@}" >/dev/null 2>/dev/null
}

echo "Checking conda env.."
if find_in_conda_env ".*MEMCACHE.*" ; then
    echo "Conda env detected, activating..."
    conda info | egrep "conda version|active environment"
    conda activate MEMCACHE
else 
    echo "Conda env doesn't exist."
    echo "Importing conda env..."
    conda info | egrep "conda version|active environment"
    conda env create -f environment.yml
    if find_in_conda_env ".*MEMCACHE.*" ; then
        echo "Conda env installed, activating..."
        conda info | egrep "conda version|active environment"
        conda activate MEMCACHE
    else
        echo "Failed to import conda env, exit."
        exit
    fi
fi

echo "You are good to go. Launching instance.."
sleep 1s

# Lauch instance
python3 run.py