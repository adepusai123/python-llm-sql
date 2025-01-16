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
from langchain_community.tools.sql_database.tool import QuerySQLDatabaseTool
from langgraph.graph import START, StateGraph
from IPython.display import display, Image
from langgraph.checkpoint.memory import MemorySaver


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
        return {"query": "SELECT * FROM customers"}
        structured_llm = llm.with_structured_output(QueryOutput)
        result = structured_llm.invoke(prompt)
        # print('------RES : ', llm.invoke(prompt))
        return result["query"]

    except Exception as e:
        print('Error in generating query:', e)
        return {"query": None}

# Example usage of the write_query function
output = write_query({"question": "Get all the customers"})
print("*******Generated Query:", output["query"])

def execute_query(state: State):
    """Execute the SQL query on the database."""
    try:
        excute_query_tool = QuerySQLDatabaseTool(db=db)
        return { "result": excute_query_tool.invoke(state["query"])}
    except Exception as e:
        print('Error in executing query:', e)
        return {"result": None}
    
# result = execute_query({"query": "SELECT * FROM customers"})
result = execute_query(output)
# print('---RES ', result)

# Generate Answers
def generate_answer(state: State):
    """Generate answer based on the query result."""
    try:
        prompt = (
            "Given the following user question, corresponding SQL query, and the result of the query, "
            "and SQL result, answer the user question.\n\n"
            f"question: {state['question']}\n"
            f"SQL Query: {state['query']}\n"
            f"SQL Result: {state['result']}\n\n"
        )
        response = llm.invoke(prompt)
        return {"answer": response.content }
    except Exception as e:
        print('Error in generating answer:', e)
        return {"answer": None}

graph_builder = StateGraph(State).add_sequence(
    [write_query, execute_query, generate_answer]
)
graph_builder.add_edge(START, "write_query")
graph = graph_builder.compile()

# display(Image(graph.get_graph().draw_mermaid_png()))    
# print('******Graph:****** ', graph)

# for step in graph.stream(
#     {"question": "how many customers are present"}
# ):
#     print(step)

# Human in the loop
memory = MemorySaver()
graph = graph_builder.compile(checkpointer=memory, interrupt_before=["execute_query"])

config = { "configurable": {"thread_id": "1"}}

# display(Image(graph.get_graph().draw_mermaid_png())) 

for step in graph.stream(
    {"question": "how many customers are present"},
    config,
    stream_mode="updates"
):
    print(step)

try:
    user_approval = input("Do you want to go to execute query? (yes/no): ")
except Exception as e:
    user_approval = "no"
    print('Error in user approval:', e)

if user_approval.lower() == "yes":
    # If step approved, continue
    for step in graph.stream(None, config, stream_mode="updates"):
        print(step) 
else:
    print("Operation cancelled by user")
