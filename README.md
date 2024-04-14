# Music Pdf Chat

A PDF Chatbot Application for reading Music Equipment Instruction Manuals :robot:
- - - -

## Application

This is a Python Retrieval-Augmented Generation (RAG) that is able to read multiple PDFs and answer questions inputed into the 'input question' box.
It was designed to run in a local machine, with a focus on open-source tools and uses the following stack:

* Streamlit - Front End
* OpenAi - LLM
* Langchain - Orchestration
* PostgreSQL with the `pgvector` extension - Vector Database
* PyPDF2 - PDF text extraction
* PyTesseract - OCR on AES Encrypted PDFs or PDFs with images in the background that would result in an empty text extraction

- - - -

## Features

* A Langchain `callback` function that calculates 'OpenAi' token usage and prints it to a logger file
* A secure API/TOKEN keys connection hidden in the `.env` file
* A capability to answer questions based on documents that are already vectorized and stored in the database - no need to reupload the same PDFs
* A 'Clear Chat History' button

- - - -

### Future Improvements

* Create a 'Web URL Input' functionality, so that the user has the option to either upload a file or add a PDF web url.
* Create a 'document uploaded' metadata JSON file that will be sent into a NoSQL database so that there is a record of all the PDFs vectorized by the user
* Cloud Native Deployment
  
- - - -

#### Instructions

* Activate local `virtual environment` on terminal:

    `source roland_venv/bin/activate`

* Add the `OpenAI`, `PGVector` and `tesseract` connection tokens in the `.env` file

* `PGVector` local connection set up:
  [WRITE DOWN THE INSTRUCTIONS HERE]

* Start the `streamlit` application on terminal:

      `streamlit run roland-app.py`



##### Required Packages

```
InstructorEmbedding       1.0.1
langchain                 0.1.16
langchain-community       0.0.32
langchain-core            0.1.42
langchain-openai          0.0.6
langchain-text-splitters  0.0.1
langsmith                 0.1.47
openai                    1.12.0
pdf2image                 1.17.0
pgvector                  0.2.5
SQLAlchemy                2.0.27
streamlit                 1.31.1
PyPDF2                    3.0.1
pytesseract               0.3.10
python-dotenv             1.0.1
tiktoken                  0.6.0
tokenizers                0.15.2
```
