#!/usr/bin/env python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Runs a command with PYTHONPATH set up for the Chromium build setup.

This is helpful for running scripts locally on a development machine.

Try `scripts/common/runit.py python`
or  (in scripts/slave): `../common/runit.py runtest.py --help`
"""

import optparse
import os
import subprocess
import sys

SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))
BUILD_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))

USAGE = '%s [options] <command to run>' % os.path.basename(sys.argv[0])

def main():
  option_parser = optparse.OptionParser(usage=USAGE)
  option_parser.add_option('-s', '--show-path', action='store_true',
                           help='display new PYTHONPATH before running command')
  option_parser.disable_interspersed_args()
  options, args = option_parser.parse_args()
  if not args:
    option_parser.error('Must provide a command to run.')

  path = os.environ.get('PYTHONPATH', '').split(os.pathsep)

  def add(new_path):
    if new_path not in path:
      path.insert(0, new_path)

  third_party = os.path.join(BUILD_DIR, 'third_party')
  for d in os.listdir(third_party):
    full = os.path.join(third_party, d)
    if os.path.isdir(full):
      add(full)
  add(os.path.join(BUILD_DIR, 'scripts'))
  add(third_party)
  add(os.path.join(BUILD_DIR, 'site_config'))
  add(os.path.join(BUILD_DIR, '..', 'build_internal', 'site_config'))
  add('.')
  os.environ['PYTHONPATH'] = os.pathsep.join(path)

  if options.show_path:
    print 'Set PYTHONPATH: %s' % os.environ['PYTHONPATH']

  # Use subprocess instead of execv because otherwise windows destroys quoting.
  p = subprocess.Popen(args)
  p.wait()
  return p.returncode


if __name__ == '__main__':
  sys.exit(main())
