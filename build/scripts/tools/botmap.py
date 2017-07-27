#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Dumps a list of known slaves, along with their OS and master."""

import os
import sys
path = os.path.join(os.path.dirname(__file__), os.path.pardir)
sys.path.append(path)
from common import chromium_utils


def main():
  # remove slaves with blank or no hostname
  slaves = filter(lambda x: x.get('hostname'), chromium_utils.GetAllSlaves())
  slaves.sort(key=lambda x: (x.get('mastername'), x['hostname']))
  for slave in slaves:
    if slave.get('os') == 'win':
      pathsep = '\\'
    else:
      pathsep = '/'
    if 'subdir' in slave:
      slavedir = pathsep + 'c' + pathsep + slave['subdir']
    else:
      slavedir = pathsep + 'b'
    builder = slave.get('builder') or '?'
    if type(builder) is not list:
      builder = [builder]
    for b in sorted(builder):
      print '%-30s %-20s %-35s %-35s %-10s' % (
          slave['hostname'],
          slavedir,
          slave.get('mastername', '?'),
          b,
          slave.get('os', '?'))


if __name__ == '__main__':
  main()
