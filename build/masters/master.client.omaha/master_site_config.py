# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class Omaha(Master.Master3):
  project_name = 'Omaha'
  project_url = 'http://code.google.com/p/omaha/'
  master_port = 8049
  slave_port = 8149
  master_port_alt = 8249
