# Copyright 2016 Cloudbase Solutions Srl
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from nova.policies import base


BASE_POLICY_NAME = 'os_compute_api:os-floating-ips-bulk'


floating_ips_bulk_policies = [
    base.create_rule_default(
        BASE_POLICY_NAME,
        base.RULE_ADMIN_API,
        "Bulk-create, delete, and list floating IPs. API is deprecated.",
        [
            {
                'method': 'GET',
                'path': '/os-floating-ips-bulk'
            },
            {
                'method': 'POST',
                'path': '/os-floating-ips-bulk'
            },
            {
                'method': 'PUT',
                'path': '/os-floating-ips-bulk/delete'
            },
            {
                'method': 'GET',
                'path': '/os-floating-ips-bulk/{host_name}'
            },
        ]),
]


def list_rules():
    return floating_ips_bulk_policies
