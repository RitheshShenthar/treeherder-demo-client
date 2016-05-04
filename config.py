# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os

here = os.path.dirname(os.path.abspath(__file__))

config = {
    'test_types': {
        'functional': {
            'treeherder': {
                'group_name': 'TES',
                'group_symbol': 'TEST',
                'job_name': 'Trial ({locale})',
                'job_symbol': '{locale}',
                'tier': 2,
                'log_reference': 'https://s3-us-west-1.amazonaws.com/services-qa-jenkins-artifacts/jobs/dummy-test/7/log_info.txt',
            },
        },
    },
}
