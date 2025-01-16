# Define types for function inputs/outputs
from Interfaces import State
from chat import chat_ui
from sqlGenerator import SQLQueryGenerator


if __name__ == "__main__":
    chat_ui()
    # query_generator = SQLQueryGenerator()
    # initial_state = State(question="How many customers are present?", query="", result="", answer="")
    # query_generator.run_graph(initial_state)


  