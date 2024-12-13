import datetime
import requests
import os
import base64
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition

# Load environment variables from .env file
load_dotenv()

# Retrieve values from environment variables
DOLIBARR_BASE_URL = os.environ.get("DOLIBARR_BASE_URL")
API_KEY = os.environ.get("API_KEY")
SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")

# Set up headers for authentication with Dolibarr
headers = {
    "DOLAPIKEY": API_KEY,
    "Accept": "application/json"
}

# Get today's date in YYYYMMDD format
today = datetime.date.today()
formatted_today = today.strftime('%Y%m%d')

# Create the endpoint with sqlfilters
invoices_endpoint = f"{DOLIBARR_BASE_URL}/api/index.php/invoices"

all_invoices = []
page = 0
limit = 300  # Adjust limit if needed
print(f"formatted_today: {formatted_today}")
"(t.datec:>:'{formatted_today}') AND "
while True:
    invoices_params = {
        "sqlfilters": f"(t.datec:>:'{formatted_today}180000') AND (t.datec:<:'{formatted_today}235959') AND (vendorapproved:LIKE:Yes)",  # Filter for today's invoices
        "limit": limit,
        "page": page
    }

    try:
        # Fetch invoices for the current page
        response = requests.get(invoices_endpoint, headers=headers, params=invoices_params)
        print(f"Fetching page {page}: {response.url}")
        response.raise_for_status()
        invoices = response.json()

        if not invoices:
            print(f"No more invoices found. Exiting loop.")
            break

        all_invoices.extend(invoices)
        print(f"Fetched {len(invoices)} invoices from page {page}.")

        # Increment page number for next request
        page += 1

    except requests.RequestException as e:
        print(f"Error with the request: {e}")
        break
    except Exception as e:
        print(f"An error occurred: {e}")
        break

# Process all collected invoices
print(f"Total invoices collected: {len(all_invoices)}")

for invoice in all_invoices:
    if invoice.get('array_options', {}).get("options_vendorapproved", "") == 'Yes':
        invoice_id = invoice.get("id")
        invoice_ref = invoice.get("ref")
        invoice_total = invoice.get("total_ttc")
        print(f"Invoice Found - ID: {invoice_id}, Ref: {invoice_ref}, Total: {invoice_total}")

        try:
            # Download the PDF
            download_pdf_endpoint = f"{DOLIBARR_BASE_URL}/api/index.php/documents/download"
            download_pdf_params = {
                "modulepart": "facture",
                "original_file": f"{invoice_ref}/{invoice_ref}.pdf"  # Adjust if necessary
            }
            pdf_file_response = requests.get(download_pdf_endpoint, headers=headers, params=download_pdf_params)
            print(f"PDF download URL: {pdf_file_response.url}")
            pdf_file_response.raise_for_status()
            pdf_file = pdf_file_response.json().get('content')
            print(f"PDF content retrieved.")

            # Base64 encode the PDF for SendGrid
            decoded_file = base64.b64decode(pdf_file)
            encode_pdf_file = base64.b64encode(decoded_file).decode('utf-8')

            # Create attachment
            attachment = Attachment(
                FileContent(encode_pdf_file),
                FileName(f"{invoice_ref}.pdf"),
                FileType("application/pdf"),
                Disposition("attachment")
            )

            # Construct the email
            message = Mail(
                from_email='noreply@manpowerfpl.com',  # Replace with sender email
                to_emails=['ccantillo1096@gmail.com', "cengroba@gmail.com"],  # Replace with recipient emails
                subject=f'Invoice {invoice_ref} PDF',
                html_content='<strong>Your invoice is attached.</strong>'
            )
            message.attachment = attachment

            # Send email via SendGrid
            sg = SendGridAPIClient(SENDGRID_API_KEY)
            email_response = sg.send(message)
            print(f"Email sent. Status code: {email_response.status_code}")

        except requests.RequestException as e:
            print(f"Error downloading the PDF: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")

print("All invoices processed.")
