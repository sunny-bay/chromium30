#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Send automated email alerts."""

import logging
import os
import re
import smtplib
import socket
import sys

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT_DIR, '..', 'commit-queue-internal'))

# These come from commit-queue-internal.
try:
  import alert_settings  # pylint: disable=F0401
except ImportError:
  alert_settings = None


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def SendAlert(subject, message):
  """Send an alert to troopers.

  Use the golo smtp relay to prevent accidental leaks from local checkouts.
  """
  hostname = socket.getfqdn()
  if (alert_settings and
      re.match(r'cq\d?\.golo\.chromium\.org$', hostname)):
    logging.warning('Sending alert, subject %s', subject)
    body = """\
From: %s
To: %s
Subject: [cq alert] %s

host: %s
script dir: %s
cwd: %s
argv: %s


%s""" % (alert_settings.FROM_ADDRESS, ', '.join(alert_settings.TO_ADDRESSES),
         subject, hostname, SCRIPT_DIR, os.getcwd(), sys.argv, message)

    server = smtplib.SMTP(alert_settings.SMTP_RELAY)
    server.sendmail(
        alert_settings.FROM_ADDRESS, alert_settings.TO_ADDRESSES, body)
    server.quit()
  else:
    logging.warning('\n  '.join([
        'Would send alert if running in production.',
        'Subject: %s' % subject, ''] + message.splitlines()[:20]))
