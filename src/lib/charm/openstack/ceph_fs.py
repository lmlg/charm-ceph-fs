# Copyright 2020 Canonical Ltd
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

import charms_openstack.adapters
import charms_openstack.charm
import charms_openstack.plugins

import charmhelpers.core as ch_core

import reactive.ceph_fs

charms_openstack.charm.use_defaults('charm.default-select-release')


class CephFSCharmConfigurationAdapter(
        charms_openstack.adapters.ConfigurationAdapter):

    @property
    def hostname(self):
        return self.charm_instance.hostname

    @property
    def mds_name(self):
        return self.charm_instance.hostname

    @property
    def networks(self):
        return reactive.ceph_fs.get_networks('ceph-public-network')

    @property
    def public_addr(self):
        if ch_core.hookenv.config('prefer-ipv6'):
            return reactive.ceph_fs.get_ipv6_addr()[0]
        else:
            return reactive.ceph_fs.get_public_addr()


class CephFSCharmRelationAdapters(
        charms_openstack.adapters.OpenStackRelationAdapters):
    relation_adapters = {
        'ceph-mds': charms_openstack.plugins.CephRelationAdapter,
    }


class BaseCephFSCharm(charms_openstack.plugins.CephCharm):
    abstract_class = True
    name = 'ceph-fs'
    python_version = 3
    required_relations = ['ceph-mds']
    user = 'ceph'
    group = 'ceph'
    adapters_class = CephFSCharmRelationAdapters
    configuration_class = CephFSCharmConfigurationAdapter
    ceph_service_type = charms_openstack.plugins.CephCharm.CephServiceType.mds
    ceph_service_name_override = 'mds'
    ceph_key_per_unit_name = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.services = [
            'ceph-mds@{}'.format(self.hostname),
        ]
        self.restart_map = {
            '/etc/ceph/ceph.conf': self.services,
        }


class MitakaCephFSCharm(BaseCephFSCharm):
    release = 'mitaka'
    packages = ['ceph-mds', 'gdisk', 'ntp', 'btrfs-tools', 'xfsprogs']


class UssuriCephFSCharm(BaseCephFSCharm):
    release = 'ussuri'
    packages = ['ceph-mds', 'gdisk', 'ntp', 'btrfs-progs', 'xfsprogs']
