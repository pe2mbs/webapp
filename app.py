# -*- coding: utf-8 -*-
"""Main webapp application package."""
#
# Main webapp application package
# Copyright (C) 2018-2020 Marc Bertens-Nguyen <m.bertens@pe2mbs.nl>
#
# This library is free software; you can redistribute it and/or modify
# it under the terms of the GNU Library General Public License GPL-2.0-only
# as published by the Free Software Foundation.
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
import sys
import yaml
import logging
import logging.config
import traceback
import importlib
from inspect import signature
from webapp.common.logger import loadLoggingFile, updateLogging
from webapp.extensions.register import registerExtensions
from webapp.common.angular import registerAngular
from webapp.commands.register import registerCommands
from webapp.common.exceptions import InvalidUsage
from webapp.extensions.flask import Flask
import webapp.api as API


def ResolveRootPath( path ):
    if path == '':
        path = os.path.abspath( os.path.join( os.path.dirname( __file__ ), '..' ) )

    elif path == '.':
        path = os.path.abspath( path )

    return path


def loadPlugins():
    # Now check if there are plugins
    pluginsFolder = os.path.abspath( os.path.join(os.path.dirname(__file__), '..', 'plugins') )
    if os.path.isdir( pluginsFolder ):
        for plugin in os.listdir( pluginsFolder ):
            # Found something
            pluginFolder = os.path.join( pluginsFolder, plugin )
            if os.path.isfile( os.path.join( pluginFolder,'__init__.py' ) ) and \
                    os.path.isfile(os.path.join(pluginFolder, '__main__.py') ):
                # It seems to be plugin, import it
                import importlib
                try:
                    API.plugins[ plugin ] = importlib.import_module( pluginFolder )

                except Exception as exc:
                    API.app.logger.error( "Loading plugin {} with error {}".format( pluginFolder, exc ) )

    return


def createApp( root_path, config_file = 'config.yaml', module = None, full_start = True, verbose = False ):
    """An application factory, as explained here:
       http://flask.pocoo.org/docs/patterns/appfactories/.

        :param root_path:   The the root path of the application.
        :param config_file: The configuration file to be used.
        :param module:       The actual application module.

        :return:            The application object.
    """
    API.app = None
    try:
        config_path = root_path = ResolveRootPath( root_path )
        if 'FLASK_APP_CONFIG' in os.environ:
            config_path, config_file = os.path.split( os.environ[ 'FLASK_APP_CONFIG' ] )
            root_path = ResolveRootPath( config_path )

        elif config_file is not None:
            config_path, config_file = os.path.split( config_file )
            if config_path == "":
                config_path = root_path = ResolveRootPath( root_path )

            else:
                root_path = ResolveRootPath( config_path )

        elif os.path.isdir( os.path.join( root_path, 'config' ) ):
            config_path = os.path.join( root_path, 'config' )
            root_path = ResolveRootPath( config_path )
            if not os.path.isfile( os.path.join( config_path, config_file ) ):
                config_file = 'config.json'

        elif os.path.isfile( os.path.join( config_path, config_file ) ):
            pass

        elif os.path.isfile( os.path.join( root_path, 'config.json' ) ):
            config_path = root_path
            config_file = 'config.json'

        if not os.path.isfile( os.path.join( config_path, config_file ) ):
            print( "The config file is missing", file = sys.stderr )
            exit( -1 )

        print( "Starting Flask application, loading configuration." )
        API.app = Flask( __name__.split( '.' )[ 0 ],
                         static_url_path    = "",
                         root_path          = root_path,
                         static_folder      = root_path )

        logDict = {}
        API.app.config.fromFile( os.path.join( config_path, config_file ) )
        # Setup logging for the application
        if 'logging' in API.app.config:
            logDict = API.app.config[ 'logging' ]

        if 'LOGGING' in API.app.config:
            logDict = API.app.config[ 'LOGGING' ]

        if len( logDict ) == 0:
            logDict = loadLoggingFile( root_path,
                                       folder = API.app.config[ 'LOGGING_FOLDER' ] if 'LOGGING_FOLDER' in API.app.config else None,
                                       verbose = verbose )

        else:
            if isinstance( logDict, str ):
                # filename
                logDict = loadLoggingFile( root_path,
                                           logDict,
                                           API.app.config[ 'LOGGING_FOLDER' ] if 'LOGGING_FOLDER' in API.app.config else None,
                                           verbose )

            elif isinstance( logDict, dict ):
                logDict = updateLogging( logDict,
                                         API.app.config[ 'LOGGING_FOLDER' ] if 'LOGGING_FOLDER' in API.app.config else None,
                                         verbose )

            else:
                print( "The logging key in config file is invalid", file = sys.stderr )

        logging.config.dictConfig( logDict )
        API.app.logger.log( API.app.logger.level,
                        "Logging Flask application: %s" % ( logging.getLevelName( API.app.logger.level ) ) )
        API.app.logger.info( "Config file: {}".format( os.path.join( root_path, config_file ) ) )
        API.app.logger.info( "{}".format( yaml.dump( API.app.config.struct, default_flow_style = False ) ) )
        module = None
        sys.path.append( root_path )
        registerExtensions( module )
        registerCommands()
        if full_start:
            loadPlugins()
            API.app.logger.info( "AngularPath : {}".format( API.app.config[ 'ANGULAR_PATH' ] ) )
            API.app.static_folder   = os.path.join( root_path, API.app.config[ 'ANGULAR_PATH' ] ) + "/"
            API.app.url_map.strict_slashes = False
            if module is None and 'API_MODULE' in API.app.config:
                API.app.logger.info("Loading module : {}".format( API.app.config[ 'API_MODULE' ] ) )
                module = importlib.import_module( API.app.config[ 'API_MODULE' ] )

            API.app.logger.info("Application module : {}".format( module ) )
            registerAngular()
            if hasattr( module, 'registerApi' ):
                sig = signature( module.registerApi )
                if len( sig.parameters ) == 2:
                    module.registerApi( API.app, API.db )

                else:
                    module.registerApi()

        def errorhandler( error ):
            response = error.to_json()
            response.status_code = error.status_code
            return response

        API.app.errorhandler( InvalidUsage )( errorhandler )

    except Exception as exc:
        if API.app:
            API.app.logger.error( traceback.format_exc() )

        else:
            print( traceback.format_exc(), file = sys.stderr )

        raise

    return API.app
