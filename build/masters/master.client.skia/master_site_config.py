# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

# NOTE: The Skia buildbot master code currently resides in the Skia repo. The
# code that remains here is out-of-date and unsued, but is still here as a
# placeholder for when Skia upstreams.

from config_bootstrap import Master

class Skia(Master.Master3):
  project_name = 'Skia'
  master_port = 8041
  slave_port = 8141
  master_port_alt = 8241
  server_url = 'http://skia.googlecode.com'
  project_url = 'http://skia.googlecode.com'
  production_host = None
  is_production_host = False
