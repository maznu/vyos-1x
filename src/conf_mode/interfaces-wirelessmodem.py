#!/usr/bin/env python3
#
# Copyright (C) 2020 VyOS maintainers and contributors
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

from sys import exit
from copy import deepcopy
from jinja2 import Template
from subprocess import Popen, PIPE
from pwd import getpwnam
from grp import getgrnam

from vyos.config import Config
from vyos import ConfigError

# Please be careful if you edit the template.
config_wwan_tmpl = """### Autogenerated by interfaces-wirelessmodem.py ###
{% if description %}
# {{ description }}
{% endif %}

# physical device
/dev/{{ device }}

ipparam {{ intf }} {{ metric }}
{% if on_demand -%}
demand
{%- endif %}
{% if name_server -%}
usepeerdns
{%- endif %}
logfile {{ logfile }}
linkname {{ intf }}
lcp-echo-failure 0
115200
debug
nodefaultroute
ipcp-max-failure 4
ipcp-accept-local
ipcp-accept-remote
noauth
crtscts
lock
persist


"""

default_config_data = {
    'address': [],
    'deleted': False,
    'description': '',
    'device': 'ttyUSB0',
    'disable': False,
    'disable_link_detect': 1,
    'on_demand': False,
    'logfile': '',
    'metric': '10',
    'mtu': '1500',
    'name_server': True,
    'network': 'att',
    'intf': ''
}

def subprocess_cmd(command):
    p = Popen(command, stdout=PIPE, shell=True)
    p.communicate()

def check_kmod():
    modules = ['option', 'usb_wwan', 'usbserial']
    for module in modules:
        if not os.path.exists(f'/sys/module/{module}'):
            if os.system(f'modprobe {module}') != 0:
                raise ConfigError(f'Loading Kernel module {module} failed')

def get_config():
    wwan = deepcopy(default_config_data)
    conf = Config()

    # determine tagNode instance
    if 'VYOS_TAGNODE_VALUE' not in os.environ:
        raise ConfigError('Interface (VYOS_TAGNODE_VALUE) not specified')

    wwan['intf'] = os.environ['VYOS_TAGNODE_VALUE']
    wwan['logfile'] = f"/var/log/vyatta/ppp_{wwan['intf']}.log"

    # Check if interface has been removed
    if not conf.exists('interfaces wirelessmodem ' + wwan['intf']):
        wwan['deleted'] = True
        return wwan

    # set new configuration level
    conf.set_level('interfaces wirelessmodem ' + wwan['intf'])

    # get metrick for backup default route
    if conf.exists(['backup', 'distance']):
        wwan['metric'] = conf.return_value(['backup', 'distance'])

    # Retrieve interface description
    if conf.exists(['description']):
        wwan['description'] = conf.return_value(['description'])

    # System device name
    if conf.exists(['device']):
        wwan['device'] = conf.return_value(['device'])

    # ignore link state changes
    if conf.exists('disable-link-detect'):
        wwan['disable_link_detect'] = 2

    # Do not use DNS servers provided by the peer
    if conf.exists(['mtu']):
        wwan['mtu'] = conf.return_value(['mtu'])

    # Do not use DNS servers provided by the peer
    if conf.exists(['network']):
        wwan['network'] = conf.return_value(['network'])

    # Do not use DNS servers provided by the peer
    if conf.exists(['no-dns']):
        wwan['name_server'] = False

    # Access concentrator name (only connect to this concentrator)
    if conf.exists(['ondemand']):
        wwan['on_demand'] = True

    return wwan

def verify(wwan):
    if wwan['deleted']:
        return None

    # we can not use isfile() here as Linux device files are no regular files
    # thus the check will return False
    if not os.path.exists(f"/dev/{wwan['device']}"):
        raise ConfigError(f"Device {wwan['device']} does not exist")

    return None

def generate(wwan):
    config_file_wwan = f"/etc/ppp/peers/{wwan['intf']}"

    # Always hang-up WWAN connection prior generating new configuration file
    cmd = f"systemctl stop ppp@{wwan['intf']}.service"
    subprocess_cmd(cmd)

    if wwan['deleted']:
        # Delete PPP configuration files
        if os.path.exists(config_file_wwan):
            os.unlink(config_file_wwan)

    else:
        # Create PPP configuration files
        tmpl = Template(config_wwan_tmpl)
        config_text = tmpl.render(wwan)
        with open(config_file_wwan, 'w') as f:
            f.write(config_text)

    return None

def apply(wwan):
    if wwan['deleted']:
        # bail out early
        return None

    if not wwan['disable']:
        # dial WWAN connection
        cmd = f"systemctl start ppp@{wwan['intf']}.service"
        subprocess_cmd(cmd)

        # make logfile owned by root / vyattacfg
        if os.path.isfile(wwan['logfile']):
            uid = getpwnam('root').pw_uid
            gid = getgrnam('vyattacfg').gr_gid
            os.chown(wwan['logfile'], uid, gid)

    return None

if __name__ == '__main__':
    try:
        check_kmod()
        c = get_config()
        verify(c)
        generate(c)
        apply(c)
    except ConfigError as e:
        print(e)
        exit(1)
