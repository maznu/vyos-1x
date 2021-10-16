#!/usr/bin/env python3
#
# Copyright (C) 2019-2020 VyOS maintainers and contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 or later as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import re
import unittest

from base_vyostest_shim import VyOSUnitTestSHIM

from vyos.configsession import ConfigSession
from vyos.configsession import ConfigSessionError
from vyos.util import cmd
from vyos.util import process_named_running
from vyos.util import read_file

PROCESS_NAME = 'sshd'
SSHD_CONF = '/run/sshd/sshd_config'
base_path = ['service', 'ssh']
vrf = 'mgmt'

key_rsa = '/etc/ssh/ssh_host_rsa_key'
key_dsa = '/etc/ssh/ssh_host_dsa_key'
key_ed25519 = '/etc/ssh/ssh_host_ed25519_key'

def get_config_value(key):
    tmp = read_file(SSHD_CONF)
    tmp = re.findall(f'\n?{key}\s+(.*)', tmp)
    return tmp

class TestServiceSSH(VyOSUnitTestSHIM.TestCase):
    @classmethod
    def setUpClass(cls):
        super(cls, cls).setUpClass()

        # ensure we can also run this test on a live system - so lets clean
        # out the current configuration :)
        cls.cli_delete(cls, base_path)

    def tearDown(self):
        # delete testing SSH config
        self.cli_delete(base_path)
        self.cli_commit()

        self.assertTrue(os.path.isfile(key_rsa))
        self.assertTrue(os.path.isfile(key_dsa))
        self.assertTrue(os.path.isfile(key_ed25519))

    def test_ssh_default(self):
        # Check if SSH service runs with default settings - used for checking
        # behavior of <defaultValue> in XML definition
        self.cli_set(base_path)

        # commit changes
        self.cli_commit()

        # Check configured port
        port = get_config_value('Port')[0]
        self.assertEqual('22', port)

        # Check for running process
        self.assertTrue(process_named_running(PROCESS_NAME))

    def test_ssh_single_listen_address(self):
        # Check if SSH service can be configured and runs
        self.cli_set(base_path + ['port', '1234'])
        self.cli_set(base_path + ['disable-host-validation'])
        self.cli_set(base_path + ['disable-password-authentication'])
        self.cli_set(base_path + ['loglevel', 'verbose'])
        self.cli_set(base_path + ['client-keepalive-interval', '100'])
        self.cli_set(base_path + ['listen-address', '127.0.0.1'])

        # commit changes
        self.cli_commit()

        # Check configured port
        port = get_config_value('Port')[0]
        self.assertTrue("1234" in port)

        # Check DNS usage
        dns = get_config_value('UseDNS')[0]
        self.assertTrue("no" in dns)

        # Check PasswordAuthentication
        pwd = get_config_value('PasswordAuthentication')[0]
        self.assertTrue("no" in pwd)

        # Check loglevel
        loglevel = get_config_value('LogLevel')[0]
        self.assertTrue("VERBOSE" in loglevel)

        # Check listen address
        address = get_config_value('ListenAddress')[0]
        self.assertTrue("127.0.0.1" in address)

        # Check keepalive
        keepalive = get_config_value('ClientAliveInterval')[0]
        self.assertTrue("100" in keepalive)

        # Check for running process
        self.assertTrue(process_named_running(PROCESS_NAME))

    def test_ssh_multiple_listen_addresses(self):
        # Check if SSH service can be configured and runs with multiple
        # listen ports and listen-addresses
        ports = ['22', '2222', '2223', '2224']
        for port in ports:
            self.cli_set(base_path + ['port', port])

        addresses = ['127.0.0.1', '::1']
        for address in addresses:
            self.cli_set(base_path + ['listen-address', address])

        # commit changes
        self.cli_commit()

        # Check configured port
        tmp = get_config_value('Port')
        for port in ports:
            self.assertIn(port, tmp)

        # Check listen address
        tmp = get_config_value('ListenAddress')
        for address in addresses:
            self.assertIn(address, tmp)

        # Check for running process
        self.assertTrue(process_named_running(PROCESS_NAME))

    def test_ssh_vrf(self):
        # Check if SSH service can be bound to given VRF
        port = '22'
        self.cli_set(base_path + ['port', port])
        self.cli_set(base_path + ['vrf', vrf])

        # VRF does yet not exist - an error must be thrown
        with self.assertRaises(ConfigSessionError):
            self.cli_commit()

        self.cli_set(['vrf', 'name', vrf, 'table', '1338'])

        # commit changes
        self.cli_commit()

        # Check configured port
        tmp = get_config_value('Port')
        self.assertIn(port, tmp)

        # Check for running process
        self.assertTrue(process_named_running(PROCESS_NAME))

        # Check for process in VRF
        tmp = cmd(f'ip vrf pids {vrf}')
        self.assertIn(PROCESS_NAME, tmp)

        # delete VRF
        self.cli_delete(['vrf', 'name', vrf])

if __name__ == '__main__':
    unittest.main(verbosity=2)
