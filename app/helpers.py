from . import mail
from flask import current_app, flash
from flask_mail import Message
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, From, To
import os
from werkzeug.utils import secure_filename
import uuid
import boto3
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
import qrcode
from PIL import Image, ImageDraw, ImageFont
import io
import tempfile
import math
from pillow_heif import register_heif_opener

# Register HEIF opener to enable HEIC support in PIL
register_heif_opener()



# US State abbreviation to full name mapping
STATE_ABBREVIATION_MAP = {
    'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas', 'CA': 'California',
    'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware', 'FL': 'Florida', 'GA': 'Georgia',
    'HI': 'Hawaii', 'ID': 'Idaho', 'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa',
    'KS': 'Kansas', 'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
    'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi', 'MO': 'Missouri',
    'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada', 'NH': 'New Hampshire', 'NJ': 'New Jersey',
    'NM': 'New Mexico', 'NY': 'New York', 'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio',
    'OK': 'Oklahoma', 'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
    'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah', 'VT': 'Vermont',
    'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia', 'WI': 'Wisconsin', 'WY': 'Wyoming',
    'DC': 'District of Columbia', 'PR': 'Puerto Rico', 'VI': 'Virgin Islands', 'AS': 'American Samoa',
    'GU': 'Guam', 'MP': 'Northern Mariana Islands'
}


def get_state_full_name(abbreviation):
    """
    Convert state abbreviation to full state name
    
    Args:
        abbreviation: Two-letter state abbreviation (e.g., 'CA', 'NY')
    
    Returns:
        Full state name (e.g., 'California', 'New York') or the abbreviation if not found
    """
    return STATE_ABBREVIATION_MAP.get(abbreviation.upper() if abbreviation else '', abbreviation)


# Send mail function
def send_email(to, subject, html_content, attachments=None):
    """
    Send email with optional attachments
    
    Args:
        to: Email recipient(s) - can be string or list
        subject: Email subject
        html_content: HTML content of email
        attachments: List of dictionaries with 'filename' and 'content' keys
    """
    # Ensure 'to' is always a list
    if isinstance(to, str):
        to = [to]
    
    # Use Mailtrap for development
    if current_app.config['MAIL_SERVER'] == 'smtp.mailtrap.io':
        # Send mail to each user
        with mail.connect() as conn:
            for recipient in to:
                msg = Message(subject, sender=current_app.config['MAIL_USERNAME'], recipients=[recipient])
                msg.html = html_content  # Set the HTML content of the email directly
                
                # Add attachments if provided
                if attachments:
                    for attachment in attachments:
                        msg.attach(
                            attachment['filename'],
                            attachment.get('content_type', 'application/pdf'),
                            attachment['content']
                        )
                
                conn.send(msg)

    # Use SendGrid for staging/production
    else:
        try:
            sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
            
            for recipient in to:
                message = Mail(
                    from_email=From(email="noreply@reportthatpantry.com", name="Report That Pantry"),  # Updated From email
                    to_emails=To(recipient),  # Send to one recipient at a time
                    subject=subject,
                    html_content=html_content
                )
                
                # Add attachments if provided
                if attachments:
                    from sendgrid.helpers.mail import Attachment, FileContent, FileName, FileType, Disposition
                    import base64
                    
                    for attachment in attachments:
                        encoded_content = base64.b64encode(attachment['content']).decode()
                        attachment_obj = Attachment(
                            FileContent(encoded_content),
                            FileName(attachment['filename']),
                            FileType(attachment.get('content_type', 'application/pdf')),
                            Disposition('attachment')
                        )
                        message.attachment = attachment_obj
                
                response = sg.send(message)
                print(f"SendGrid response: {response.status_code}")
                if response.status_code != 202:
                    print(f"SendGrid error: {response.body}")

        except Exception as e:
            print(f"SendGrid error: {e}")
            if hasattr(e, 'message'):
                print(f"Error message: {e.message}")

            
# Determines if file submitted is allowed
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif', 'heic', 'heif'}


def upload_photo_to_s3(photo, location_id):
    """Uploads a photo to the specified S3 bucket under a location-specific path.

    Args:
        photo (werkzeug.FileStorage): The photo file object.
        location_id (int): The ID of the location to associate the photo with.

    Returns:
        str or None: The S3 key (relative path) of the uploaded photo, or None if the upload fails.
    """
    if not photo or not allowed_file(photo.filename):
        return None  # Early exit if no photo or invalid type

    try:
        filename = secure_filename(photo.filename)
        original_extension = os.path.splitext(filename)[1]
        
        # Handle HEIC conversion
        if is_heic_file(photo.filename):
            print(f"Converting HEIC file: {filename}")
            converted_data = convert_heic_to_jpeg(photo)
            if converted_data is None:
                print("Failed to convert HEIC file")
                return None
            
            # Update filename and extension for converted file
            base_name = os.path.splitext(filename)[0]
            filename = f"{base_name}.jpg"
            original_extension = '.jpg'
            photo_data = converted_data
        else:
            # Use original file for non-HEIC formats
            photo.seek(0)  # Reset file pointer
            photo_data = photo

        unique_filename = f"{uuid.uuid4().hex}{original_extension}"

        s3 = boto3.client(
            's3',
            aws_access_key_id=current_app.config['S3_KEY'],
            aws_secret_access_key=current_app.config['S3_SECRET']
        )

        s3_key = os.path.join(current_app.config['FLASK_ENV'], 'uploads', str(location_id), unique_filename)
        s3.upload_fileobj(photo_data, current_app.config['S3_BUCKET'], s3_key)
        
        print(f"Photo uploaded to: {s3_key}")

        return s3_key  # Return the relative path for storage in the database

    except Exception as e:
        print(f"Error uploading photo to S3: {e}")
        flash("There was an error uploading the photo.", "error")
        return None


def delete_photo_from_s3(s3_key):
    """Deletes a photo from the S3 bucket based on its key.

    Args:
        s3_key (str): The S3 key (path) of the object to delete.

    Returns:
        bool: True if the deletion was successful, False otherwise.
    """
    try:
        s3 = boto3.client('s3',
                          aws_access_key_id=current_app.config['S3_KEY'],
                          aws_secret_access_key=current_app.config['S3_SECRET'])

        s3.delete_object(Bucket=current_app.config['S3_BUCKET'], Key=s3_key)
        print(f"Deleted photo from S3: {s3_key}")
        return True
    except Exception as e:
        print(f"Error deleting photo from S3: {e}")
        return False  # Indicate failure


def generate_qr_poster_pdf(location_name, location_id, report_url):
    """
    Generate a PDF poster with QR code for a pantry location
    Based on the orange poster design template
    
    Args:
        location_name (str): Name of the location
        location_id (int): ID of the location
        report_url (str): URL for the QR code
    
    Returns:
        bytes: PDF content as bytes
    """
    try:
        # Create a temporary file to store the PDF
        pdf_buffer = io.BytesIO()
        
        # Create canvas for PDF (letter size: 8.5" x 11")
        c = canvas.Canvas(pdf_buffer, pagesize=letter)
        width, height = letter  # 612 x 792 points
        
        # Orange background color (matching the design)
        orange_color = colors.Color(255/255, 98/255, 25/255)  # Bright orange
        c.setFillColor(orange_color)
        c.rect(0, 0, width, height, fill=1)
        
        # Title text - "Help Keep This Little Free Pantry Stocked!"
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 36)
        
        # Break title into multiple lines for better fit
        title_lines = [
            "Help Keep This Little",
            "Free Pantry Stocked!"
        ]
        
        y_pos = height - 80
        for line in title_lines:
            text_width = c.stringWidth(line, "Helvetica-Bold", 36)
            c.drawString((width - text_width) / 2, y_pos, line)
            y_pos -= 45
        
        # Pantry name/address
        c.setFont("Helvetica-Bold", 32)
        pantry_text = location_name if location_name else f"Pantry #{location_id}"
        pantry_width = c.stringWidth(pantry_text, "Helvetica-Bold", 32)
        c.drawString((width - pantry_width) / 2, y_pos - 30, pantry_text)
        
        # Generate QR code (larger size to match design)
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(report_url)
        qr.make(fit=True)
        
        # Create QR code image
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        # Save QR code to temporary file
        qr_buffer = io.BytesIO()
        qr_img.save(qr_buffer, format='PNG')
        qr_buffer.seek(0)
        
        # Add QR code to PDF (centered, large size)
        qr_size = 200
        qr_x = (width - qr_size) / 2
        qr_y = height - 420
        c.drawImage(ImageReader(qr_buffer), qr_x, qr_y, qr_size, qr_size)
        
        # Add decorative elements to match the original design
        
        # Left star burst (top left of QR code area)
        c.setFillColor(colors.Color(200/255, 80/255, 20/255))  # Darker orange
        star_x = qr_x - 80
        star_y = qr_y + 120
        
        # Draw star burst with multiple lines
        c.setStrokeColor(colors.Color(200/255, 80/255, 20/255))
        c.setLineWidth(3)
        for i in range(12):
            angle = i * 30 * 3.14159 / 180  # 30 degree increments
            length = 25 if i % 2 == 0 else 15  # Alternating lengths
            x1 = star_x + length * math.cos(angle)
            y1 = star_y + length * math.sin(angle)
            c.line(star_x, star_y, x1, y1)
        
        # Right star burst (top right of QR code area)
        star_x2 = qr_x + qr_size + 80
        star_y2 = qr_y + 120
        c.setStrokeColor(colors.Color(255/255, 140/255, 60/255))  # Lighter orange
        for i in range(8):
            angle = i * 45 * 3.14159 / 180  # 45 degree increments
            length = 20 if i % 2 == 0 else 12
            x1 = star_x2 + length * math.cos(angle)
            y1 = star_y2 + length * math.sin(angle)
            c.line(star_x2, star_y2, x1, y1)
        
        # Blue flower shape (bottom left of QR code)
        c.setFillColor(colors.Color(30/255, 144/255, 255/255))  # Bright blue
        flower_x = qr_x - 60
        flower_y = qr_y - 30
        
        # Draw flower petals as overlapping circles
        petal_positions = [
            (0, 15), (13, 7), (13, -7), (0, -15), (-13, -7), (-13, 7)
        ]
        for dx, dy in petal_positions:
            c.circle(flower_x + dx, flower_y + dy, 12, fill=1)
        
        # Flower center
        c.setFillColor(colors.Color(0/255, 100/255, 200/255))  # Darker blue
        c.circle(flower_x, flower_y, 8, fill=1)
        
        # Right decorative element (cloud-like shape)
        c.setStrokeColor(colors.Color(200/255, 60/255, 20/255))
        c.setLineWidth(4)
        cloud_x = qr_x + qr_size + 60
        cloud_y = qr_y - 40
        
        # Draw cloud outline with curves
        # This is a simplified cloud - in a real implementation you'd use bezier curves
        c.circle(cloud_x, cloud_y, 15, fill=0, stroke=1)
        c.circle(cloud_x + 12, cloud_y + 5, 12, fill=0, stroke=1)
        c.circle(cloud_x - 12, cloud_y + 5, 10, fill=0, stroke=1)
        c.circle(cloud_x, cloud_y + 15, 8, fill=0, stroke=1)
        
        # Instructions text below QR code
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 18)
        instruction_text = "Scan the QR code to let others know the"
        instruction_width = c.stringWidth(instruction_text, "Helvetica-Bold", 18)
        c.drawString((width - instruction_width) / 2, qr_y - 80, instruction_text)
        
        instruction_text2 = "current status of this food pantry."
        instruction_width2 = c.stringWidth(instruction_text2, "Helvetica-Bold", 18)
        c.drawString((width - instruction_width2) / 2, qr_y - 105, instruction_text2)
        
        # Description text
        c.setFont("Helvetica", 16)
        desc_text1 = "ReportThatPantry helps little free pantries stay"
        desc_width1 = c.stringWidth(desc_text1, "Helvetica", 16)
        c.drawString((width - desc_width1) / 2, qr_y - 140, desc_text1)
        
        desc_text2 = "full with the help of AI and data analytics."
        desc_width2 = c.stringWidth(desc_text2, "Helvetica", 16)
        c.drawString((width - desc_width2) / 2, qr_y - 160, desc_text2)
        
        # Website URL at bottom
        c.setFont("Helvetica", 14)
        url_text = "Visit www.ReportThatPantry.org to learn more"
        url_width = c.stringWidth(url_text, "Helvetica", 14)
        c.drawString((width - url_width) / 2, 60, url_text)
        
        # Save PDF
        c.save()
        
        # Get PDF content
        pdf_buffer.seek(0)
        pdf_content = pdf_buffer.getvalue()
        pdf_buffer.close()
        
        return pdf_content
        
    except Exception as e:
        print(f"Error generating QR poster PDF: {e}")
        return None


def convert_heic_to_jpeg(file_obj, max_width=1200, max_height=1200, quality=85):
    """
    Convert HEIC/HEIF image to JPEG format with optional resizing
    
    Args:
        file_obj: File object (werkzeug.FileStorage)
        max_width: Maximum width for resizing (default: 1200px)
        max_height: Maximum height for resizing (default: 1200px)  
        quality: JPEG quality (default: 85)
    
    Returns:
        io.BytesIO: JPEG image data, or None if conversion fails
    """
    try:
        # Read the original file content
        file_obj.seek(0)  # Reset file pointer
        image_data = file_obj.read()
        
        # Open with PIL (pillow-heif will handle HEIC)
        with Image.open(io.BytesIO(image_data)) as img:
            # Convert to RGB (JPEG doesn't support RGBA)
            if img.mode in ('RGBA', 'LA', 'P'):
                # Create a white background for transparent images
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                rgb_img.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                img = rgb_img
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Resize if image is too large
            original_width, original_height = img.size
            if original_width > max_width or original_height > max_height:
                # Calculate new dimensions maintaining aspect ratio
                ratio = min(max_width / original_width, max_height / original_height)
                new_width = int(original_width * ratio)
                new_height = int(original_height * ratio)
                
                print(f"Resizing HEIC image from {original_width}x{original_height} to {new_width}x{new_height}")
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Save as JPEG to BytesIO
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=quality, optimize=True)
            output.seek(0)
            
            return output
            
    except Exception as e:
        print(f"Error converting HEIC to JPEG: {e}")
        return None


def is_heic_file(filename):
    """Check if file is HEIC/HEIF format"""
    if not filename:
        return False
    extension = filename.rsplit('.', 1)[-1].lower()
    return extension in {'heic', 'heif'}