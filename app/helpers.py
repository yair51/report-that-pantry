from . import mail
from flask import current_app, flash
from flask_mail import Message, Mail
from sendgrid import SendGridAPIClient
import os
from werkzeug.utils import secure_filename
import uuid
import boto3



# Send mail function
def send_email(to, subject, html_content):
    # Use Mailtrap for development
    if current_app.config['MAIL_SERVER'] == 'smtp.mailtrap.io':
        # Send mail to each user
        with mail.connect() as conn:
                for recipient in to:
                    msg = Message(subject, sender=current_app.config['MAIL_USERNAME'], recipients=[recipient])
                    msg.html = html_content  # Set the HTML content of the email directly
                    conn.send(msg)
    # Use SendGrid for staging/production
    else:
        message = Mail(
            from_email=current_app.config['MAIL_USERNAME'],
            to_emails=to,
            subject=subject,
            html_content=html_content
        )
        try:
            sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
            response = sg.send(message)
            print(response.status_code)
            print(response.body)
            print(response.headers)
        except Exception as e:
            print(e.message)

            
# Determines if file submitted is allowed
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}


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
        _, extension = os.path.splitext(filename)
        unique_filename = f"{uuid.uuid4().hex}{extension}"

        s3 = boto3.client(
            's3',
            aws_access_key_id=current_app.config['S3_KEY'],
            aws_secret_access_key=current_app.config['S3_SECRET']
        )

        s3_key = os.path.join(current_app.config['FLASK_ENV'], 'uploads', str(location_id), unique_filename)
        s3.upload_fileobj(photo, current_app.config['S3_BUCKET'], s3_key)
        
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