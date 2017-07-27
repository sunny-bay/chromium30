# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class WebRTC(Master.Master3):
  project_name = 'WebRTC'
  master_port = 8060
  slave_port = 8160
  master_port_alt = 8260
  server_url = 'http://webrtc.googlecode.com'
  project_url = 'http://webrtc.googlecode.com'
  from_address = 'webrtc-cb-watchlist@google.com'
  permitted_domains = ('google.com', 'chromium.org', 'webrtc.org')
