import streamlit as st
import os
from dotenv import load_dotenv
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings.openai import OpenAIEmbeddings
from elasticsearch import Elasticsearch
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from streamlit_chat import message
from pymongo import MongoClient

# Custom Elasticsearch retriever
class CustomElasticsearchRetriever:
    def __init__(self, es_client, index_name):
        self.es_client = es_client
        self.index_name = index_name

    def get_relevant_documents(self, query, top_k=5):
        query_body = {
            "query": {
                "match": {
                    "text": query
                }
            },
            "size": top_k
        }
        response = self.es_client.search(index=self.index_name, body=query_body)
        documents = [hit['_source']['text'] for hit in response['hits']['hits']]
        return documents

def main():
    load_dotenv()
    OPENAI_API_KEY = os.getenv("GPT_API_KEY")
    if not OPENAI_API_KEY:
        st.error("API key for OpenAI is not set. Please check your .env file.")
        return

    st.set_page_config(page_title="LegalTree", page_icon="⚖️")

    if "conversation" not in st.session_state:
        st.session_state.conversation = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    st.header("Chat with your court hearings :books:")
    user_question = st.text_input("Ask a question about your case:")
    temperature = st.slider("Set Temperature", min_value=0.0, max_value=1.0, value=0.6)

    # Process text files and create conversation chain if user clicks "Process"
    if st.button("Process"):
        with st.spinner("Processing"):
            TXT_DIRECTORY = "Cases"  # Directory where the text files are stored
            text_files = [os.path.join(TXT_DIRECTORY, f) for f in os.listdir(TXT_DIRECTORY) if f.endswith('.txt')]

            raw_text = ""
            for txt_file in text_files:
                with open(txt_file, 'r', encoding='utf-8') as file:
                    raw_text += file.read()

            text_chunks = CharacterTextSplitter(
                separator="\n",
                chunk_size=1000,
                chunk_overlap=200,
                length_function=len
            ).split_text(raw_text)

            embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)

            es = Elasticsearch("http://localhost:9200")
            for i, chunk in enumerate(text_chunks):
                vector = embeddings.embed_documents([chunk])[0]  # Using the correct method to generate embeddings
                es.index(index="text-documents", body={"text": chunk, "vector": vector}, id=i)

            llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=temperature, openai_api_key=OPENAI_API_KEY)
            memory = ConversationBufferMemory(memory_key='chat_history', return_messages=True)
            retriever = CustomElasticsearchRetriever(es_client=es, index_name="text-documents")
            conversation_chain = ConversationalRetrievalChain.from_llm(
                llm=llm,
                retriever=retriever,
                memory=memory
            )

            st.session_state.conversation = conversation_chain
            st.session_state.chat_history = []

    # Handle user input if provided
    if user_question and st.session_state.conversation:
        response = st.session_state.conversation({'question': user_question})
        st.session_state.chat_history.append({'message': user_question, 'is_user': True})
        st.session_state.chat_history.append({'message': response['result'], 'is_user': False})

        for chat in st.session_state.chat_history:
            message(chat['message'], is_user=chat['is_user'])


if __name__ == "__main__":
    main()
