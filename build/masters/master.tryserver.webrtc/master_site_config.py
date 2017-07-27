# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class WebRTCTryServer(Master.Master4):
  project_name = 'WebRTC Try Server'
  master_port = 8070
  slave_port = 8170
  master_port_alt = 8270
  try_job_port = 8370
  from_address = 'tryserver@webrtc.org'
  reply_to = 'chrome-troopers+tryserver@google.com'
  permitted_domains = ('google.com', 'chromium.org', 'webrtc.org')
  svn_url = 'svn://svn.chromium.org/chrome-try/try-webrtc'
  last_good_url = 'http://webrtc-dashboard.appspot.com/lkgr'
  code_review_site = 'http://review.webrtc.org'
