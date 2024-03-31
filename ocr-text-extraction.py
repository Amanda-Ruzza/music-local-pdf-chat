import os
from dotenv import load_dotenv 
from pdf2image import convert_from_path
import pytesseract

"""
This is an OCR test script. This code was refactored and added to the main `roland-app.py`

"""

# Tesseract OCR engine executable
load_dotenv()
pytesseract.pytesseract.tesseract_cmd = r"{}".format(os.getenv("TESSERACT_PATH"))
print(f"Tesseract Path: {pytesseract.pytesseract.tesseract_cmd}")

def extract_text_from_pdf(pdf_filename):
    # Construct the full path to the PDF file
    cwd = os.getcwd()
    print(f"This is the CWD: {cwd}")
    pdf_path = os.path.join(cwd, pdf_filename)
    print(f"This is the PDF Path: {pdf_path}")

    # Convert PDF to images
    try:
        images = convert_from_path(pdf_path)
    except Exception as e:
        print(f"Error converting PDF to images: {e}")
        return ""

    # Initialize an empty string to store the extracted text
    extracted_text = ""

    # Loop through each image and extract text
    for image in images:
        text = pytesseract.image_to_string(image)
        extracted_text += text + '\n'

    return extracted_text

if __name__ == "__main__":
    pdf_filename = "rock-paper-scissors-instructions.pdf"
    extracted_text = extract_text_from_pdf(pdf_filename)
    print(extracted_text)