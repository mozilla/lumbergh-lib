import sys
import smtplib
import warnings

try:
    from email.mime.text import MIMEText
except ImportError:
    from email.MIMEText import MIMEText

supports_timeout = sys.version_info > (2, 5)


class SendmailWarning(UserWarning):
    """Problem happened while sending the e-mail message."""


class Message(object):

    def __init__(self, to=None, sender=None, subject=None, body=None,
            charset="us-ascii"):
        self.to = to
        self.sender = sender
        self.subject = subject
        self.body = body
        self.charset = charset

        if not isinstance(self.to, (list, tuple)):
            self.to = [self.to]

    def __str__(self):
        msg = MIMEText(self.body, "plain", self.charset)
        msg["Subject"] = self.subject
        msg["From"] = self.sender
        msg["To"] = ", ".join(self.to)
        return msg.as_string()


class Mailer(object):

    def __init__(self, host="localhost", port=0, user=None, password=None,
            timeout=None):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.timeout = timeout

    def send(self, message):
        if supports_timeout:
            self._send(message, timeout=self.timeout)
        else:
            import socket
            old_timeout = socket.getdefaulttimeout()
            socket.setdefaulttimeout(self.timeout)
            try:
                self._send(message)
            finally:
                socket.setdefaulttimeout(old_timeout)

    def _send(self, message, **kwargs):
        client = smtplib.SMTP(self.host, self.port, **kwargs)

        if self.user and self.password:
            client.login(self.user, self.password)

        client.sendmail(message.sender, message.to, str(message))
        client.quit()


def mail_admins(subject, message, fail_silently=False):
    """Send a message to the admins in conf.ADMINS."""
    from celery import conf

    if not conf.ADMINS:
        return

    to = [admin_email for _, admin_email in conf.ADMINS]
    message = Message(sender=conf.SERVER_EMAIL, to=to,
                      subject=subject, body=message)

    try:
        mailer = Mailer(conf.EMAIL_HOST, conf.EMAIL_PORT,
                        conf.EMAIL_HOST_USER,
                        conf.EMAIL_HOST_PASSWORD,
                        conf.EMAIL_TIMEOUT)
        mailer.send(message)
    except Exception, exc:
        if not fail_silently:
            raise
        warnings.warn(SendmailWarning(
            "Mail could not be sent: %r %r" % (
                exc, {"To": to, "Subject": subject})))
