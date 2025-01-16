# Install required packages:
# pip install --upgrade langchain-community langchainhub langgraph
# pip install google-cloud google-cloud-aiplatform
# pip install langchain-google-vertexai
# pip install mysql-connector-python pymysql
from langchain_community.utilities import SQLDatabase
from google.cloud import aiplatform
from google.auth import load_credentials_from_file
from dotenv import load_dotenv
from langchain_google_vertexai import ChatVertexAI
from langchain import hub
from typing import Optional
from typing_extensions import Annotated, TypedDict

import os

# Load environment variables
load_dotenv()

# Define types for function inputs/outputs
class State(TypedDict):
    question: str
    query: str
    result: str
    answer: str

class QueryOutput(TypedDict):
    """Generated SQL query."""
    query: Annotated[str, ..., "Syntactically valid SQL query."]


# Function to connect to MySQL Database
def getSQLConnection():
    username = os.environ.get('DB_USER')
    password = os.environ.get('DB_PASSWORD')
    host = os.environ.get('DB_HOST')
    port = os.environ.get('DB_PORT')
    database_name = os.environ.get('DB_NAME') 
    db = None
    try:
        db = SQLDatabase.from_uri(
            f"mysql+mysqlconnector://{username}:{password}@{host}:{port}/{database_name}"
        )
        if db is not None:
            print('Connected to MySQL Database')
    except Exception as e:
        print('Error in connecting to MySQL Database:', e)
    return db

# Initialize the database connection
db = getSQLConnection()

# Function to initialize Google Vertex AI platform
def initiateGoogleAIPlatform():
    service_account_file = os.environ.get('GOOGLE_CRED_FILE_PATH')
    credentials, project_id = load_credentials_from_file(service_account_file)
    aiplatform.init(project=project_id, credentials=credentials, location='asia-south1')
    print('Google AI Platform initiated')
    llm = ChatVertexAI(model="gemini-1.5-flash-002", project=project_id, location="asia-south1", credentials=credentials)
    if llm is not None:
        print('Google Vertex AI initiated')
    return llm

# Initialize the LLM
llm = initiateGoogleAIPlatform()

# Pull the query prompt template from LangChain Hub
query_prompt_template = hub.pull("langchain-ai/sql-query-system-prompt")

# Function to generate SQL queries
def write_query(state: State):
    ''' Generate SQL Query to fetch information. '''
    print('Entered write_query function.', state["question"])
    try:
        # Generate the SQL query using the prompt template
        prompt = query_prompt_template.invoke(
            {
                "dialect": db.dialect,
                "top_k": 10,
                "table_info": db.get_table_info(),
                "input": state["question"]
            }
        )
        # Use the structured LLM to get the query
        structured_llm = llm.with_structured_output(QueryOutput)
        result = structured_llm.invoke(prompt)
        print('------RES : ', llm.invoke(prompt))
        return result["query"]
    except Exception as e:
        print('Error in generating query:', e)
        return {"query": None}

# Example usage of the write_query function
output = write_query({"question": "Get all the customers"})
print("Generated Query:", output["query"])
