import sys
import pytesseract
from PIL import Image
from tabulate import tabulate


pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


# Receive image path argument
image_path = sys.argv[1]

# Extract raw text
text = pytesseract.image_to_string(Image.open(image_path))

# Convert OCR text to rows/columns (simple split)
rows = [line.split() for line in text.split("\n") if line.strip()]

# Print ASCII table to Node console
print(tabulate(rows, tablefmt="grid"))
