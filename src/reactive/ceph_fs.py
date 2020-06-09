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

import socket

import dns.resolver

from charms import reactive

import charms_openstack.bus
import charms_openstack.charm as charm

from charmhelpers.core.hookenv import (
    config, log, cached, DEBUG, unit_get,
    network_get_primary_address,
    status_set)
from charmhelpers.contrib.network.ip import (
    get_address_in_network,
    get_ipv6_addr)


charms_openstack.bus.discover()

charm.use_defaults(
    'charm.installed',
    'config.changed',
    'config.rendered',
    'upgrade-charm',
    'update-status',
)


@reactive.when('ceph-mds.available')
def config_changed():
    ceph_mds = reactive.endpoint_from_flag('ceph-mds.available')
    with charm.provide_charm_instance() as cephfs_charm:
        cephfs_charm.configure_ceph_keyring(ceph_mds.mds_key())
        cephfs_charm.render_with_interfaces([ceph_mds])
        if reactive.is_flag_set('config.changed.source'):
            cephfs_charm.upgrade_if_available([ceph_mds])
            reactive.clear_flag('config.changed.source')
        reactive.set_flag('cephfs.configured')
        reactive.set_flag('config.rendered')
        cephfs_charm.assess_status()


def get_networks(config_opt='ceph-public-network'):
    """Get all configured networks from provided config option.

    If public network(s) are provided, go through them and return those for
    which we have an address configured.
    """
    networks = config(config_opt)
    if networks:
        networks = networks.split()
        return [n for n in networks if get_address_in_network(n)]

    return []


@cached
def get_public_addr():
    if config('ceph-public-network'):
        return get_network_addrs('ceph-public-network')[0]

    try:
        return network_get_primary_address('public')
    except NotImplementedError:
        log("network-get not supported", DEBUG)

    return get_host_ip()


@cached
def get_host_ip(hostname=None):
    if config('prefer-ipv6'):
        return get_ipv6_addr()[0]

    hostname = hostname or unit_get('private-address')
    try:
        # Test to see if already an IPv4 address
        socket.inet_aton(hostname)
        return hostname
    except socket.error:
        # This may throw an NXDOMAIN exception; in which case
        # things are badly broken so just let it kill the hook
        answers = dns.resolver.query(hostname, 'A')
        if answers:
            return answers[0].address


def get_network_addrs(config_opt):
    """Get all configured public networks addresses.

    If public network(s) are provided, go through them and return the
    addresses we have configured on any of those networks.
    """
    addrs = []
    networks = config(config_opt)
    if networks:
        networks = networks.split()
        addrs = [get_address_in_network(n) for n in networks]
        addrs = [a for a in addrs if a]

    if not addrs:
        if networks:
            msg = ("Could not find an address on any of '%s' - resolve this "
                   "error to retry" % networks)
            status_set('blocked', msg)
            raise Exception(msg)
        else:
            return [get_host_ip()]

    return addrs
