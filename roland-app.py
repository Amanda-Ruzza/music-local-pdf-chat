import logging
import tempfile
from time import sleep, time
from os import getenv, getcwd, path
from os.path import getsize

import streamlit as st
from dotenv import load_dotenv 
from PyPDF2 import PdfReader
from pdf2image import convert_from_path
import pytesseract

from langchain.text_splitter import CharacterTextSplitter
from langchain.docstore.document import Document
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.callbacks import get_openai_callback
from langchain_community.vectorstores import PGVector

from htmlTemplates import css, bot_template, user_template


log_file_path = path.join(getcwd(), "music-app-logs.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.FileHandler(log_file_path)]
)

# Enable API Keys, DB + Tesseract connection strings from the `.env` file
load_dotenv()

# Initialize session state
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

def ocr_on_pdf(pdf_path):
    """
    Perform OCR on PDFs that cannot have their text extracted by PyPDF2
    """
    try:
        pytesseract.pytesseract.tesseract_cmd = r"{}".format(getenv("TESSERACT_PATH"))
        logging.info(f"Tesseract Path: {pytesseract.pytesseract.tesseract_cmd}\n")
        
        # Convert PDF to images
        images = convert_from_path(pdf_path)
        
        # Initialize an empty string to store the extracted text
        extracted_text = ""

        # Loop through each image and extract text
        for image in images:
            text = pytesseract.image_to_string(image)
            extracted_text += text + '\n'

        return extracted_text
    
    except FileNotFoundError as fnf_error:
        logging.error(f"File not found: {pdf_path}. Error: {fnf_error}")
    except pytesseract.TesseractError as tess_error:
        logging.error(f"Tesseract OCR failed. Error: {tess_error}")
    except Exception as e:
        logging.error(f"Unexpected error during OCR on PDF: {pdf_path}. Error: {e}")
    return ""

def get_pdf_text(pdf_docs):
    text = ""
    pdf_texts = [] 

    for pdf in pdf_docs:
        try:
            # Save the contents of the uploaded PDF to a temporary file
            with tempfile.NamedTemporaryFile(delete=False) as temp_pdf:
                temp_pdf.write(pdf.read())
                temp_pdf_path = temp_pdf.name

            # Check if the PDF file is empty
            if getsize(temp_pdf_path) == 0:
                logging.warning(f"The PDF file '{pdf.name}' is empty.")
                continue  # Skip processing empty PDF files

            pdf_reader = PdfReader(temp_pdf_path)
            text_from_pdf = ""
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_from_pdf += page_text

            pdf_texts.append((temp_pdf_path, text_from_pdf))
            logging.info(f"Appended text from PDF: {pdf.name}. Total PDFs processed: {len(pdf_texts)}")

        except FileNotFoundError as fnf_error:
            logging.error(f"File not found: {pdf.name}. Error: {fnf_error}")
        except Exception as e:
            logging.error(f"Error processing PDF: {pdf.name}. Error: {e}")
            continue

        text += text_from_pdf

    # Check which PDF files need OCR (based on empty text)
    pdf_files_for_ocr = [pdf_path for pdf_path, pdf_text in pdf_texts if not pdf_text]
    logging.info(f"PDF files requiring OCR: {len(pdf_files_for_ocr)}")

    # Perform OCR on the PDF files that need it
    for temp_pdf_path in pdf_files_for_ocr:
        text += ocr_on_pdf(temp_pdf_path)
        logging.info(f"Performed OCR on PDF: {temp_pdf_path}")

    logging.info(f"Total extracted text length: {len(text)}")
    return text

# chunk size extracted text using LangChain's text splitter
def get_text_chunks(text):
    text_splitter = CharacterTextSplitter(
        separator="\n", 
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )
    chunks = text_splitter.split_text(text)
    return chunks
    logging.info(f"The ammount of chunks created is: {len(chunks)}")

def get_vectorstore(text_chunks):
    """
    Convert the extracted text chunks into vectors and send them to the database
    """

    # check that text values are being passed:
    chunk_data_types = [type(c) for c in text_chunks]
    logging.info(f"Data types in text_chunks: {chunk_data_types}\n")
    for c in text_chunks:
        if not isinstance (c, str):
            raise TypeError(f"Chunk {c} is NOT a string\n")

    # Instantiate the OpenAIEmbeddings Class
    embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
    # Convert 'text chunks' into Document objects for PGVector, and store it in a list
    documents_from_text_chunks = [Document(page_content=chunk) for chunk in text_chunks]

    #PGVector set up
    db = PGVector.from_documents(
    embedding=embeddings,
    documents=documents_from_text_chunks,
    collection_name=getenv("PGVECTOR_COLLECTION_NAME"), 
    connection_string=getenv("PGVECTOR_CONNECTION_STRING"),
)
    
    logging.debug("Creating vector store")
    logging.info(f"This is the amount of embeddings created: {len(documents_from_text_chunks)}\n")
    return db

def get_conversation_chain(vectorstore):
    """
    Create a conversation chain
    """
    llm = ChatOpenAI(model_name="gpt-4")
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    conversation_chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=vectorstore.as_retriever(),
        memory=memory
    )
    return conversation_chain


def handle_userinput(user_question):
    if st.session_state.chat_history is None:
        # User has not uploaded any PDFs, so we need to handle the question accordingly
        if st.session_state.vectorstore is None:
            st.warning("Please upload PDFs first or wait until the database is initialized.")
        else:
            # User can ask questions based on the existing data in the database
            # track token usage:
            with get_openai_callback() as cb: #This is where I updated the 'invoke'
                response = st.session_state.conversation({"question": user_question})
                st.session_state.chat_history = response["chat_history"]
                logging.info(f"This is the 'OpenAi Token Usage' information:\n\t{cb}")

            # loop through the chat history with an index and the context of the index
            # adding the User + Bot CSS templates
            for i, message in enumerate(st.session_state.chat_history):
                if i % 2 == 0: # Mod 2 for the odd messages
                    st.write(user_template.replace("{{MSG}}", message.content), unsafe_allow_html=True)
                elif i % 2 != 0: # even messages for the Bot response
                    st.write(bot_template.replace("{{MSG}}", message.content), unsafe_allow_html=True)
    else:
        # User has uploaded PDFs, so we can proceed with the conversation
        # track token usage:
        with get_openai_callback() as cb:
            response = st.session_state.conversation({"question": user_question})
            st.session_state.chat_history = response["chat_history"]
            logging.info(f"This is the 'OpenAi Token Usage' information:\n\t{cb}")

        # loop through the chat history with an index and the context of the index
        # adding the User + Bot CSS templates
        for i, message in enumerate(st.session_state.chat_history):
            if i % 2 == 0: # Mod 2 for the odd messages
                st.write(user_template.replace("{{MSG}}", message.content), unsafe_allow_html=True)
            elif i % 2 != 0: # even messages for the Bot response
                st.write(bot_template.replace("{{MSG}}", message.content), unsafe_allow_html=True)

def clear_chat_history():
    logging.info("Clearing the chat history because the user pressed the 'Clear Chat History Button'\n")
    st.session_state.chat_history = [] # Clear chat history list
    st.session_state.conversation = None # Reset the conversation chain
    st.rerun()

def main():
    prog_start_time = time()
    # Streamlit GUI - Page Configuration:
    st.set_page_config(page_title="Chat with Music Gear Manuals", page_icon=":notes:")
    
    # Adding the CSS template here:
    st.write(css, unsafe_allow_html=True)

    # Initialize vectorstore if not already initialized
    if "vectorstore" not in st.session_state:
        st.session_state.vectorstore = None

    # Establish connection with PGVector database
    vectorstore = get_vectorstore([])
    st.session_state.vectorstore = vectorstore

    # Initialize conversation chain if not already initialized
    if "conversation" not in st.session_state or st.session_state.conversation is None:
        st.session_state.conversation = get_conversation_chain(vectorstore)

    st.header("Chat with Music Gear Manuals :notes:")
    # Store the value from the user input question
    user_question = st.text_input("Ask me a question about any music equipment that can be answered from the manufacturer's official manual:")
    if user_question:
        handle_userinput(user_question)

    # Display "Clear Chat History" button
    if st.button("Clear Chat History"):
        clear_chat_history()
    
    # Add a sidebar where the user can upload PDFs:
    with st.sidebar:
        st.subheader("Your PDF Manuals")
        pdf_docs = st.file_uploader("Upload your PDFs here and click 'Process PDF'", accept_multiple_files=True)
        if st.button("Process PDF"):
            with st.spinner("Processing"):
                # Create a placeholder to display text chunks
                text_chunks_placeholder = st.empty()
                
                # Process PDF here and display text chunks
                for pdf in pdf_docs:
                    raw_text = get_pdf_text([pdf])
                    text_chunks = get_text_chunks(raw_text)
                    text_chunks_placeholder.write(text_chunks)  # Display text chunks

                # Create a progress bar after displaying text chunks
                progress_text = "Processing PDFs..."
                progress_bar = st.empty()
                
                # Calculate the total number of PDFs for processing
                total_pdfs = len(pdf_docs)
                
                # Iterate through each PDF and update the progress bar accordingly
                for i, pdf in enumerate(pdf_docs):
                    # Calculate progress percentage
                    progress_percent = (i + 1) / total_pdfs
                
                    # Update progress bar
                    progress_bar.progress(progress_percent, text=progress_text)
                
                    # Process PDF here
                    raw_text = get_pdf_text([pdf])
                    text_chunks = get_text_chunks(raw_text)
                    vectorstore = get_vectorstore(text_chunks)
                    st.session_state.vectorstore = vectorstore  # Store vectorstore in session state
                    st.session_state.conversation = get_conversation_chain(vectorstore)
                    
                    # Add Progress Bar delay
                    sleep(4.0)
                
                # Empty the progress bar after processing
                progress_bar.empty()

                # Program execution time
                prog_end_time = time()
                prog_execution_time = prog_end_time - prog_start_time 
                # Convert into minutes and seconds
                minutes, seconds = divmod(prog_execution_time, 60)
                # Log execution time
                logging.info(f"The script's execution time is: {int(minutes)} minutes and {seconds: .2f} seconds \n")

    
if __name__ == '__main__':
    main()