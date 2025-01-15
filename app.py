# pip install --upgrade --quiet langchain-community langchainhub langgraph
from langchain_community.utilities import SQLDatabase
# pip install google-cloud google-cloud-aiplatform 
from google.cloud import aiplatform
from google.auth import load_credentials_from_file
import os
from dotenv import load_dotenv

load_dotenv()

# pip install mysql-connector-python pymysql
def getSQLConnection():
    username =os.environ.get('DB_USER')
    password =os.environ.get('DB_PASSWORD')
    host = os.environ.get('DB_HOST')
    port = os.environ.get('DB_PORT')
    databaseName = os.environ.get('DB_NAME') 
    db = None
    try:
        db = SQLDatabase.from_uri(f"mysql+mysqlconnector://{username}:{password}@{host}:{port}/{databaseName}")
        if db is not None:
            print('Connected to MySQL Database')
    except Exception as e:
        print('Error in connecting to MySQL Database', e)
    finally:
        return db

def initiateGoogleAIPlatform():
    service_accout_file = os.environ.get('GOOGLE_CRED_FILE_PATH')
    credentials, project_id = load_credentials_from_file(service_accout_file)
    aiplatform.init(project=project_id, credentials=credentials, location='asia-south1')
    print('Google AI Platform initiated')


initiateGoogleAIPlatform()
db = getSQLConnection()
ans = db.run("SELECT * FROM customers")
print('type of ',ans)



