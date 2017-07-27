# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class Gatekeeper(Master.Base):
  project_name = 'Chromium Gatekeeper'
  master_host = 'localhost'
  master_port = 9511
  slave_port = 9611
  master_port_alt = 9711
