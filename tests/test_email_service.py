'''
# Copyright (c) 2025 Fernando Guerriero Cardoso da Silva.
# Created Date: Mon Sep 01 2025
# SPDX-License-Identifier: MIT
'''

import asyncio
import unittest
from unittest import mock

from app.db import models
from app.services.email_service import EmailService


class TestEmailService(unittest.TestCase):
    """
    Test suite for the EmailService class.
    
    We're removing the setUp method to ensure that the EmailService instance
    is created within each test method, after the mock is in place.
    """
    
    # Mock data for the tests
    volunteer_data = models.Volunteer(
        id=1,
        name="Jane Doe",
        email="jane.doe@example.com",
        phone="123-456-7890",
        skills="Python, SQL",
        volunteer_interests="Software development"
    )
    need_data = models.Need(
        id=1,
        title="Help with coding a new feature",
        description="We need a Python developer to help us with a new feature.",
        contact_name="John Smith",
        contact_email="john.smith@example.com",
        contact_phone="987-654-3210"
    )
    match_details_data = "Match found based on your skills in Python."

    @mock.patch("app.services.email_service.SendGridAPIClient")
    @mock.patch("app.services.email_service.Mail")
    def test_send_email_success(self, mock_mail_class, mock_sendgrid_client):
        """
        Test that _send_email successfully sends an email on a 2xx status code.
        """
        # Arrange
        email_service = EmailService()
        mock_sg_instance = mock_sendgrid_client.return_value
        mock_response = mock.MagicMock(status_code=202)
        mock_sg_instance.send.return_value = mock_response
        
        # Act
        asyncio.run(
            email_service._send_email(
                "test@example.com", "Test Subject", "Test HTML"
            )
        )

        # Assert
        # Verify that the Mail object was instantiated with the correct arguments.
        # Now correctly referencing the instance attribute 'sender_email'.
        mock_mail_class.assert_called_once_with(
            from_email=(email_service.sender_email, email_service.sender_name),
            to_emails="test@example.com",
            subject="Test Subject",
            html_content="Test HTML"
        )
        
        # Verify that the send method was called with the Mail instance
        mock_sg_instance.send.assert_called_once_with(mock_mail_class.return_value)

    @mock.patch("app.services.email_service.SendGridAPIClient")
    def test_send_email_failure(self, mock_sendgrid_client):
        """
        Test that _send_email handles exceptions gracefully.
        """
        # Arrange: Create EmailService instance here, so it gets the mock client
        email_service = EmailService()
        mock_sg_instance = mock_sendgrid_client.return_value
        # Use `side_effect` to raise an exception when the send method is called
        mock_sg_instance.send.side_effect = Exception("Test exception")

        # Act & Assert
        # The test should not raise an exception, as the error is handled internally
        asyncio.run(
            email_service._send_email(
                "test@example.com", "Test Subject", "Test HTML"
            )
        )
        # We can still assert that the `send` method was called as expected
        mock_sg_instance.send.assert_called_once()

    @mock.patch("app.services.email_service.EmailService._send_email")
    def test_send_match_notification_calls_send_email_twice(self, mock_send_email):
        """
        Test that send_match_notification calls the _send_email helper
        for both the volunteer and the need contact.
        """
        # Arrange
        email_service = EmailService()

        # Act
        asyncio.run(
            email_service.send_match_notification(
                self.volunteer_data, self.need_data, self.match_details_data
            )
        )

        # Assert
        # Check if _send_email was called exactly twice
        self.assertEqual(mock_send_email.call_count, 2)

        # Verify the call for the volunteer email
        volunteer_call = mock_send_email.call_args_list[0]
        self.assertEqual(volunteer_call[0][0], self.volunteer_data.email)
        self.assertIn(self.volunteer_data.name, volunteer_call[0][2])

        # Verify the call for the need contact email
        need_call = mock_send_email.call_args_list[1]
        self.assertEqual(need_call[0][0], self.need_data.contact_email)
        self.assertIn(self.need_data.contact_name, need_call[0][2])