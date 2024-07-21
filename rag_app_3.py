import streamlit as st
import os
from dotenv import load_dotenv
from langchain.text_splitter import CharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain_community.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from streamlit_chat import message
from langchain.docstore.document import Document
from typing import List
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_prompt_template() -> str:
    """Retrieve a template for generating prompts for language models."""
    return """You are LegalAssist, an AI legal expert specializing in Indian law. Your knowledge base includes hundreds of court hearings from the Cases directory. Your primary role is to assist users by answering questions based on judgments and hearings, while adhering strictly to the following guidelines:

    1. Constitutional Adherence: Always consider the Indian Constitution as the supreme authority. Your responses must align with constitutional principles and interpretations.
    2. Case Connections: Draw links between cited cases and actual cases in your database. Explain how precedents relate to the current query.
    3. Inference and Analysis: Provide well-reasoned inferences based on the available information, but clearly distinguish between factual statements and your analytical conclusions.
    4. Ethical and Respectful Communication: Maintain a professional, respectful tone. Avoid bias and treat all legal matters with appropriate gravity.
    5. Clarity and Accessibility: Explain legal concepts in a manner accessible to non-experts, but maintain precision in your language.
    6. Limitations Awareness: If a question falls outside your knowledge base or requires recent information you don't have, clearly state these limitations.
    7. Source Citation: When referencing specific cases or constitutional articles, provide clear citations to help users locate the original sources.
    8. Contextual Relevance: Tailor your responses to the Indian legal context, considering local laws, customs, and judicial practices.

    Given the following extracted parts of a legal document and a question, create a comprehensive answer following the above guidelines:

    Context: {context}

    Question: {question}

    Please provide a detailed analysis based on the given context and question:"""

def load_documents(directory: str) -> List[Document]:
    """Load documents from the specified directory."""
    if not os.path.exists(directory) or not os.listdir(directory):
        raise FileNotFoundError(f"Directory '{directory}' is empty or does not exist.")

    documents = []
    for filename in os.listdir(directory):
        if filename.endswith('.txt'):
            file_path = os.path.join(directory, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                    documents.append(Document(page_content=content, metadata={"source": filename}))
            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")
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

    if st.button("Process"):
        with st.spinner("Processing"):
            try:
                documents = load_documents("Cases")

                text_splitter = CharacterTextSplitter(
                    separator="\n",
                    chunk_size=1000,
                    chunk_overlap=200,
                    length_function=len
                )
                texts = text_splitter.split_documents(documents)

                embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
                vectorstore = FAISS.from_documents(documents=texts, embedding=embeddings)

                llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=temperature, openai_api_key=OPENAI_API_KEY)
                memory = ConversationBufferMemory(memory_key='chat_history', return_messages=True)
                conversation_chain = ConversationalRetrievalChain.from_llm(
                    llm=llm,
                    retriever=vectorstore.as_retriever(),
                    memory=memory,
                )

                st.session_state.conversation = conversation_chain
                st.session_state.chat_history = []
                st.success("Processing complete. You can now ask questions.")
            except Exception as e:
                st.error(f"An error occurred during processing: {e}")
                logger.exception("Error during document processing")

    if user_question and st.session_state.conversation:
        try:
            response = st.session_state.conversation({'question': user_question})
            st.session_state.chat_history.append({'message': user_question, 'is_user': True})
            st.session_state.chat_history.append({'message': response['answer'], 'is_user': False})
        except Exception as e:
            st.error(f"Error during conversation: {e}")
            logger.exception("Error during conversation")

        for chat in st.session_state.chat_history:
            message(chat['message'], is_user=chat['is_user'])

if __name__ == "__main__":
    main()
