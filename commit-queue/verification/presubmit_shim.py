#!/usr/bin/env python
# coding=utf8
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Runs presubmit check on the source tree.

This shims removes the checks for try jobs.
"""

import os
import sys

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(ROOT_DIR))

import find_depot_tools  # pylint: disable=W0611
import presubmit_support

# Do not pass them through the command line.
email = sys.stdin.readline().strip()
assert email
password = sys.stdin.readline().strip()
assert password
sys.stdin.close()

argv = sys.argv[1:]
argv.extend(['--rietveld_email', email, '--rietveld_password', password])
argv.extend(['--skip_canned', 'CheckRietveldTryJobExecution'])
argv.extend(['--skip_canned', 'CheckTreeIsOpen'])
argv.extend(['--skip_canned', 'CheckBuildbotPendingBuilds'])

sys.exit(presubmit_support.Main(argv))
