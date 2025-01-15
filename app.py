# pip install --upgrade --quiet langchain-community langchainhub langgraph
from langchain_community.utilities import SQLDatabase
# pip install google-cloud google-cloud-aiplatform 
from google.cloud import aiplatform
from google.auth import load_credentials_from_file
from dotenv import load_dotenv
import os
from typing_extensions import TypedDict

# pip install langchain-google-vertexai
from langchain_google_vertexai import ChatVertexAI
from langchain import hub
from typing_extensions import Annotated

# pip install -U langsmith 
from langchain_community import LangSmith

langsmith_client = LangSmith(api_key=os.getenv("LANGSMITH_API_KEY"))

# loading .env data to os.environ
load_dotenv()
query_prompt_template=None
llm = None

class State(TypedDict):
    question: str
    query: str
    result: str
    answer: str

class QueryOutput(TypedDict):
    '''Generated SQL Query.'''
    query: Annotated[str, "Syntactically valid SQL Query."]

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

db = getSQLConnection()

def initiateGoogleAIPlatform():
    service_accout_file = os.environ.get('GOOGLE_CRED_FILE_PATH')
    credentials, project_id = load_credentials_from_file(service_accout_file)
    aiplatform.init(project=project_id, credentials=credentials, location='asia-south1')
    print('Google AI Platform initiated')
    llm = ChatVertexAI(model="gemini-1.5-flash", project=project_id, location="asia-south1")
    if llm is not None:
        print('Google Vertex AI initiated')
    return llm 

llm = initiateGoogleAIPlatform()


# ans = db.run("SELECT * FROM customers")
# print('type of ',db.dialect, db.get_table_info())
hub.set_api_key(os.getenv("LANGSMITH_API_KEY"))
query_prompt_template = hub.pull("langchain-ai/sql-query-system-prompt")
# assert len(query_prompt_template.messages) == 1
# query_prompt_template.messages[0].pretty_print()

def write_query(state:State):
    ''' Generate SQL Query to fetch information. '''
    prompt = query_prompt_template.invoke(
        {
            "dialect": db.dialect,
            "top_k": 10,
            "table_info": db.get_table_info(),
            "input": state['question']
        }
    )

    structured_llm = llm.with_structured_output(QueryOutput)
    result = structured_llm.invoke(prompt)
    return {"query": result["query"]}


write_query({'question':'Get all the customers'})
        

