"""
Email service for sending notifications
"""
from flask import current_app
from flask_mail import Message
from extensions import mail
from threading import Thread
import logging

logger = logging.getLogger(__name__)


def send_async_email(app, msg):
    """Send email asynchronously"""
    with app.app_context():
        try:
            mail.send(msg)
            logger.info(f"Email sent successfully to {msg.recipients}")
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")


def send_email(subject, recipients, text_body, html_body=None, sender=None):
    """
    Send email (wrapper function)
    
    Args:
        subject: Email subject
        recipients: List of recipient emails
        text_body: Plain text body
        html_body: HTML body (optional)
        sender: Sender email (optional, uses default from config)
    
    Returns:
        Boolean indicating success
    """
    try:
        # Check if email is configured
        if not current_app.config.get('MAIL_USERNAME'):
            logger.warning("Email not configured. Skipping email send.")
            return False
        
        msg = Message(
            subject=f"{current_app.config['MAIL_SUBJECT_PREFIX']} {subject}",
            recipients=recipients if isinstance(recipients, list) else [recipients],
            sender=sender or current_app.config['MAIL_DEFAULT_SENDER']
        )
        msg.body = text_body
        msg.html = html_body or text_body
        
        # Send asynchronously
        app = current_app._get_current_object()
        Thread(target=send_async_email, args=(app, msg)).start()
        
        return True
    except Exception as e:
        logger.error(f"Error preparing email: {str(e)}")
        return False


class EmailService:
    """Email service for trip planner notifications"""
    
    @staticmethod
    def send_welcome_email(user):
        """Send welcome email to new user"""
        subject = "Welcome to Trip Planner!"
        
        text_body = f"""
Hi {user.username},

Welcome to Trip Planner! We're excited to help you plan your next adventure.

You can now:
• Create and manage trips
• Collaborate with friends and family
• Track expenses and budgets in INR (₹)
• Plan activities and itineraries
• Get weather updates

Start planning your first trip today!

Best regards,
The Trip Planner Team
        """
        
        html_body = f"""
<html>
  <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
      <h2 style="color: #4CAF50;">Welcome to Trip Planner! 🎉</h2>
      <p>Hi <strong>{user.username}</strong>,</p>
      <p>Welcome to Trip Planner! We're excited to help you plan your next adventure.</p>
      
      <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
        <h3 style="margin-top: 0;">What you can do:</h3>
        <ul>
          <li>✈️ Create and manage trips</li>
          <li>👥 Collaborate with friends and family</li>
          <li>💰 Track expenses and budgets in INR (₹)</li>
          <li>📅 Plan activities and itineraries</li>
          <li>🌤️ Get weather updates</li>
        </ul>
      </div>
      
      <p><strong>Start planning your first trip today!</strong></p>
      
      <p style="margin-top: 30px;">Best regards,<br>The Trip Planner Team</p>
      
      <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
      <p style="font-size: 12px; color: #666;">
        This is an automated email. Please do not reply.
      </p>
    </div>
  </body>
</html>
        """
        
        return send_email(subject, user.email, text_body, html_body)
    
    @staticmethod
    def send_trip_invitation(trip, inviter, invitee):
        """Send trip invitation email"""
        subject = f"You're invited to join '{trip.title}'"
        
        text_body = f"""
Hi {invitee.username},

{inviter.username} has invited you to collaborate on their trip: {trip.title}

Trip Details:
• Destination: {trip.destination}
• Dates: {trip.start_date} to {trip.end_date}
• Budget: ₹{trip.budget or 'Not set'}

Login to your Trip Planner account to accept the invitation and start planning together!

Best regards,
The Trip Planner Team
        """
        
        html_body = f"""
<html>
  <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
      <h2 style="color: #4CAF50;">Trip Invitation 🎫</h2>
      <p>Hi <strong>{invitee.username}</strong>,</p>
      <p><strong>{inviter.username}</strong> has invited you to collaborate on their trip:</p>
      
      <div style="background-color: #f5f5f5; padding: 20px; border-radius: 5px; margin: 20px 0;">
        <h3 style="margin-top: 0; color: #2196F3;">{trip.title}</h3>
        <p><strong>📍 Destination:</strong> {trip.destination}</p>
        <p><strong>📅 Dates:</strong> {trip.start_date} to {trip.end_date}</p>
        <p><strong>💰 Budget:</strong> ₹{trip.budget or 'Not set'}</p>
        {f'<p><strong>📝 Description:</strong> {trip.description}</p>' if trip.description else ''}
      </div>
      
      <p><strong>Login to your Trip Planner account to accept the invitation and start planning together!</strong></p>
      
      <p style="margin-top: 30px;">Best regards,<br>The Trip Planner Team</p>
    </div>
  </body>
</html>
        """
        
        return send_email(subject, invitee.email, text_body, html_body)
    
    @staticmethod
    def send_expense_notification(expense, trip, recipients):
        """Notify collaborators of new expense"""
        from utils.currency_helper import format_currency
        
        subject = f"New expense added to '{trip.title}'"
        
        amount_formatted = format_currency(expense.amount, expense.currency)
        
        text_body = f"""
A new expense has been added to {trip.title}

Expense Details:
• Title: {expense.title}
• Amount: {amount_formatted}
• Category: {expense.category_id or 'Uncategorized'}
• Date: {expense.expense_date}
• Paid by: {expense.payer.username}

{f'Description: {expense.description}' if expense.description else ''}

Login to view full details and manage your trip expenses.

Best regards,
The Trip Planner Team
        """
        
        html_body = f"""
<html>
  <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
      <h2 style="color: #4CAF50;">New Expense Added 💸</h2>
      <p>A new expense has been added to <strong>{trip.title}</strong></p>
      
      <div style="background-color: #f5f5f5; padding: 20px; border-radius: 5px; margin: 20px 0;">
        <h3 style="margin-top: 0; color: #FF5722;">{expense.title}</h3>
        <p><strong>💰 Amount:</strong> {amount_formatted}</p>
        <p><strong>📂 Category:</strong> {expense.category_id or 'Uncategorized'}</p>
        <p><strong>📅 Date:</strong> {expense.expense_date}</p>
        <p><strong>👤 Paid by:</strong> {expense.payer.username}</p>
        {f'<p><strong>📝 Description:</strong> {expense.description}</p>' if expense.description else ''}
      </div>
      
      <p>Login to view full details and manage your trip expenses.</p>
      
      <p style="margin-top: 30px;">Best regards,<br>The Trip Planner Team</p>
    </div>
  </body>
</html>
        """
        
        # Send to all recipients
        for recipient_email in recipients:
            send_email(subject, recipient_email, text_body, html_body)
        
        return True
    
    @staticmethod
    def send_budget_alert(trip, category, recipients):
        """Send budget warning when threshold reached"""
        from utils.currency_helper import format_currency
        
        subject = f"Budget Alert: {category.category} - '{trip.title}'"
        
        allocated = format_currency(category.allocated_amount, category.currency)
        spent = format_currency(category.spent_amount, category.currency)
        remaining = category.allocated_amount - category.spent_amount
        remaining_formatted = format_currency(remaining, category.currency)
        percentage = (category.spent_amount / category.allocated_amount * 100) if category.allocated_amount > 0 else 0
        
        text_body = f"""
Budget Alert for {trip.title}

You've spent {percentage:.1f}% of your {category.category} budget!

Budget Status:
• Allocated: {allocated}
• Spent: {spent}
• Remaining: {remaining_formatted}
• Status: {'Over Budget! ⚠️' if remaining < 0 else 'Warning ⚠️'}

Login to review your expenses and adjust your budget if needed.

Best regards,
The Trip Planner Team
        """
        
        status_color = '#f44336' if remaining < 0 else '#ff9800'
        status_text = 'OVER BUDGET!' if remaining < 0 else 'APPROACHING LIMIT'
        
        html_body = f"""
<html>
  <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
      <div style="background-color: {status_color}; color: white; padding: 15px; border-radius: 5px 5px 0 0;">
        <h2 style="margin: 0;">⚠️ Budget Alert</h2>
      </div>
      
      <div style="border: 2px solid {status_color}; border-top: none; padding: 20px; border-radius: 0 0 5px 5px;">
        <p><strong>{trip.title}</strong></p>
        <p style="font-size: 18px; color: {status_color};">
          You've spent <strong>{percentage:.1f}%</strong> of your <strong>{category.category}</strong> budget!
        </p>
        
        <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
          <h3 style="margin-top: 0;">{category.category} Budget Status</h3>
          <p><strong>💰 Allocated:</strong> {allocated}</p>
          <p><strong>💸 Spent:</strong> {spent}</p>
          <p><strong>💵 Remaining:</strong> {remaining_formatted}</p>
          <p style="color: {status_color}; font-weight: bold;">
            <strong>⚠️ Status:</strong> {status_text}
          </p>
        </div>
        
        <p>Login to review your expenses and adjust your budget if needed.</p>
      </div>
      
      <p style="margin-top: 30px;">Best regards,<br>The Trip Planner Team</p>
    </div>
  </body>
</html>
        """
        
        for recipient_email in recipients:
            send_email(subject, recipient_email, text_body, html_body)
        
        return True
    
    @staticmethod
    def send_test_email(recipient_email):
        """Send a test email to verify SMTP configuration"""
        subject = "Test Email from Trip Planner"
        
        text_body = """
This is a test email from Trip Planner!

If you received this email, your SMTP configuration is working correctly.

You can now receive:
• Welcome emails
• Trip invitations
• Expense notifications
• Budget alerts
• Activity reminders

Happy planning!

Best regards,
The Trip Planner Team
        """
        
        html_body = """
<html>
  <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
      <h2 style="color: #4CAF50;">Success! 🎉</h2>
      <p>This is a test email from Trip Planner!</p>
      
      <div style="background-color: #e8f5e9; padding: 20px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #4CAF50;">
        <p style="margin: 0;"><strong>✅ Your SMTP configuration is working correctly!</strong></p>
      </div>
      
      <p>You can now receive:</p>
      <ul>
        <li>📧 Welcome emails</li>
        <li>🎫 Trip invitations</li>
        <li>💸 Expense notifications</li>
        <li>⚠️ Budget alerts</li>
        <li>📅 Activity reminders</li>
      </ul>
      
      <p><strong>Happy planning!</strong></p>
      
      <p style="margin-top: 30px;">Best regards,<br>The Trip Planner Team</p>
    </div>
  </body>
</html>
        """
        
        return send_email(subject, recipient_email, text_body, html_body)
