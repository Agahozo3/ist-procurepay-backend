
import pdfplumber
import pytesseract
from PyPDF2 import PdfReader, PdfWriter
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import re

# -----------------------------
# Extract text from PDF
# -----------------------------
def extract_text_from_pdf(file):
    """
    Extract text from PDF using pdfplumber and fallback to pytesseract if necessary.
    file: InMemoryUploadedFile or file path
    Returns: str
    """
    text = ""
    try:
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
        if not text.strip():
            # fallback: OCR with pytesseract
            from PIL import Image
            import pdf2image
            images = pdf2image.convert_from_path(file)
            for image in images:
                text += pytesseract.image_to_string(image)
    except Exception as e:
        print(f"Error extracting PDF text: {e}")
    return text

# -----------------------------
# Extract key data from Proforma
# -----------------------------
def extract_proforma_data(text):
    """
    Extract key fields from proforma invoice text.
    Returns dict with vendor, items, amounts, etc.
    """
    data = {
        "vendor": None,
        "items": [],
        "total_amount": None,
    }

    # Example patterns (adjust based on your PDFs)
    vendor_match = re.search(r"Vendor[:\s]*(.*)", text, re.IGNORECASE)
    total_match = re.search(r"Total[:\s]*\$?([\d,.]+)", text, re.IGNORECASE)
    items_matches = re.findall(r"(\d+)\s+x\s+(.+?)\s+@?\s*\$?([\d,.]+)", text)

    if vendor_match:
        data["vendor"] = vendor_match.group(1).strip()
    if total_match:
        data["total_amount"] = total_match.group(1).replace(",", "")
    for qty, name, price in items_matches:
        data["items"].append({
            "name": name.strip(),
            "quantity": int(qty),
            "unit_price": float(price.replace(",", "")),
        })
    return data

# -----------------------------
# Generate Purchase Order PDF
# -----------------------------
def generate_po_pdf(po_data):
    """
    Generate a simple Purchase Order PDF using ReportLab
    po_data: dict with vendor, items, total_amount, terms, etc.
    Returns: BytesIO object of PDF
    """
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, f"Purchase Order")
    y -= 40

    c.setFont("Helvetica", 12)
    c.drawString(50, y, f"Vendor: {po_data.get('vendor', '')}")
    y -= 30
    c.drawString(50, y, f"Total Amount: ${po_data.get('total_amount', '')}")
    y -= 30

    c.drawString(50, y, "Items:")
    y -= 20
    for item in po_data.get("items", []):
        c.drawString(60, y, f"{item['quantity']} x {item['name']} @ ${item['unit_price']}")
        y -= 20

    if po_data.get("terms"):
        y -= 10
        c.drawString(50, y, f"Terms: {po_data['terms']}")

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

# -----------------------------
# Validate Receipt
# -----------------------------
def validate_receipt(receipt_text, po_data):
    """
    Validate receipt against PO data.
    Checks: vendor, items, quantities, prices.
    Returns: dict with validation results and discrepancies.
    """
    result = {
        "valid": True,
        "discrepancies": []
    }

    # Check vendor
    vendor_match = re.search(r"Vendor[:\s]*(.*)", receipt_text, re.IGNORECASE)
    receipt_vendor = vendor_match.group(1).strip() if vendor_match else None
    if receipt_vendor != po_data.get("vendor"):
        result["valid"] = False
        result["discrepancies"].append(f"Vendor mismatch: {receipt_vendor} != {po_data.get('vendor')}")

    # Check items
    receipt_items = re.findall(r"(\d+)\s+x\s+(.+?)\s+@?\s*\$?([\d,.]+)", receipt_text)
    po_items = po_data.get("items", [])

    for po_item in po_items:
        match_found = False
        for r_qty, r_name, r_price in receipt_items:
            if po_item["name"].lower() == r_name.strip().lower():
                if int(r_qty) != po_item["quantity"] or float(r_price.replace(",", "")) != po_item["unit_price"]:
                    result["valid"] = False
                    result["discrepancies"].append(
                        f"Item {po_item['name']} mismatch: PO {po_item['quantity']} x {po_item['unit_price']} != Receipt {r_qty} x {r_price}"
                    )
                match_found = True
                break
        if not match_found:
            result["valid"] = False
            result["discrepancies"].append(f"Item {po_item['name']} missing in receipt")

    return result
