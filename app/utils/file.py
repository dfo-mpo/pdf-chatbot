from io import BytesIO
from PyPDF2 import PdfReader, PdfWriter
from fastapi import UploadFile
from reportlab.pdfgen import canvas
from reportlab.pdfbase.pdfmetrics import stringWidth

# adds page numbers to PDFs by recreating them and adding them in the centre of the page
def add_page_numbers(file: UploadFile) -> BytesIO:
    input_bytes = file.file.read()
    input_pdf = BytesIO(input_bytes)
    reader = PdfReader(input_pdf)
    writer = PdfWriter()
    
    for page_num, page in enumerate(reader.pages):  
        # Determine the size of the current page dynamically.  
        width = float(page.mediabox[2])  
        height = float(page.mediabox[3])  

        # Create an in-memory PDF with the page number added.  
        packet = BytesIO()  
        can = canvas.Canvas(packet, pagesize=(width, height))  
        page_number_text = f"Page {page_num + 1}"  
        text_width = stringWidth(page_number_text, "Helvetica", 12)  
        can.setFont("Helvetica", 12)  
        # Centre the page number on the page (horizontally), 20 points from the bottom.  
        can.drawString((width - text_width) / 2, 20, page_number_text)  
        can.save()  

        # Merge the new page number canvas with the original PDF page.  
        packet.seek(0)  
        new_pdf = PdfReader(packet)  
        page.merge_page(new_pdf.pages[0])  
        writer.add_page(page)  

    # Write the modified PDF to a BytesIO object.  
    output_pdf = BytesIO()  
    writer.write(output_pdf)  
    output_pdf.seek(0)  
    return output_pdf  