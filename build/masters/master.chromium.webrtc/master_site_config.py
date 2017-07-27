# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class ChromiumWebRTC(Master.Master1):
  project_name = 'Chromium WebRTC'
  master_port = 8054
  slave_port = 8154
  master_port_alt = 8254
  server_url = 'http://webrtc.googlecode.com'
  project_url = 'http://webrtc.googlecode.com'
  from_address = 'webrtc-cb-watchlist@google.com'
  permitted_domains = ('google.com', 'chromium.org', 'webrtc.org')
