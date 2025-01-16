from Interfaces import QueryOutput, State
from langchain_community.utilities import SQLDatabase
from google.cloud import aiplatform
from google.auth import load_credentials_from_file
from dotenv import load_dotenv
from langchain_google_vertexai import ChatVertexAI
from langchain_community.tools.sql_database.tool import QuerySQLDatabaseTool
from langgraph.graph import START, StateGraph
from langgraph.checkpoint.memory import MemorySaver
import os

# Load environment variables
load_dotenv()

class SQLQueryGenerator:
    def __init__(self):
        # Initialize environment variables and database connection
        self.db = self.getSQLConnection()
        self.llm = self.initiateGoogleAIPlatform()
    
    def getSQLConnection(self):
        """Function to connect to MySQL Database."""
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
    
    def initiateGoogleAIPlatform(self):
        """Initialize Google Vertex AI platform."""
        service_account_file = os.environ.get('GOOGLE_CRED_FILE_PATH')
        credentials, project_id = load_credentials_from_file(service_account_file)
        aiplatform.init(project=project_id, credentials=credentials, location='asia-south1')
        print('Google AI Platform initiated')
        llm = ChatVertexAI(model="gemini-1.5-flash-002", project=project_id, location="asia-south1", credentials=credentials)
        if llm is not None:
            print('Google Vertex AI initiated')
        return llm
    
    def create_custom_prompt(self, schema, dialect, question):
        """Create a custom prompt for SQL query generation."""
        prompt = f"""
        You are an AI assistant tasked with generating SQL queries. 
        The database uses the {dialect} dialect. Here is the schema of the database:

        {schema}

        Write a syntactically correct SQL query for the following question:

        {question}

        Ensure the query retrieves relevant information and adheres to SQL best practices.
        Do not include any unnecessary columns or clauses.
        """
        return prompt

    def write_query(self, state: State):
        """Generate SQL Query to fetch information based on the user question."""
        try:
            # Get schema and dialect from the database
            schema = self.db.get_table_info()
            dialect = self.db.dialect

            # Generate a custom prompt for the LLM
            prompt = self.create_custom_prompt(schema=schema, dialect=dialect, question=state.question)

            # Use Vertex AI LLM with structured output to get the query
            structured_llm = self.llm.with_structured_output(QueryOutput)
            response = structured_llm.invoke(prompt)

            # Debug: Print raw response for inspection
            print("Raw LLM Response:", response)

            # Extract the query from the response
            if isinstance(response, dict) and "query" in response:
                state.query = response["query"]
            elif hasattr(response, "query"):
                state.query = response.query
            else:
                state.query = response.strip()  # Fallback for plain string responses

            print(f"Generated Query:\n{state.query}")
            return state
        except Exception as e:
            print("Error in generating SQL query:", e)
            state.query = None
            return state
    
    def execute_query(self, state: State):
        """Execute the SQL query on the database."""
        try:
            execute_query_tool = QuerySQLDatabaseTool(db=self.db)
            return {"result": execute_query_tool.invoke(state.query)}
        except Exception as e:
            print('Error in executing query:', e)
            return {"result": None}

    def generate_answer(self, state: State):
        """Generate answer based on the query result."""
        try:
            prompt = (
                "Given the following user question, corresponding SQL query, and the result of the query, "
                "answer the user question in natural language.\n\n"
                f"Question: {state.question}\n"
                f"SQL Query: {state.query}\n"
                f"SQL Result: {state.result}\n\n"
            )
            response = self.llm.invoke(prompt)
            state.answer = response.content
            return state
        except Exception as e:
            print('Error in generating answer:', e)
            state.answer = None
            return state

    def run_graph(self, initial_state: State):
        """Run the LangGraph with human-in-the-loop."""
        memory = MemorySaver()
        graph_builder = StateGraph(State).add_sequence([self.write_query, self.execute_query, self.generate_answer])
        graph_builder.add_edge(START, "write_query")
        graph = graph_builder.compile(checkpointer=memory, interrupt_before=["execute_query"])
        config = {"configurable": {"thread_id": "1"}}

        for step in graph.stream(initial_state, config, stream_mode="updates"):
            print(f"Step Result: {step}")
            # Update the state with the step result
            if "question" in step:
                initial_state.question = step["question"]
            if "query" in step:
                initial_state.query = step["query"]
            if "result" in step:
                initial_state.result = step["result"]
            if "answer" in step:
                initial_state.answer = step["answer"]
        
        try:
            user_approval = input("Do you want to proceed with executing the query? (yes/no): ")
        except Exception as e:
            user_approval = "no"
            print("Error during user approval:", e)

        if user_approval.lower() == "yes":
            for step in graph.stream(None, config, stream_mode="updates"):
                print(f"Step Result: {step}")
        else:
            print("Operation cancelled by user.")

