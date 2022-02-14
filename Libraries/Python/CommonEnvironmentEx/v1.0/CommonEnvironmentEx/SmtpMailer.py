# ----------------------------------------------------------------------
# |
# |  SmtpMailer.py
# |
# |  David Brownell <db@DavidBrownell.com>
# |      2018-06-30 22:32:10
# |
# ----------------------------------------------------------------------
# |
# |  Copyright David Brownell 2018-22.
# |  Distributed under the Boost Software License, Version 1.0.
# |  (See accompanying file LICENSE_1_0.txt or copy at http://www.boost.org/LICENSE_1_0.txt)
# |
# ----------------------------------------------------------------------
"""Contains the SmtpMailer object"""

import io
import mimetypes
import os
import smtplib
import sys

from email import encoders
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from six.moves import cPickle as pickle

import CommonEnvironment
from CommonEnvironment.Shell.All import CurrentShell

# ----------------------------------------------------------------------
_script_fullpath = CommonEnvironment.ThisFullpath()
_script_dir, _script_name = os.path.split(_script_fullpath)
# ----------------------------------------------------------------------

class SmtpMailer(object):
    """Call that manages smtp profiles and sends messages from those profiles."""

    PROFILE_EXTENSION                       = ".SmtpMailer"

    # ----------------------------------------------------------------------
    @classmethod
    def GetProfiles(cls):
        """Returns all available profiles"""

        data_dir = CurrentShell.UserDirectory

        return [ os.path.splitext(item)[0] for item in os.listdir(data_dir) if os.path.isfile(os.path.join(data_dir, item)) and os.path.splitext(item)[1] == cls.PROFILE_EXTENSION ]

    # ----------------------------------------------------------------------
    @classmethod
    def Load(cls, profile_name):
        """Loads a profile"""

        data_filename = CurrentShell.CreateDataFilename(profile_name, suffix=cls.PROFILE_EXTENSION)
        if not os.path.isfile(data_filename):
            raise Exception("'{}' is not a valid filename".format(data_filename))

        with open(data_filename, 'rb') as f:
            content = f.read()

        if CurrentShell.CategoryName == "Windows":
            import win32crypt
            content = win32crypt.CryptUnprotectData(content, None, None, None, 0)
            content = content[1]

        return pickle.loads(content)

    # ----------------------------------------------------------------------
    def __init__( self,
                  host,
                  username=None,
                  password=None,
                  port=26,
                  from_name=None,
                  from_email=None,
                  ssl=False,
                ):
        assert from_name or from_email

        self.Host                           = host
        self.Username                       = username or ''
        self.Password                       = password or ''
        self.Port                           = port
        self.FromName                       = from_name or ''
        self.FromEmail                      = from_email or ''
        self.Ssl                            = ssl

    # ----------------------------------------------------------------------
    def __repr__(self):
        return CommonEnvironment.ObjectReprImpl(self)

    # ----------------------------------------------------------------------
    def Save(self, profile_name):
        """Saves a profile"""

        content = pickle.dumps(self)

        if CurrentShell.CategoryName == "Windows":
            import win32crypt
            content = win32crypt.CryptProtectData(content, '', None, None, None, 0)

        with open( CurrentShell.CreateDataFilename(profile_name, suffix=self.PROFILE_EXTENSION),
                   'wb',
                 ) as f:
            f.write(content)

    # ----------------------------------------------------------------------
    def SendMessage( self,
                     recipients,
                     subject,
                     message,
                     attachment_filenames=None,
                     message_format="plain",
                   ):
        """Sends a message via the current profile"""

        if self.Ssl:
            smtp = smtplib.SMTP_SSL()
        else:
            smtp = smtplib.SMTP()

        smtp.connect(self.Host, self.Port)

        if self.Username and self.Password:
            if not self.Ssl:
                smtp.starttls()

            smtp.login(self.Username, self.Password)

        assert self.FromName or self.FromEmail

        if not self.FromName:
            from_addr = self.FromEmail
        elif not self.FromEmail:
            from_addr = self.FromName
        else:
            from_addr = "{} <{}>".format(self.FromName, self.FromEmail)

        msg = MIMEMultipart()

        msg["Subject"] = subject
        msg["From"] = from_addr
        msg["To"] = ', '.join(recipients)

        msg.attach(MIMEText(message, message_format))

        for attachment_filename in (attachment_filenames or []):
            ctype, encoding = mimetypes.guess_type(attachment_filename)
            if ctype is None or encoding is not None:
                ctype = "application/octet-stream"

            maintype, subtype = ctype.split('/', 1)

            if maintype == "text":
                attachment = MIMEText(
                    io.open(
                        attachment_filename,
                        encoding="utf-8",
                    ).read(),
                    _subtype=subtype,
                )
            elif maintype == "image":
                attachment = MIMEImage(open(attachment_filename, 'rb').read(), _subtype=subtype)
            elif maintype == "audio":
                attachment = MIMEAudio(open(attachment_filename, 'rb').read(), _subtype=subtype)
            else:
                attachment = MIMEBase(maintype, subtype)

                attachment.set_payload(open(attachment_filename, 'rb').read())
                encoders.encode_base64(attachment)

            attachment.add_header("Content-Disposition", "attachment", filename=os.path.basename(attachment_filename))

            msg.attach(attachment)

        smtp.sendmail(from_addr, recipients, msg.as_string())
        smtp.close()
