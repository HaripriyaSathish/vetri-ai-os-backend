from django.core.mail import EmailMultiAlternatives


def send_email(to, subject, html_body, cc=None, attachments=None):
    """
    Shared email sender using Django's SMTP backend.
    `to` can be a single address (string) or a list of addresses.
    `cc` (optional) is a list of addresses.
    `attachments` (optional) is a list of (filename, content_bytes, mimetype) tuples.
    Returns True on success, False on failure — never raises.
    """
    try:
        to_list = [to] if isinstance(to, str) else list(to)
        email = EmailMultiAlternatives(
            subject=subject,
            body='',
            from_email=None,
            to=to_list,
            cc=cc or None,
        )
        email.attach_alternative(html_body, "text/html")
        if attachments:
            for filename, content, mimetype in attachments:
                email.attach(filename, content, mimetype)
        email.send(fail_silently=False)
        return True
    except Exception as e:
        print(f"Email send failed: {e}")
        return False