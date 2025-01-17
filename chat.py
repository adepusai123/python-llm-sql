from Interfaces import State
import streamlit as st
from time import sleep
from sqlGenerator import SQLQueryGenerator


# Ensure all session state attributes are initialized
if "connected" not in st.session_state:
    st.session_state.connected = False  # Track connection status
if "query_generator" not in st.session_state:
    st.session_state.query_generator = None  # Placeholder for the SQLQueryGenerator instance
if "chat_state" not in st.session_state:
    st.session_state.chat_state = {
        "question": "",
        "query": "",
        "result": "",
        "answer": ""
    }
if "query_generated" not in st.session_state:
    st.session_state.query_generated = False  # Track if the query is generated
if "query_confirmed" not in st.session_state:
    st.session_state.query_confirmed = False  # Track user confirmation for query execution

def chat_ui():
    st.title("SQL Query Chatbot")
    st.session_state.connected = False
    try:
        # Toggle button for connection
        connection_toggle = st.checkbox(
            "Connect to SQLQueryGenerator",
            value=st.session_state.connected,
            help="Toggle to connect or disconnect SQLQueryGenerator"
        )

        if connection_toggle:
            if not st.session_state.connected:
                st.session_state.query_generator = SQLQueryGenerator()
                st.session_state.connected = True
                st.success("Connected to SQLQueryGenerator!")
                st.session_state.chat_state = {
                    "question": "",
                    "query": "",
                    "result": "",
                    "answer": ""
                }
        else:
            if st.session_state.connected:
                st.session_state.query_generator = None
                st.session_state.connected = False
                st.warning("Disconnected from SQLQueryGenerator!")

        if st.session_state.connected:
            # Handle question submission
            def handle_question_submit():
                user_input = st.session_state.user_input
                if user_input:
                    # Set the user's question in the chat state
                    st.session_state.chat_state["question"] = user_input

                    # Display the user's question
                    st.write(f"**User**: {user_input}")

                    # Use the run_graph method to process the question
                    st.session_state.chat_state = st.session_state.query_generator.run_graph(
                        st.session_state.chat_state
                    )

                    # Display the generated SQL query
                    st.write(f"**Generated SQL Query**: {st.session_state.chat_state['query']}")

                    # Display the query result
                    st.write(f"**SQL Result**: {st.session_state.chat_state['result']}")

                    # Display the AI's answer
                    st.write(f"**Answer**: {st.session_state.chat_state['answer']}")

                    # Clear the input field after submission
                    st.session_state.user_input = ""

            # Input field for user question
            st.text_input(
                "Ask a question:",
                key="user_input",
                placeholder="Ask about your database...",
                on_change=handle_question_submit  # Trigger on Enter key press
            )

            # Submit button
            if st.button("Submit Question"):
                handle_question_submit()

    except Exception as e:
        st.session_state.connected = False
        st.error(f"An error occurred: {e}")
