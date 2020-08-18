# Copyright 2016 Canonical Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from charms import reactive
from charmhelpers.core.hookenv import (
    service_name,
    config)

import charms_openstack.bus
import charms_openstack.charm as charm


charms_openstack.bus.discover()


charm.use_defaults(
    'charm.installed',
    'config.changed',
    'config.rendered',
    'upgrade-charm',
    'update-status',
)


@reactive.when_none('charm.paused', 'run-default-update-status')
@reactive.when('ceph-mds.pools.available')
def config_changed():
    ceph_mds = reactive.endpoint_from_flag('ceph-mds.pools.available')
    with charm.provide_charm_instance() as cephfs_charm:
        cephfs_charm.configure_ceph_keyring(ceph_mds.mds_key())
        cephfs_charm.render_with_interfaces([ceph_mds])
        if reactive.is_flag_set('config.changed.source'):
            # update system source configuration and check for upgrade
            cephfs_charm.install()
            cephfs_charm.upgrade_if_available([ceph_mds])
            reactive.clear_flag('config.changed.source')
        reactive.set_flag('cephfs.configured')
        reactive.set_flag('config.rendered')
        cephfs_charm.assess_status()


@reactive.when_not('ceph.create_pool.req.sent')
@reactive.when('ceph-mds.connected')
def storage_ceph_connected(ceph):
    ceph_mds = reactive.endpoint_from_flag('ceph-mds.connected')
    ceph_mds.announce_mds_name()
    service = service_name()
    weight = config('ceph-pool-weight')
    replicas = config('ceph-osd-replication-count')

    if config('rbd-pool-name'):
        pool_name = config('rbd-pool-name')
    else:
        pool_name = "{}_data".format(service)

    # The '_' rather than '-' in the default pool name
    # maintains consistency with previous versions of the
    # charm but is inconsistent with ceph-client charms.
    metadata_pool_name = (
        config('metadata-pool') or
        "{}_metadata".format(service)
    )
    # Metadata sizing is approximately 1% of overall data weight
    # but is in effect driven by the number of rbd's rather than
    # their size - so it can be very lightweight.
    metadata_weight = weight * 0.01
    # Resize data pool weight to accomodate metadata weight
    weight = weight - metadata_weight

    if config('pool-type') == 'erasure-coded':
        # General EC plugin config
        plugin = config('ec-profile-plugin')
        technique = config('ec-profile-technique')
        device_class = config('ec-profile-device-class')
        bdm_k = config('ec-profile-k')
        bdm_m = config('ec-profile-m')
        # LRC plugin config
        bdm_l = config('ec-profile-locality')
        crush_locality = config('ec-profile-crush-locality')
        # SHEC plugin config
        bdm_c = config('ec-profile-durability-estimator')
        # CLAY plugin config
        bdm_d = config('ec-profile-helper-chunks')
        scalar_mds = config('ec-profile-scalar-mds')
        # Profile name
        profile_name = (
            config('ec-profile-name') or "{}-profile".format(service)
        )
        # Create erasure profile
        ceph_mds.create_erasure_profile(
            name=profile_name,
            k=bdm_k, m=bdm_m,
            lrc_locality=bdm_l,
            lrc_crush_locality=crush_locality,
            shec_durability_estimator=bdm_c,
            clay_helper_chunks=bdm_d,
            clay_scalar_mds=scalar_mds,
            device_class=device_class,
            erasure_type=plugin,
            erasure_technique=technique
        )

        # Create EC data pool
        ceph_mds.create_erasure_pool(
            name=pool_name,
            erasure_profile=profile_name,
            weight=weight,
            app_name=ceph_mds.ceph_pool_app_name,
            allow_ec_overwrites=True
        )
        ceph_mds.create_replicated_pool(
            name=metadata_pool_name,
            weight=metadata_weight,
            app_name=ceph_mds.ceph_pool_app_name
        )
    else:
        ceph_mds.create_replicated_pool(
            name=pool_name,
            replicas=replicas,
            weight=weight,
            app_name=ceph_mds.ceph_pool_app_name)
        ceph_mds.create_replicated_pool(
            name=metadata_pool_name,
            replicas=replicas,
            weight=metadata_weight,
            app_name=ceph_mds.ceph_pool_app_name)
    ceph_mds.request_cephfs(service)
    reactive.set_state('ceph.create_pool.req.sent')
