#!/usr/bin/env python
# Display health information on commit queue.

import Queue
import multiprocessing
import os
import re
import subprocess
import threading
import time

CQ_LOGS = ['/b/commit-queue/logs-chromium/commit_queue.log',
           '/b/commit-queue/logs-chromium_deps/commit_queue.log',
           '/b/commit-queue/logs-nacl/commit_queue.log',
           '/b/commit-queue/logs-skia/commit_queue.log',
           '/b/commit-queue/logs-tools/commit_queue.log',]


def call(args, timeout=None, shell=False):
  """Returns (code, stdout, stderr)"""
  def _run_proc(args, output):
    proc = subprocess.Popen(
        args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, shell=shell)
    output.put(proc)
    output.put((proc.wait(),) + proc.communicate())

  def _timer(output, timeout):
    time.sleep(timeout)
    output.put([618, '', 'Process timed out.'])

  output = Queue.Queue()
  thr = threading.Thread(target=_run_proc, args=[args, output])
  thr.daemon = True
  thr.start()
  # First item passed through output is always the Popen object.
  proc = output.get()

  # Wait for process to finish, or timeout.
  if timeout:
    timer_thread = threading.Thread(target=_timer, args=[output, timeout])
    timer_thread.daemon = True
    timer_thread.start()

  # Get the first output that comes out, which is either an error from _timer()
  # or the desired output from the process.
  code, out, err = output.get()
  if code == 618:
    # Kill the child process if it timed out.
    try:
      proc.terminate()
      time.sleep(0.5)
      if proc.poll() is None:
        proc.kill()
    except OSError:
      pass

  return code, out, err

def test_num_proc_factory(proc_name):
  def test_num_proc():
    cmd = 'pgrep %s' % proc_name
    _, out, _ = call(cmd, 15, True)
    numproc = len(out.splitlines())
    if numproc < 300:
      return (0, 'OK - %d'  % numproc)
    else:
      return (1, 'FAIL - %d.  This CQ is probably overloaded.' % numproc)
  return test_num_proc

def test_load():
  code , out, _ = call('uptime', 15, True)
  if code == 618:
    return (1, 'FAIL - Process timed out.')

  cpuload_m = re.search(r'(\d+\.\d+)\s*$', out)
  if cpuload_m:
    cpuload = float(cpuload_m.group(1))
    if cpuload < multiprocessing.cpu_count():
      return (0, 'OK - %2f' % cpuload)
    else:
      return (1, 'FAIL - %2f.  This CQ is probably overloaded.' % cpuload)
  else:
    return (1, 'FAIL - Can\'t find cpu load: %s' % out)

def test_log_mod_time_factory(name):
  def test_log_mod_time():
    if not os.path.exists(name):
      return (1, 'FAIL - %s does not exist' % name)
    time_since_modified = time.time() - os.path.getmtime(name)
    if time_since_modified > 120.0:
      return (1, 'FAIL - %d seconds ago.' % time_since_modified)
    return (0, 'OK - %d seconds ago.' % time_since_modified)
  return test_log_mod_time

tests = [
    ('number of python_runtime procs',
     test_num_proc_factory('_python_runtime')),
    ('cpu load', test_load)]
for log_name in CQ_LOGS:
  tests.append(('%s last modified' % log_name,
                test_log_mod_time_factory(log_name)))

def main():
  return_code = 0
  for test_name, test in tests:
    code, msg = test()
    return_code += code
    print '%s: %s' % (test_name, msg)
  print 'status: %d' % return_code

if __name__ == '__main__':
  main()
