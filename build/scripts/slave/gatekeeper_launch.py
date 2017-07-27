#!/usr/bin/env python
# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Annotated script to launch the gatekeeper script."""

import os
import sys

SLAVE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(SLAVE_DIR, os.pardir, os.pardir))
sys.path.insert(0, os.path.join(BASE_DIR, 'scripts'))
sys.path.insert(0, os.path.join(BASE_DIR, 'scripts', 'slave'))

from common import annotator
from common import chromium_utils


def main():
  master_urls = ['http://build.chromium.org/p/chromium']

  json = os.path.join(SLAVE_DIR, 'gatekeeper.json')
  args = ['-v', '--no-email-app', '--json=%s' % json]

  script = os.path.join(SLAVE_DIR, 'gatekeeper_ng.py')
  cmd = [sys.executable, script]

  cmd.extend(args)
  cmd.extend(master_urls)

  stream = annotator.StructuredAnnotationStream(seed_steps=['gatekeeper_ng'])
  with stream.step('gatekeeper_ng') as s:
    env = {}
    env['PYTHONPATH'] = os.pathsep.join(sys.path)

    result = chromium_utils.RunCommand(cmd, env=env)
    if result != 0:
      s.step_failure()
      return 2
  return 0


if '__main__' == __name__:
  sys.exit(main())
