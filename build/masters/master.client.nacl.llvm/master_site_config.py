# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class NativeClientLLVM(Master.NaClBase):
  project_name = 'NativeClientLLVM'
  master_port = 8046
  slave_port = 8146
  master_port_alt = 8246
