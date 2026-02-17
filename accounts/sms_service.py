# SMS Service Module
# This module handles SMS sending functionality for password reset and OTP codes.
# Currently uses a mock implementation for development.
# In production, integrate with services like Twilio, Kavenegar, or similar SMS providers.

import logging
import os
from typing import Tuple

logger = logging.getLogger(__name__)


class SMSService:
    """
    SMS service handler for sending SMS messages.
    This is a mock implementation that logs to console for development.
    """

    def __init__(self):
        """Initialize SMS service with configuration from environment variables."""
        self.api_key = os.getenv("SMS_API_KEY", "mock-key")
        self.sender_id = os.getenv("SMS_SENDER_ID", "User-Management")
        self.provider = os.getenv("SMS_PROVIDER", "mock")

    def send_sms(self, phone_number: str, message: str) -> Tuple[bool, str]:
        """
        Send SMS message to the specified phone number.

        Args:
            phone_number (str): Recipient phone number
            message (str): Message content to send

        Returns:
            Tuple[bool, str]: (success, message_id or error)
        """
        try:
            if self.provider == "twilio":
                return self._send_via_twilio(phone_number, message)
            elif self.provider == "kavenegar":
                return self._send_via_kavenegar(phone_number, message)
            else:
                # Mock implementation for development
                return self._send_via_mock(phone_number, message)
        except Exception as e:
            logger.error(f"SMS sending failed for {phone_number}: {str(e)}")
            return False, str(e)

    def _send_via_mock(self, phone_number: str, message: str) -> Tuple[bool, str]:
        """
        Mock SMS sending for development/testing.
        Logs message to server console instead of sending.

        Args:
            phone_number (str): Recipient phone number
            message (str): Message content

        Returns:
            Tuple[bool, str]: (success, mock_message_id)
        """
        mock_id = f"mock-{phone_number}-{hash(message) % 10000}"
        logger.warning(
            f"[MOCK SMS] To: {phone_number} | Message: {message} | ID: {mock_id}"
        )
        return True, mock_id

    def _send_via_twilio(self, phone_number: str, message: str) -> Tuple[bool, str]:
        """
        Send SMS via Twilio API.
        Requires: twilio package and TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN env vars.

        Args:
            phone_number (str): Recipient phone number
            message (str): Message content

        Returns:
            Tuple[bool, str]: (success, message_id or error)
        """
        try:
            from twilio.rest import Client

            account_sid = os.getenv("TWILIO_ACCOUNT_SID")
            auth_token = os.getenv("TWILIO_AUTH_TOKEN")
            from_number = os.getenv("TWILIO_FROM_NUMBER")

            client = Client(account_sid, auth_token)
            msg = client.messages.create(
                body=message, from_=from_number, to=phone_number
            )
            logger.info(f"SMS sent via Twilio: {msg.sid}")
            return True, msg.sid
        except ImportError:
            logger.error("Twilio not installed. Install with: pip install twilio")
            return False, "Twilio package not installed"
        except Exception as e:
            return False, f"Twilio error: {str(e)}"

    def _send_via_kavenegar(self, phone_number: str, message: str) -> Tuple[bool, str]:
        """
        Send SMS via Kavenegar API (popular in Iran).
        Requires: requests package and KAVENEGAR_API_KEY env var.

        Args:
            phone_number (str): Recipient phone number
            message (str): Message content

        Returns:
            Tuple[bool, str]: (success, message_id or error)
        """
        try:
            import requests

            url = "https://api.kavenegar.com/v1/{}/sms/send.json".format(
                self.api_key
            )
            params = {"receptor": phone_number, "message": message}

            response = requests.post(url, data=params, timeout=10)
            response.raise_for_status()

            result = response.json()
            if result.get("result"):
                message_id = result["result"][0]["messageid"]
                logger.info(f"SMS sent via Kavenegar: {message_id}")
                return True, message_id
            else:
                return False, result.get("message", "Unknown error")
        except ImportError:
            logger.error("Requests not installed. Install with: pip install requests")
            return False, "Requests package not installed"
        except Exception as e:
            return False, f"Kavenegar error: {str(e)}"

    def send_password_reset_sms(self, phone_number: str, reset_token: str) -> Tuple[bool, str]:
        """
        Send password reset SMS with token.

        Args:
            phone_number (str): User phone number
            reset_token (str): Password reset token

        Returns:
            Tuple[bool, str]: (success, message_id or error)
        """
        message = f"Password reset code: {reset_token}\nValid for 15 minutes.\nDo not share with anyone."
        return self.send_sms(phone_number, message)

    def send_login_otp(self, phone_number: str, otp_code: str) -> Tuple[bool, str]:
        """
        Send login OTP SMS.

        Args:
            phone_number (str): User phone number
            otp_code (str): OTP code

        Returns:
            Tuple[bool, str]: (success, message_id or error)
        """
        message = f"Your login code is: {otp_code}\nValid for 5 minutes."
        return self.send_sms(phone_number, message)


# Global SMS service instance
sms_service = SMSService()
