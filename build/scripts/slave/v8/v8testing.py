#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A tool to run the v8 tests.

  For a list of command-line options, call this script with '--help'.
"""

import optparse
import os
import sys

from common import chromium_utils

def main():
  if sys.platform in ('win32', 'cygwin'):
    default_platform = 'win'
    outdir = 'build'
  elif sys.platform.startswith('darwin'):
    default_platform = 'mac'
    outdir = 'xcodebuild'
  elif sys.platform == 'linux2':
    default_platform = 'linux'
    outdir = 'out'
  else:
    default_platform = None

  option_parser = optparse.OptionParser()

  option_parser.add_option('', '--testname',
                           default=None,
                           help='The test to run'
                                '[default: %default]')
  option_parser.add_option('', '--target',
                           default='Debug',
                           help='build target (Debug, Release) '
                                '[default: %default]')
  option_parser.add_option('', '--arch',
                           default='ia32',
                           help='Architecture (ia32, x64, arm) '
                                '[default: ia32]')
  option_parser.add_option('', '--platform',
                           default=default_platform,
                           help='specify platform [default: %%default]')
  option_parser.add_option('', '--shard_count',
                           default=1,
                           help='Specify shard count [default: %%default]')
  option_parser.add_option('', '--shard_run',
                           default=1,
                           help='Specify shard count [default: %%default]')
  option_parser.add_option('--shell_flags',
                           default=None,
                           help="Specify shell flags passed tools/run-test.py")
  option_parser.add_option('--command_prefix',
                           default=None,
                           help="Command prefix passed tools/run-test.py")
  option_parser.add_option('--isolates',
                           default=None,
                           help="Run isolates tests")
  option_parser.add_option('--buildbot',
                           default='True',
                           help="Resolve paths to executables for buildbots")
  option_parser.add_option('--no-presubmit',
                           default=False, action="store_true",
                           help='Skip presubmit checks')

  options, args = option_parser.parse_args()
  if args:
    option_parser.error('Unsupported arguments: %s' % args)

  os.environ['LD_LIBRARY_PATH'] = os.environ.get('PWD')

  if options.testname == 'presubmit':
    cmd = ['python', 'tools/presubmit.py']
  else:
    cmd = ['python', 'tools/run-tests.py',
           '--progress=verbose',
           '--outdir=' + outdir,
           '--arch=' + options.arch,
           '--mode=' + options.target]
    if options.buildbot == 'True':
      cmd.extend(['--buildbot'])
    if options.no_presubmit:
      cmd.extend(['--no-presubmit'])
    if options.testname:
      cmd.extend([options.testname])
    if options.testname == 'test262':
      cmd.extend(['--download-data'])
    if options.testname == 'mozilla':
      # Mozilla tests requires a number of tests to timeout, set it a bit lower.
      if options.arch in ('arm', 'mipsel'):
        cmd.extend(['--timeout=180'])
      else:
        cmd.extend(['--timeout=120'])
    elif options.shell_flags and '--gc-interval' in options.shell_flags:
      # GC Stress testing takes much longer, set generous timeout.
      if options.arch in ('arm', 'mipsel'):
        cmd.extend(['--timeout=1200'])
      else:
        cmd.extend(['--timeout=900'])
    else:
      if options.arch in ('arm', 'mipsel'):
        cmd.extend(['--timeout=600'])
      else:
        cmd.extend(['--timeout=200'])
    if options.isolates:
      cmd.extend(['--isolates'])
    if options.shell_flags:
      cmd.extend(["--extra-flags", options.shell_flags.replace("\"", "")])
    if options.command_prefix:
      cmd.extend(["--command-prefix", options.command_prefix])


  if options.shard_count > 1:
    cmd.extend(['--shard-count=%s' % options.shard_count,
                '--shard-run=%s' % options.shard_run])

  return chromium_utils.RunCommand(cmd)


if __name__ == '__main__':
  sys.exit(main())
