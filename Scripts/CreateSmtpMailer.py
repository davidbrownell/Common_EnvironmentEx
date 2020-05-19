# ----------------------------------------------------------------------
# |
# |  CreateSmtpMailer.py
# |
# |  David Brownell <db@DavidBrownell.com>
# |      2018-06-30 22:52:11
# |
# ----------------------------------------------------------------------
# |
# |  Copyright David Brownell 2018-20.
# |  Distributed under the Boost Software License, Version 1.0.
# |  (See accompanying file LICENSE_1_0.txt or copy at http://www.boost.org/LICENSE_1_0.txt)
# |
# ----------------------------------------------------------------------
"""Creates, Lists, and Verifies SmtpMailer profiles"""

import datetime
import os
import sys
import textwrap

import CommonEnvironment
from CommonEnvironment import CommandLine

from CommonEnvironmentEx.SmtpMailer import SmtpMailer

# ----------------------------------------------------------------------
_script_fullpath = CommonEnvironment.ThisFullpath()
_script_dir, _script_name = os.path.split(_script_fullpath)
# ----------------------------------------------------------------------

# ----------------------------------------------------------------------
@CommandLine.EntryPoint
@CommandLine.Constraints( profile_name=CommandLine.StringTypeInfo(),
                          host=CommandLine.StringTypeInfo(),
                          username=CommandLine.StringTypeInfo(arity='?'),
                          password=CommandLine.StringTypeInfo(arity='?'),
                          port=CommandLine.IntTypeInfo(min=1, arity='?'),
                          from_name=CommandLine.StringTypeInfo(arity='?'),
                          from_email=CommandLine.StringTypeInfo(arity='?'),
                          output_stream=None,
                        )
def Create( profile_name,
            host,
            username=None,
            password=None,
            port=26,
            from_name=None,
            from_email=None,
            ssl=False,
            output_stream=sys.stdout,
          ):
    """Creates a new SmtpMailer profile"""

    if not from_name and not from_email:
        raise CommandLine.UsageException("'from_name' or 'from_email' must be provided")

    mailer = SmtpMailer( host,
                         username=username,
                         password=password,
                         port=port,
                         from_name=from_name,
                         from_email=from_email,
                         ssl=ssl,
                       )
    mailer.Save(profile_name)

    output_stream.write("The profile '{}' has been created.\n".format(profile_name))

# ----------------------------------------------------------------------
@CommandLine.EntryPoint
@CommandLine.Constraints( output_stream=None,
                        )
def List( output_stream=sys.stdout,
        ):
    """Lists SmtpMailer profiles"""
    output_stream.write(textwrap.dedent(
        """\

        Available profiles:
        {}
        """).format( '\n'.join([ "    - {}".format(profile) for profile in SmtpMailer.GetProfiles() ]),
                   ))

# ----------------------------------------------------------------------
@CommandLine.EntryPoint
@CommandLine.Constraints( profile_name=CommandLine.StringTypeInfo(),
                          output_stream=None,
                        )
def Display( profile_name,
             output_stream=sys.stdout,
           ):
    mailer = SmtpMailer.Load(profile_name)

    output_stream.write(str(mailer))

# ----------------------------------------------------------------------
@CommandLine.EntryPoint
@CommandLine.Constraints( profile_name=CommandLine.StringTypeInfo(),
                          to=CommandLine.StringTypeInfo(arity='+'),
                          output_stream=None,
                        )
def Verify( profile_name,
            to,
            output_stream=sys.stdout,
          ):
    mailer = SmtpMailer.Load(profile_name)

    mailer.SendMessage( to,
                        "SmtpMailer Verification",
                        "This is a test message to ensure that the profile '{}' is working as expected ({}).".format( profile_name,
                                                                                                                      datetime.datetime.now(),
                                                                                                                    ),
                      )

    output_stream.write("A verification email has been sent.\n")

# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
if __name__ == "__main__":
    try: sys.exit(CommandLine.Main())
    except KeyboardInterrupt: pass
