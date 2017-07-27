#!/usr/bin/env python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


"""Script for creating coverage.info file with dynamorio bbcov2lcov binary.
"""

import glob
import optparse
import os
import subprocess
import sys

from common import chromium_utils

# Method could be a function
# pylint: disable=R0201

COVERAGE_DIR_POSTFIX = '_coverage'
COVERAGE_INFO = 'coverage.info'


def GetExecutableName(executable):
  """The executable name must be executable plus '.exe' on Windows, or else
  just the test name."""
  if sys.platform == 'win32':
    return executable + '.exe'
  return executable


def RunCmd(command, env=None, shell=True):
  """Call a shell command.
  Args:
    command: the command to run
    env: dictionary of environment variables

  Returns:
    retcode
  """
  process = subprocess.Popen(command, shell=shell, env=env)
  process.wait()
  return process.returncode


def CreateCoverageFileAndUpload(options):
  """Create coverage file with bbcov2lcov binary and upload to www dir."""
  # Assert log files exist
  log_files = glob.glob(os.path.join(options.dynamorio_log_dir, '*.log'))
  if not log_files:
    print 'No coverage log files found.'
    return 1

  if (options.browser_shard_index and
      options.test_to_upload in options.sharded_tests):
    coverage_info = os.path.join(
        options.build_dir, 'coverage_%s.info' % options.browser_shard_index)
  else:
    coverage_info = os.path.join(options.build_dir, COVERAGE_INFO)
  coverage_info = os.path.normpath(coverage_info)
  if os.path.isfile(coverage_info):
    os.remove(coverage_info)

  bbcov2lcov_binary = GetExecutableName(
      os.path.join(options.dynamorio_dir, 'tools', 'bin32', 'bbcov2lcov'))
  cmd = [
      bbcov2lcov_binary,
      '--dir', options.dynamorio_log_dir,
      '--output', coverage_info]
  RunCmd(cmd)

  # Delete log files.
  log_files = glob.glob(os.path.join(options.dynamorio_log_dir, '*.log'))
  for log_file in log_files:
    os.remove(log_file)

  # Assert coverage.info file exist
  if not os.path.isfile(coverage_info):
    print 'Failed to create coverage.info file.'
    return 1

  # Upload coverage file.
  cov_dir = options.test_to_upload.replace('_', '') + COVERAGE_DIR_POSTFIX
  dest = os.path.join(options.www_dir,
                      options.platform, options.build_id, cov_dir)
  dest = os.path.normpath(dest)
  if chromium_utils.IsWindows():
    print ('chromium_utils.CopyFileToDir(%s, %s)' %
           (coverage_info, dest))
    chromium_utils.MaybeMakeDirectory(dest)
    chromium_utils.CopyFileToDir(coverage_info, dest)
  elif chromium_utils.IsLinux() or chromium_utils.IsMac():
    print 'SshCopyFiles(%s, %s, %s)' % (coverage_info, options.host, dest)
    chromium_utils.SshMakeDirectory(options.host, dest)
    chromium_utils.MakeWorldReadable(coverage_info)
    chromium_utils.SshCopyFiles(coverage_info, options.host, dest)
    os.unlink(coverage_info)
  else:
    raise NotImplementedError(
        'Platform "%s" is not currently supported.' % sys.platform)
  return 0


def main():
  option_parser = optparse.OptionParser()

  # Required options:
  option_parser.add_option('--build-dir',
                           help='path to main build directory (the parent of '
                                'the Release or Debug directory)')
  option_parser.add_option('--build-id',
                           help='The build number of the tested build.')
  option_parser.add_option('--target',
                           help='Target directory.')
  option_parser.add_option('--platform',
                           help='Coverage subdir.')
  option_parser.add_option('--dynamorio-dir',
                           help='Path to dynamorio binary.')
  option_parser.add_option('--dynamorio-log-dir',
                           help='Path to dynamorio coverage log files.')
  option_parser.add_option('--test-to-upload',
                           help='Test name.')

  chromium_utils.AddPropertiesOptions(option_parser)
  options, _ = option_parser.parse_args()

  fp = options.factory_properties
  options.browser_shard_index = fp.get('browser_shard_index')
  options.sharded_tests = fp.get('sharded_tests')
  options.host = fp.get('host')
  options.www_dir = fp.get('www-dir')
  del options.factory_properties
  del options.build_properties

  return CreateCoverageFileAndUpload(options)

if '__main__' == __name__:
  sys.exit(main())
