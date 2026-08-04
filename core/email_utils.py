import base64
from decouple import config
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition


def send_email(to, subject, html_body, cc=None, attachments=None):
    """
    Shared email sender using SendGrid's HTTP API (works on hosts that block
    outbound SMTP, like Render's free tier).
    `to` can be a single address (string) or a list of addresses.
    `cc` (optional) is a list of addresses.
    `attachments` (optional) is a list of (filename, content_bytes, mimetype) tuples.
    Returns True on success, False on failure — never raises.
    """
    try:
        to_list = [to] if isinstance(to, str) else list(to)

        message = Mail(
            from_email=config('EMAIL_HOST_USER'),
            to_emails=to_list,
            subject=subject,
            html_content=html_body,
        )

        if cc:
            for cc_address in cc:
                message.add_cc(cc_address)

        if attachments:
            for filename, content, mimetype in attachments:
                encoded = base64.b64encode(content).decode()
                attachment = Attachment(
                    FileContent(encoded),
                    FileName(filename),
                    FileType(mimetype),
                    Disposition('attachment'),
                )
                message.add_attachment(attachment)

        sg = SendGridAPIClient(config('SENDGRID_API_KEY'))
        response = sg.send(message)
        return response.status_code in (200, 201, 202)
    except Exception as e:
        print(f"Email send failed: {e}")
        return False