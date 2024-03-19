import streamlit as st
import pdfplumber
import docx2txt
import os
import openai
from llama_index.llms.openai import OpenAI
try:
  from llama_index import VectorStoreIndex, ServiceContext, Document, SimpleDirectoryReader
except ImportError:
  from llama_index.core import VectorStoreIndex, ServiceContext, Document, SimpleDirectoryReader
from llama_index.core import Settings
from llama_index.core.readers.base import BaseReader
from llama_index.core import Document


# Function to extract text from a file
def extract_text(file):
    if file.type == "application/pdf":
        with pdfplumber.open(file) as pdf:
            page = pdf.pages[0]
            return page.extract_text()
    elif file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return docx2txt.process(file)
    elif file.type == "text/plain":
        return file.getvalue().decode()
    else:
        st.write("Unsupported file type")


class StringReader(BaseReader):
    def __init__(self, text):
        self.text = text

    def load_data(self):
        yield Document(content=self.text)


@st.cache_resource(show_spinner=False)
def load_data(text):
    with st.spinner(text="Loading and indexing your file – hang tight! This should take 1-2 minutes."):
        reader = StringReader(text)
        docs = reader.load_data()
        service_context = ServiceContext.from_defaults(llm=OpenAI(model="gpt-3.5-turbo", temperature=0.5, system_prompt=system_prompt))
        index = VectorStoreIndex.from_documents(docs, service_context=service_context)
        return index


st.title("AI Document-bot, powered by LlamaIndex 💬🦙")
openai.api_key = st.secrets.openai_key

# Upload the file
file = st.file_uploader("Upload a file", type=["pdf", "docx", "txt"])
if file is not None:
    # Extract text from the file
    text = extract_text(file)
    #st.write(text)

    system_prompt = f"You are an AI with the ability to understand and generate responses based on the content of an uploaded file. The file contains the following information: {text}. Your job is to answer questions about the content of the file. – do not hallucinate features."

    # Initialize the chat messages history
    st.session_state["messages"] = [
             {"role": "assistant", "content": "Ask me a question about the uploaded file!"}
        ]


    index = load_data(text)

    #if "chat_engine" not in st.session_state.keys(): # Initialize the chat engine
    st.session_state.chat_engine = index.as_chat_engine(ChatMode="condense_question", verbose=True)

    if prompt := st.chat_input("Your question"): # Prompt for user input and save to chat history
      st.session_state.messages.append({"role": "user", "content": prompt})
      system_prompt += f" The user asked: {prompt}"

    for message in st.session_state.messages: # Display the prior chat messages
      with st.chat_message(message["role"]):
        st.write(message["content"])

# If last message is not from assistant, generate a new response
    if st.session_state.messages[-1]["role"] != "assistant":
     with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = st.session_state.chat_engine.chat(system_prompt)
            st.write(response.response)
            message = {"role": "assistant", "content": response.response}
            st.session_state.messages.append(message) # Add response to message history



