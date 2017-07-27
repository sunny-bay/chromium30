#!/usr/bin/env python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Manages the initial bootstrapping.

Automatically generates the dimensions for the current machine and stores them
in the given file.
"""

import cStringIO
import json
import logging
import optparse
import os
import socket
import subprocess
import sys
import urllib2
import zipfile

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# A mapping between sys.platform values and the corresponding swarm name
# for that platform.
PLATFORM_MAPPING = {
  'cygwin': 'Windows',
  'darwin': 'Mac',
  'linux2': 'Linux',
  'win32': 'Windows',
}


def WriteJsonToFile(filepath, data):
  return WriteToFile(filepath, json.dumps(data, sort_keys=True, indent=2))


def WriteToFile(filepath, content):
  """Writes out a json file.

  Returns True on success.
  """
  try:
    with open(filepath, mode='w') as f:
      f.write(content)
    return True
  except IOError as e:
    logging.error('Cannot write file %s: %s', filepath, e)
    return False


def GetDimensions(hostname, platform):
  """Returns a dictionary of attributes representing this machine.

  Returns:
    A dictionary of the attributes of the machine.
  """
  if sys.platform not in PLATFORM_MAPPING:
    logging.error('Running on an unknown platform, %s, unable to '
                  'generate dimensions', sys.platform)
    return {}

  return {
    'dimensions': {
      'os': PLATFORM_MAPPING[platform],
    },
    'tag': hostname,
  }


def GetChromiumDimensions(hostname, platform):
  """Returns chromium infrastructure specific dimensions."""
  dimensions = GetDimensions(hostname, platform)
  if not dimensions:
    return dimensions

  hostname = dimensions['tag']
  # Get the vlan of this machine from the hostname when it's in the form
  # '<host>-<vlan>'.
  if '-' in hostname:
    dimensions['dimensions']['vlan'] = hostname.split('-')[-1]
    # Replace vlan starting with 'c' to 'm'.
    if dimensions['dimensions']['vlan'][0] == 'c':
      dimensions['dimensions']['vlan'] = (
          'm' + dimensions['dimensions']['vlan'][1:])
  return dimensions


def DownloadSwarmBot(swarm_server):
  """Downloads the latest version of swarm_bot code directly from the Swarm
  server.

  It is assumed that this will download a file named slave_machine.py.

  Returns True on success.
  """
  swarm_get_code_url = swarm_server.rstrip('/') + '/get_slave_code'
  try:
    response = urllib2.urlopen(swarm_get_code_url)
  except urllib2.URLError as e:
    logging.error('Unable to download swarm slave code from %s.\n%s',
                  swarm_get_code_url, e)
    return False

  # 'response' doesn't act exactly like a file so we can't pass it directly
  # to the zipfile reader.
  z = zipfile.ZipFile(cStringIO.StringIO(response.read()), 'r')
  try:
    z.extractall()
  finally:
    z.close()
  return True


def CreateStartSlave(filepath):
  """Creates the python scripts that is called to restart the swarm bot slave.

  See src/swarm_bot/slave_machine.py in the swarm server code about why this is
  needed.
  """
  content = (
    'import slave_machine\n'
    'slave_machine.Restart()\n')
  return WriteToFile(filepath, content)


def SetupAutoStartupWin(command):
  """Uses Startup folder in the Start Menu."""
  # TODO(maruel): Not always true. Read from registry if needed.
  filepath = os.path.expanduser(
      '~\\AppData\\Roaming\\Microsoft\\Windows\\'
      'Start Menu\\Programs\\Startup\\run_swarm_bot.bat')
  content = '@cd /d ' + BASE_DIR + ' && ' + ' '.join(command)
  return WriteToFile(filepath, content)


def GenerateLaunchdPlist(command):
  """Generates a plist with the corresponding command."""
  # The documentation is available at:
  # https://developer.apple.com/library/mac/documentation/Darwin/Reference/ \
  #    ManPages/man5/launchd.plist.5.html
  entries = [
    '<key>Label</key><string>org.swarm.bot</string>',
    '<key>StandardOutPath</key><string>swarm_bot.log</string>',
    '<key>StandardErrorPath</key><string>swarm_bot-err.log</string>',
    '<key>LimitLoadToSessionType</key><array><string>Aqua</string></array>',
    '<key>RunAtLoad</key><true/>',
    '<key>Umask</key><integer>18</integer>',

    '<key>EnvironmentVariables</key>',
    '<dict>',
    '  <key>PATH</key>',
    '  <string>/opt/local/bin:/opt/local/sbin:/usr/local/sbin:/usr/local/bin'
      ':/usr/sbin:/usr/bin:/sbin:/bin</string>',
    '</dict>',

    '<key>SoftResourceLimits</key>',
    '<dict>',
    '  <key>NumberOfFiles</key>',
    '  <integer>8000</integer>',
    '</dict>',
  ]
  entries.append('<key>Program</key><string>%s</string>' % command[0])
  entries.append('<key>ProgramArguments</key>')
  entries.append('<array>')
  # Command[0] must be passed as an argument.
  entries.extend('  <string>%s</string>' % i for i in command)
  entries.append('</array>')
  entries.append('<key>WorkingDirectory</key><string>%s</string>' % BASE_DIR)
  header = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
    '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
    '<plist version="1.0">\n'
    '  <dict>\n'
    + ''.join('    %s\n' % l for l in entries) +
    '  </dict>\n'
    '</plist>\n')
  return header


def SetupAutoStartupOSX(command):
  """Uses launchd with auto-login user."""
  plistname = os.path.expanduser('~/Library/LaunchAgents/org.swarm.bot.plist')
  return WriteToFile(plistname, GenerateLaunchdPlist(command))


def SetupAutoStartupUnix(command):
  """Uses crontab."""
  # The \n is very important.
  content = '@reboot cd %s && %s\n' % (BASE_DIR, ' '.join(command))
  if not WriteToFile('mycron', content):
    return False

  try:
    # It returns 1 if there was no cron job set.
    subprocess.call(['crontab', '-r'])
    subprocess.check_call(['crontab', 'mycron'])
  finally:
    os.remove('mycron')
  return True


def SetupAutoStartup(slave_machine, swarm_server, dimensionsfile):
  command = [
    sys.executable,
    slave_machine,
    '-a', swarm_server,
    '-p', '443',
    '-r', '400',
    '--keep_alive',
    '-v',
    dimensionsfile,
  ]
  if sys.platform == 'win32':
    return SetupAutoStartupWin(command)
  elif sys.platform == 'darwin':
    return SetupAutoStartupOSX(command)
  else:
    return SetupAutoStartupUnix(command)


def main():
  # Simplify the code by setting the current directory as the directory
  # containing this file.
  os.chdir(BASE_DIR)

  parser = optparse.OptionParser(description=sys.modules[__name__].__doc__)
  parser.add_option('-d', '--dimensionsfile', default='dimensions.in')
  parser.add_option('-s', '--swarm-server')
  parser.add_option('--no-auto-start', action='store_true',
                    help='Do not setup the swarm bot to auto start on boot.')
  parser.add_option('--no-reboot', action='store_true',
                    help='Do not reboot at the end of the setup.')
  parser.add_option('-v', '--verbose', action='store_true',
                    help='Set logging level to DEBUG. Optional. Defaults to '
                    'ERROR level.')
  (options, args) = parser.parse_args()

  if args:
    parser.error('Unexpected argument, %s' % args)
  if not options.swarm_server:
    parser.error('Swarm server is required.')

  logging.basicConfig(level=logging.DEBUG if options.verbose else logging.ERROR)

  options.dimensionsfile = os.path.abspath(options.dimensionsfile)

  print('Generating the machine dimensions...')
  hostname = socket.gethostname().lower().split('.', 1)[0]
  dimensions = GetChromiumDimensions(hostname, sys.platform)
  if not WriteJsonToFile(options.dimensionsfile, dimensions):
    return 1

  print('Downloading newest swarm_bot code...')
  if not DownloadSwarmBot(options.swarm_server):
    return 1

  slave_machine = os.path.join(BASE_DIR, 'slave_machine.py')
  if not os.path.isfile(slave_machine):
    print('Failed to find %s' % slave_machine)
    return 1

  print('Create start_slave.py script...')
  if not CreateStartSlave(os.path.join(BASE_DIR, 'start_slave.py')):
    return 1

  if not options.no_auto_start:
    print('Setup up swarm script to run on startup...')
    if not SetupAutoStartup(
        slave_machine, options.swarm_server, options.dimensionsfile):
      return 1

  if not options.no_reboot:
    print('Rebooting...')
    if sys.platform == 'win32':
      result = subprocess.call(['shutdown', '-r', '-f', '-t', '1'])
    else:
      result = subprocess.call(['sudo', 'shutdown', '-r', 'now'])
    if result:
      print('Please reboot the slave manually.')
    return result

  return 0


if __name__ == '__main__':
  sys.exit(main())
