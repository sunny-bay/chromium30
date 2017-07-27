#!/usr/bin/python
#
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Wrapper that does auto-retry and stats logging for command invocation.

Various command line tools in use: gsutil, curl have spurious failure.
This wrapper will track stats to an AppEngine based service to
help track down the cause of failures, as well as add retry logic.
"""


import optparse
import os
import platform
import socket
import subprocess
import sys
import threading
import time
import urllib
import uuid


LOG_TIMEOUT = 10
ON_POSIX = 'posix' in sys.builtin_module_names


def LogCommand(options, command_id,
               attempt, cmd, returncode, stdout, stderr, runtime):
  """Log a command invocation and result to a central location.

  Arguments:
    options: parsed options
    command_id: unique id for this command (shared by all retries)
    attempt: which try numbered from 0
    cmd: command run
    returncode: return code from running command
    stdout: text of stdout
    stderr: text of stderr
    runtime: command runtime in seconds
  Returns:
    True/False indicating if the current result should be accepted without
    further retry.
  """
  uname = platform.uname()
  params = urllib.urlencode({
      'attempt': str(attempt),
      'cwd': os.getcwd(),
      'command_id': command_id,
      'command': cmd,
      'returncode': str(returncode),
      'stdout': stdout[:400],
      'stderr': stderr[:400],
      'runtime': str(runtime),
      'retries': str(options.retries),
      'uname_sysname': uname[0],
      'uname_nodename': uname[1],
      'uname_release': uname[2],
      'uname_version': uname[3],
      'uname_machine': uname[4],
      'uname_processor': uname[5],
  })
  f = urllib.urlopen(options.logurl, params)
  ret = f.read()
  f.close()
  try:
    return int(ret) != 0
  except ValueError:
    return 0


def RunWithTimeout(timeout, func, *args, **kwargs):
  wrapper = { 'result': None }
  def CallFunc():
    wrapper['result'] = func(*args, **kwargs)
  th = threading.Thread(target=CallFunc)
  th.start()
  th.join(timeout)
  return wrapper['result']


def Tee(fd, string_buffer, forward_fd):
  """Read characters from fd and both append them to a buffer and write them to
  forward_fd."""
  for char in iter(lambda: fd.read(1), ''):
    string_buffer += char
    forward_fd.write(char)
  fd.close()


def main(argv):
  parser = optparse.OptionParser()
  parser.add_option('-r', '--retries', dest='retries',
                    type='int', default=10,
                    help='number of times to retry on failure')
  parser.add_option('-u', '--logurl', dest='logurl',
                    default='https://command-wrapper.appspot.com/log',
                    help='URL to log invocations/failures to')
  (options, args) = parser.parse_args(args=argv[1:])

  # Limit tcp connnection timeouts to 10 seconds.
  socket.setdefaulttimeout(10)

  command_id = uuid.uuid1()

  # Ensure that args with spaces in them remain quoted.
  args_quoted = []
  for arg in args:
    if ' ' in arg:
      arg = '"' + arg + '"'
    args_quoted.append(arg)
  cmd = ' '.join(args_quoted)

  # Log that we're even starting.
  RunWithTimeout(LOG_TIMEOUT, LogCommand,
                 options, command_id, -1, cmd, -1, '', '', 0)

  # Try up to a certain number of times.
  for r in range(options.retries):
    tm = time.time()
    p = subprocess.Popen(cmd, shell=True,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         close_fds=ON_POSIX)
    p_stdout = ''
    t_stdout = threading.Thread(target=Tee,
                                args=(p.stdout, p_stdout, sys.stdout))
    t_stdout.start()

    p_stderr = ''
    t_stderr = threading.Thread(target=Tee,
                                args=(p.stderr, p_stderr, sys.stderr))
    t_stderr.start()

    p.wait()

    t_stdout.join()
    t_stderr.join()


    runtime = time.time() - tm
    accept = RunWithTimeout(LOG_TIMEOUT, LogCommand,
                            options, command_id, r, cmd,
                            p.returncode, p_stdout, p_stderr, runtime)
    if accept:
      return p.returncode
    if p.returncode == 0:
      return 0
    print >> sys.stderr, 'Command %s failed with retcode %d, try %d.' % (
        ' '.join(args), p.returncode, r + 1)
  print >> sys.stderr, 'Command %s failed %d retries, giving up.' % (
      ' '.join(args), options.retries)

  return p.returncode


if __name__ == '__main__':
  sys.exit(main(sys.argv))
