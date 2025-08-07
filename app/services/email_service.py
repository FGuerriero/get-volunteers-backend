'''
# Copyright (c) 2025 Fernando Guerriero Cardoso da Silva.
# Created Date: Thu Aug 07 2025
# SPDX-License-Identifier: MIT
'''

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from app.config import settings
from app.db import models


class EmailService:
    def __init__(self):
        self.sg = SendGridAPIClient(settings.sendgrid_api_key)
        self.sender_email = settings.mail_sender_email
        self.sender_name = settings.mail_sender_name

    async def send_match_notification(
        self,
        volunteer: models.Volunteer,
        need: models.Need,
        match_details: str
    ):
        """
        Sends an email notification to both the volunteer and the need contact
        about a new match.
        """
        # Email to Volunteer
        volunteer_subject = f"New Match Found: {need.title} needs your help!"
        volunteer_html_content = f"""
        <html>
        <body>
            <p>Hi {volunteer.name},</p>
            <p>Great news! We've found a potential match for you:</p>
            <h3>Need: {need.title}</h3>
            <p><strong>Description:</strong> {need.description}</p>
            <p><strong>Your Match Details:</strong> {match_details}</p>
            <p>If you're interested, please contact the organizer:</p>
            <ul>
                <li><strong>Contact Name:</strong> {need.contact_name}</li>
                <li><strong>Contact Email:</strong> {need.contact_email}</li>
                <li><strong>Contact Phone:</strong> {need.contact_phone or 'N/A'}</li>
            </ul>
            <p>Thank you for being a part of the getVolunteer community!</p>
            <p>Best regards,</p>
            <p>{self.sender_name}</p>
        </body>
        </html>
        """
        await self._send_email(volunteer.email, volunteer_subject, volunteer_html_content)

        # Email to Need Contact
        need_subject = f"New Volunteer Match for your Need: {need.title}"
        need_html_content = f"""
        <html>
        <body>
            <p>Hi {need.contact_name},</p>
            <p>We've found a potential volunteer for your need:</p>
            <h3>Need: {need.title}</h3>
            <p><strong>Description:</strong> {need.description}</p>
            <p><strong>Volunteer Details:</strong></p>
            <ul>
                <li><strong>Name:</strong> {volunteer.name}</li>
                <li><strong>Email:</strong> {volunteer.email}</li>
                <li><strong>Phone:</strong> {volunteer.phone or 'N/A'}</li>
                <li><strong>Skills:</strong> {volunteer.skills or 'N/A'}</li>
                <li><strong>Interests:</strong> {volunteer.volunteer_interests or 'N/A'}</li>
            </ul>
            <p><strong>Match Details:</strong> {match_details}</p>
            <p>Please reach out to the volunteer if you'd like to proceed.</p>
            <p>Thank you for using getVolunteer!</p>
            <p>Best regards,</p>
            <p>{self.sender_name}</p>
        </body>
        </html>
        """
        await self._send_email(need.contact_email, need_subject, need_html_content)

    async def _send_email(self, to_email: str, subject: str, html_content: str):
        """
        Internal helper to send an email using SendGrid.
        """
        message = Mail(
            from_email=(self.sender_email, self.sender_name),
            to_emails=to_email,
            subject=subject,
            html_content=html_content
        )
        try:
            response = self.sg.send(message)
            print(f"Email sent to {to_email}. Status Code: {response.status_code}")
            # print(f"Response Body: {response.body}") # Uncomment for debugging
            # print(f"Response Headers: {response.headers}") # Uncomment for debugging
        except Exception as e:
            print(f"Error sending email to {to_email}: {e}")
