# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from nova.tests.functional import integrated_helpers


class FinishResizeErrorAllocationCleanupTestCase(
        integrated_helpers.ProviderUsageBaseTestCase):
    """Test for bug 1825537 introduced in Rocky and backported down to Pike.

    Tests a scenario where finish_resize fails on the dest compute during a
    resize and ensures resource provider allocations are properly cleaned up
    in placement.
    """

    compute_driver = 'fake.FakeFinishMigrationFailDriver'

    # ProviderUsageBaseTestCase uses the AllServicesCurrent fixture which
    # means we'll use migration-based allocations by default. This flag allows
    # us to control the logic in conductor to handle legacy allocations where
    # the source (old flavor) and dest (new flavor) node allocations are
    # doubled up on the instance.
    migration_based_allocations = True

    def setUp(self):
        super(FinishResizeErrorAllocationCleanupTestCase, self).setUp()
        # Get the flavors we're going to use.
        flavors = self.api.get_flavors()
        self.flavor1 = flavors[0]
        self.flavor2 = flavors[1]

        self.stub_out('nova.conductor.tasks.migrate.'
                      'should_do_migration_allocation',
                      lambda *args, **kwargs: self.migration_based_allocations)

    def _resize_and_assert_error(self, server, dest_host):
        # Now resize the server and wait for it to go to ERROR status because
        # the finish_migration virt driver method in host2 should fail.
        req = {'resize': {'flavorRef': self.flavor2['id']}}
        self.api.post_server_action(server['id'], req)
        # The instance is set to ERROR status before the fault is recorded so
        # to avoid a race we need to wait for the task_state to change
        # to None which happens after the fault is recorded.
        server = self._wait_for_server_parameter(
            self.admin_api, server,
            {'status': 'ERROR', 'OS-EXT-STS:task_state': None})
        # The server should be pointing at $dest_host because resize_instance
        # will have updated the host/node value on the instance before casting
        # to the finish_resize method on the dest compute.
        self.assertEqual(dest_host, server['OS-EXT-SRV-ATTR:host'])
        # In this case the FakeFinishMigrationFailDriver.finish_migration
        # method raises VirtualInterfaceCreateException.
        self.assertIn('Virtual Interface creation failed',
                      server['fault']['message'])

    def test_finish_resize_fails_allocation_cleanup(self):
        # Start two computes so we can resize across hosts.
        self._start_compute('host1')
        self._start_compute('host2')

        # Create a server on host1.
        server = self._boot_and_check_allocations(self.flavor1, 'host1')

        # Resize to host2 which should fail.
        self._resize_and_assert_error(server, 'host2')

        # Check the resource provider allocations. Since the server is pointed
        # at the dest host in the DB now, the dest node resource provider
        # allocations should still exist with the new flavor.
        source_rp_uuid = self._get_provider_uuid_by_host('host1')
        dest_rp_uuid = self._get_provider_uuid_by_host('host2')
        dest_rp_usages = self._get_provider_usages(dest_rp_uuid)
        self.assertFlavorMatchesAllocation(self.flavor2, dest_rp_usages)
        # And the source node provider should not have any usage.
        source_rp_usages = self._get_provider_usages(source_rp_uuid)
        no_usage = {'VCPU': 0, 'MEMORY_MB': 0, 'DISK_GB': 0}
        self.assertEqual(no_usage, source_rp_usages)


class FinishResizeErrorAllocationCleanupLegacyTestCase(
        FinishResizeErrorAllocationCleanupTestCase):
    """Variant of FinishResizeErrorAllocationCleanupTestCase which does not
    use migration-based allocations, e.g. tests the scenario that there are
    older computes in the deployment so the source and dest node allocations
    are doubled up on the instance consumer record rather than the migration
    record.
    """
    migration_based_allocations = False
