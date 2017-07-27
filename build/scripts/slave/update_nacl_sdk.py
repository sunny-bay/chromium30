#!/usr/bin/env python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A tool to download/update the NaCl SDK, executed by buildbot.

When this is run, the current directory (cwd) should be the outer build
directory (e.g., chrome-release/build/). The newest pepper bundle will be
copied to nacl_sdk/pepper_current.
"""

from common import chromium_utils
chromium_utils.AddThirdPartyLibToPath('requests_1_2_3')

import os
import re
import shutil
import sys

import requests # pylint: disable=F0401

NACL_SDK_UPDATE_HOST = 'https://storage.googleapis.com'
NACL_SDK_UPDATE_PATH = '/nativeclient-mirror/nacl/nacl_sdk/nacl_sdk.zip'
NACL_SDK_UPDATE_URL = NACL_SDK_UPDATE_HOST + NACL_SDK_UPDATE_PATH
NACL_TOOL = os.path.join('nacl_sdk', 'naclsdk')
CURRENT_PEPPER_BUNDLE = os.path.join('nacl_sdk', 'pepper_current')


def Retrieve(response, file_name):
  """Downloads a file from a response to local destination 'file_name'.
  """
  with open(file_name, 'wb') as f:
    for b in response.iter_content(8192):
      if not b:
        break
      f.write(b)


def main():
  work_dir = os.path.abspath('.')

  print 'Locating NaCl SDK update script at %s' % NACL_SDK_UPDATE_URL
  file_name = NACL_SDK_UPDATE_URL.split('/')[-1]
  response = requests.get(NACL_SDK_UPDATE_URL, verify=True, stream=True)

  print 'Downloading: %s' % file_name
  Retrieve(response, file_name)

  print 'Unzipping %s into %s' % (file_name, work_dir)
  chromium_utils.ExtractZip(file_name, work_dir, verbose=True)

  result = chromium_utils.RunCommand([NACL_TOOL, 'update', '--force'])

  if os.path.exists(CURRENT_PEPPER_BUNDLE):
    print 'Removing current pepper bundle %s' % CURRENT_PEPPER_BUNDLE
    shutil.rmtree(CURRENT_PEPPER_BUNDLE)

  def PepperDirs():
    for x in os.listdir('nacl_sdk'):
      if re.match('pepper_\d+', x):
        yield x

  pepper_rev = max([int(i.split('_')[1]) for i in PepperDirs()])
  pepper_rev_dir = os.path.join('nacl_sdk', 'pepper_' + str(pepper_rev))

  print 'Copying pepper bundle %d to current' % pepper_rev
  shutil.copytree(pepper_rev_dir, CURRENT_PEPPER_BUNDLE, symlinks=True)

  return result


if '__main__' == __name__:
  sys.exit(main())
