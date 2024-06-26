import streamlit as st
import os
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.embeddings import OpenAIEmbeddings
from elasticsearch import Elasticsearch, ElasticSearch
from langchain_elasticsearch import ElasticsearchRetriever
from langchain_community.chat_models import ChatOpenAI
from langchain_openai import OpenAI
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from streamlit_chat import message


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
    st.session_state.chat_history = None

  st.header("Chat with your court hearings :books:")
  user_question = st.text_input("Ask a question about your case:")

  # Process PDFs and create conversation chain if user uploads and clicks "Process"
  if st.button("Process"):
    with st.spinner("Processing"):
      pdf_docs = st.session_state.get('uploaded_pdfs', [])  # Check for previously uploaded PDFs
      if not pdf_docs:
        pdf_docs = st.file_uploader(
          "Upload your PDFs here", accept_multiple_files=True)
      
      raw_text = ""
      for pdf in pdf_docs:
        pdf_reader = PdfReader(pdf)
        for page in pdf_reader.pages:
          raw_text += page.extract_text()

      text_chunks = CharacterTextSplitter(
          separator="\n",
          chunk_size=1000,
          chunk_overlap=200,
          length_function=len
      ).split_text(raw_text)

      embeddings = OpenAIEmbeddings() 

      es = Elasticsearch("http://localhost:9200")
      for i, chunk in enumerate(text_chunks):
                vector = embeddings.embed_text(chunk)
                es.index(index="pdf-documents", body={"text": chunk, "vector": vector}, id=i)


      llm = OpenAI(model="gpt-3.5-turbo-instruct",temperature=0.6, openai_api_key=OPENAI_API_KEY)
      memory = ConversationBufferMemory(
          memory_key='chat_history', return_messages=True)
      conversation_chain = ConversationalRetrievalChain.from_llm(
          llm=llm,
          retriever=ElasticsearchRetriever(es_client=es, index_name="pdf-documents"),
          memory=memory
      )

      st.session_state['uploaded_pdfs'] = pdf_docs  
      st.session_state.conversation = conversation_chain

  # Handle user input if provided
  if user_question:
    response = st.session_state.conversation({'question': user_question})
    st.session_state.chat_history.append({'message': user_question, 'is_user': True})
    st.session_state.chat_history.append({'message': response['chat_history'], 'is_user': False})

    for chat in st.session_state.chat_history:
        message(chat['message'], is_user=chat['is_user'])
