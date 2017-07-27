# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'gclient',
  'json',
  'path',
  'properties',
  'python',
  'rietveld',
  'step',
  'step_history',
]

def GenSteps(api):
  api.chromium.set_config('blink')
  api.chromium.apply_config('trybot_flavor')
  api.gclient.set_config('blink_internal',
                         GIT_MODE=api.properties.get('GIT_MODE', False))
  api.step.auto_resolve_conflicts = True

  webkit_lint = api.path.build('scripts', 'slave', 'chromium',
                               'lint_test_files_wrapper.py')
  webkit_python_tests = api.path.build('scripts', 'slave', 'chromium',
                                       'test_webkitpy_wrapper.py')


  def BlinkTestsStep(with_patch):
    def followup_fn(step_result):
      if step_result.retcode > 0:
        step_result.presentation.status = 'WARNING'

    name = 'webkit_tests (with%s patch)' % ('' if with_patch else 'out')
    test = api.path.build('scripts', 'slave', 'chromium',
                          'layout_test_wrapper.py')
    args = ['--target', api.chromium.c.BUILD_CONFIG,
            '-o', api.path.slave_build('layout-test-results'),
            '--build-dir', api.path.checkout(api.chromium.c.build_dir),
            api.json.output()]
    return api.chromium.runtests(test, args, name=name, can_fail_build=False,
                                 followup_fn=followup_fn)

  yield (
    api.gclient.checkout(),
    api.rietveld.apply_issue('third_party', 'WebKit'),
    api.chromium.runhooks(),
    api.chromium.compile(),
    api.python('webkit_lint', webkit_lint, [
      '--build-dir', api.path.checkout('out'),
      '--target', api.properties['build_config']]),
    api.python('webkit_python_tests', webkit_python_tests, [
      '--build-dir', api.path.checkout('out'),
      '--target', api.properties['build_config']
    ]),
    api.chromium.runtests('webkit_unit_tests'),
    api.chromium.runtests('weborigin_unittests'),
    api.chromium.runtests('wtf_unittests'),
  )

  yield BlinkTestsStep(with_patch=True)
  if api.step_history.last_step().retcode == 0:
    yield api.python.inline('webkit_tests', 'print "ALL IS WELL"')
    return

  failing_tests = api.step_history.last_step().json.output

  yield (
    api.gclient.revert(),
    api.chromium.runhooks(),
    api.chromium.compile(),
    BlinkTestsStep(with_patch=False),
  )
  base_failing_tests = api.step_history.last_step().json.output

  yield api.python(
    'webkit_tests',
    api.path.checkout('third_party', 'WebKit', 'Tools', 'Scripts',
                      'print-json-test-results'),
    ['--ignored-failures-path', api.json.input(base_failing_tests),
      api.json.input(failing_tests)]
  )


def GenTests(api):
  SUCCESS_DATA = lambda: {}

  FAIL_DATA = lambda: {
    'webkit_tests (with patch)': {
      'json': {'output': {'crazy': ['data', 'format']}},
      '$R': 1
    },
    'webkit_tests (without patch)': {
      'json': {'output': {'crazy': ['data', 'format']}},
      '$R': 1
    },
  }

  for result, step_mocks in [('success', SUCCESS_DATA), ('fail', FAIL_DATA)]:
    for build_config in ['Release', 'Debug']:
      for plat in ('win', 'mac', 'linux'):
        for git_mode in True, False:
          suffix = '_git' if git_mode else ''
          yield ('%s_%s_%s%s' % (plat, result, build_config.lower(), suffix)), {
            'properties': api.properties_tryserver(
              build_config=build_config,
              config_name='blink',
              root='src/third_party/WebKit',
              GIT_MODE=git_mode,
            ),
            'step_mocks': step_mocks(),
            'mock': {
              'platform': {
                'name': plat
              }
            }
          }
