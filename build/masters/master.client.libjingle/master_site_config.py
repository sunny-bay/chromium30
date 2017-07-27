# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class Libjingle(Master.Master3):
  project_name = 'Libjingle'
  master_port = 8061
  slave_port = 8161
  master_port_alt = 8261
  server_url = 'http://webrtc.googlecode.com'
  project_url = 'http://webrtc.googlecode.com'
  from_address = 'libjingle-cb-watchlist@google.com'
