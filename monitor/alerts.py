# ==============================================================================
# monitor/alerts.py — Email and Slack alert senders.
#
# Both channels gracefully skip when their environment variables are not set,
# logging a warning instead of crashing.
# ==============================================================================
import os
import smtplib
import logging
import requests
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


def send_email_alert(subject: str, body: str):
    """Send an alert email via SMTP with TLS.

    Required env vars: SMTP_HOST, SMTP_USER, SMTP_PASS, ALERT_FROM, ALERT_TO.
    If any are missing, the function logs a warning and returns without sending.
    """
    smtp_host = os.getenv("SMTP_HOST")
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    alert_from = os.getenv("ALERT_FROM")
    alert_to = os.getenv("ALERT_TO")

    # Gracefully skip if email is not configured
    if not all([smtp_host, smtp_user, smtp_pass, alert_from, alert_to]):
        logger.warning("Email alert skipped — SMTP env vars not fully configured.")
        return

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = alert_from
    msg["To"] = alert_to

    try:
        with smtplib.SMTP(smtp_host, 587) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        logger.info(f"Email alert sent to {alert_to}: {subject}")
    except Exception as e:
        logger.error(f"Failed to send email alert: {e}")


def send_slack_alert(message: str):
    """Send an alert message to a Slack channel via webhook.

    Required env var: SLACK_WEBHOOK_URL.
    If missing, the function logs a warning and returns without sending.
    """
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")

    if not webhook_url:
        logger.warning("Slack alert skipped — SLACK_WEBHOOK_URL not configured.")
        return

    try:
        response = requests.post(
            webhook_url,
            json={"text": f"🚨 *Server Alert*\n{message}"},
            timeout=5,
        )
        response.raise_for_status()
        logger.info(f"Slack alert sent: {message[:80]}...")
    except requests.RequestException as e:
        logger.error(f"Failed to send Slack alert: {e}")
