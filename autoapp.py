# -*- coding: utf-8 -*-
"""Create an application instance for the 'Main Angular application package'."""
#
# Create an application instance for the 'Main Angular application package'
# Copyright (C) 2018 Marc Bertens-Nguyen <m.bertens@pe2mbs.nl>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
import os
from webapp.app import createApp
import webapp.api as API

__version__     = "1.0"
__author__      = 'Marc Bertens-Nguyen'
__copyright__   = 'Copyright (C) 2018 - 2020'

app = createApp( os.path.abspath( os.path.join( os.path.dirname( __file__ ), '..' ) ) )

