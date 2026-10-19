from flask_mail import Mail, Message
from models.models import User
from config.config import Config

class EmailService:
    """Service for handling email operations"""
    
    def __init__(self, app=None):
        self.mail = None
        if app:
            self.init_app(app)
        self.user_model = User()
    
    def init_app(self, app):
        """Initialize email service with Flask app"""
        self.mail = Mail(app)
    
    def send_query_response_notification(self, user_id, question, response):
        """Send email notification when query is answered using direct SMTP"""
        try:
            user = self.user_model.find_by_id(user_id)
            if not user or not user.get("email"):
                print("User or email not found")
                return False
            
            email = user["email"]
            
            # Simple text cleaning
            def clean_text(text):
                if not text:
                    return ""
                text = str(text)
                # Replace non-breaking spaces and other common Unicode issues
                text = text.replace('\xa0', ' ').replace('\u00a0', ' ')
                text = text.replace('\u2019', "'").replace('\u2018', "'")
                text = text.replace('\u201c', '"').replace('\u201d', '"')
                text = text.replace('\u2013', '-').replace('\u2014', '-')
                # Force ASCII encoding
                return text.encode('ascii', errors='replace').decode('ascii').strip()
            
            question_str = clean_text(question)
            response_str = clean_text(response)
            
            # Create email body
            email_body = f"""Hello,

Your question: "{question_str}"
Has been answered: "{response_str}"

Thank you for your patience!

- Sahayak: The Support Team
"""
            
            # Use direct SMTP to send email
            import smtplib
            from email.mime.text import MIMEText
            
            try:
                # Create email using standard library
                smtp_msg = MIMEText(email_body, 'plain', 'ascii')
                smtp_msg['Subject'] = "Your query has been answered!"
                smtp_msg['From'] = Config.MAIL_USERNAME
                smtp_msg['To'] = email
                
                # Send using SMTP
                server = smtplib.SMTP(Config.MAIL_SERVER, Config.MAIL_PORT)
                server.starttls()
                server.login(Config.MAIL_USERNAME, Config.MAIL_PASSWORD)
                server.send_message(smtp_msg)
                server.quit()
                
                return True
                
            except Exception as smtp_error:
                print(f"✗ SMTP failed: {smtp_error}")
                return False
            
        except Exception as e:
            print(f"Error sending email: {str(e)}")
            return False
    
    def send_welcome_email(self, user_email, username):
        """Send welcome email to new users using direct SMTP"""
        try:
            # Simple text cleaning
            def clean_text(text):
                if not text:
                    return ""
                text = str(text)
                # Replace non-breaking spaces and other common Unicode issues
                text = text.replace('\xa0', ' ').replace('\u00a0', ' ')
                text = text.replace('\u2019', "'").replace('\u2018', "'")
                text = text.replace('\u201c', '"').replace('\u201d', '"')
                text = text.replace('\u2013', '-').replace('\u2014', '-')
                # Force ASCII encoding
                return text.encode('ascii', errors='replace').decode('ascii').strip()
            
            clean_username = clean_text(username)
            
            email_body = f"""Hello {clean_username},

Welcome aboard! we are excited to have you join the Student Query Chatbot platform - your personal assisstant for all academic queries.

Here is what you can do now:
- Ask academic questions anytime, anywhere
- Get instant, accurate responses
- Access your chat history
- Receive email notifications

Thank you for joining us!

- The Support Team
"""
            
            # Use direct SMTP to send email
            import smtplib
            from email.mime.text import MIMEText
            
            try:
                # Create email using standard library
                smtp_msg = MIMEText(email_body, 'plain', 'ascii')
                smtp_msg['Subject'] = "Welcome to Student Chatbot!"
                smtp_msg['From'] = Config.MAIL_USERNAME
                smtp_msg['To'] = user_email
                
                # Send using SMTP
                server = smtplib.SMTP(Config.MAIL_SERVER, Config.MAIL_PORT)
                server.starttls()
                server.login(Config.MAIL_USERNAME, Config.MAIL_PASSWORD)
                server.send_message(smtp_msg)
                server.quit()
                
                return True
                
            except Exception as smtp_error:
                print(f"✗ Welcome email SMTP failed: {smtp_error}")
                return False
            
        except Exception as e:
            print(f"Error sending welcome email: {str(e)}")
            return False
