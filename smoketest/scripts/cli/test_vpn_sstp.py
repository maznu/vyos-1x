#!/usr/bin/env python3
#
# Copyright (C) 020 VyOS maintainers and contributors
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

import unittest

from base_accel_ppp_test import BasicAccelPPPTest

process_name = 'accel-pppd'

class TestVPNSSTPServer(BasicAccelPPPTest.BaseTest):
    def setUp(self):
        self._base_path = ['vpn', 'sstp']
        super().setUp()

    def tearDown(self):
        self.session.delete(local_if)
        super().tearDown()

if __name__ == '__main__':
    unittest.main()