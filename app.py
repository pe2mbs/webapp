# -*- coding: utf-8 -*-
"""Angular base module, containing the app factory function.
for the 'Main Angular application package'"""
#
# Angular base module, containing the app factory function.
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
import yaml
import logging
import traceback
import importlib
from applogger import loadLoggingFile, updateLogging
from logging.config import dictConfig
from os.path import join
from angular import registerAngular
import commands
from exceptions import InvalidUsage
import webapp.api as API
import webapp.extensions.flask import Flask


def ResolveRootPath( path ):
    if path == '':
        path = os.path.abspath( os.path.dirname( __file__ ) )

    elif path == '.':
        path = os.path.abspath( path )

    return path


def createApp( root_path, config_file = None, module = None, full_start = True, verbose = False ):
    """An application factory, as explained here:
       http://flask.pocoo.org/docs/patterns/appfactories/.

        :param root_path:   The the root path of the application.
        :param config_file: The configuration file to be used.
        :param module:       The actual application module.

        :return:            The application object.
    """
    API.app = None
    try:
        if config_file is None:
            if 'FLASK_APP_CONFIG' in os.environ:
                config_file = os.environ[ 'FLASK_APP_CONFIG' ]
                root_path, config_file = os.path.split( config_file )
                root_path = ResolveRootPath( root_path )

            else:
                config_file = 'config.yaml'
                root_path = ResolveRootPath( root_path )
                if not os.path.isfile( join( root_path, config_file ) ):
                    config_file = 'config.json'

        if not os.path.isfile( join( root_path, config_file ) ):
            print( "The config file is missing", file = sys.stderr )
            exit( -1 )

        API.app = Flask( __name__.split( '.' )[ 0 ],
                     static_url_path    = "",
                     root_path          = root_path,
                     static_folder      = root_path )
        logDict = {}
        API.app.logger.info( "Starting Flask application, loading configuration." )
        API.app.config.fromFile( join( root_path, config_file ) )

        # Setup logging for the application
        if 'logging' in API.app.config:
            logDict = API.app.config[ 'logging' ]

        if 'LOGGING' in API.app.config:
            logDict = API.app.config[ 'LOGGING' ]

        if len( logDict ) == 0:
            logDict = loadLoggingFile( root_path,
                                       folder = API.app.config[ 'LOGGING_FOLDER' ] if 'LOGGING_FOLDER' in app.config else None,
                                       verbose = verbose )

        else:
            if isinstance( logDict, str ):
                # filename
                logDict = loadLoggingFile( root_path,
                                           logDict,
                                           API.app.config[ 'LOGGING_FOLDER' ] if 'LOGGING_FOLDER' in app.config else None,
                                           verbose )

            elif isinstance( logDict, dict ):
                logDict = updateLogging( logDict,
                                         API.app.config[ 'LOGGING_FOLDER' ] if 'LOGGING_FOLDER' in app.config else None,
                                         verbose )

            else:
                print( "The logging key in config file is invalid", file = sys.stderr )


        dictConfig( logDict )
        #app.logger.setLevel( logging.DEBUG if app.config[ 'DEBUG' ] else logging.ERROR )
        API.app.logger.log( API.app.logger.level,
                        "Logging Flask application: %s" % ( logging.getLevelName( app.logger.level ) ) )
        API.app.logger.info( "{}".format( yaml.dump( app.config, default_flow_style = False ) ) )
        if full_start:
            API.app.logger.info( "AngularPath : {}".format( app.config[ 'ANGULAR_PATH' ] ) )
            API.app.static_folder   = join( root_path, app.config[ 'ANGULAR_PATH' ] ) + "/"
            API.app.url_map.strict_slashes = False
            if module is None and 'API_MODULE' in app.config:
                API.app.logger.info("Loading module : {}".format( app.config[ 'API_MODULE' ] ) )
                module = importlib.import_module( app.config[ 'API_MODULE' ] )

            API.app.logger.info("Application module : {}".format( module ) )

            registerExtensions( API.app, module )
            registerBluePrints( API.app, module )
            registerErrorHandlers( API.app, module )
            registerShellContext( API.app, module )
            registerCommands( API.app, module )

    except Exception as exc:
        if API.app:
            API.app.logger.error( traceback.format_exc() )

        else:
            print( traceback.format_exc(), file = sys.stderr )

        raise

    return API.app


def registerExtensions( module ):
    """Register Flask extensions.

       :param app:          The application object.
       :param module:       The actual application module.
       :return:             None.
    """
    API.app.logger.info( "Registering extensions" )
    API.bcrypt.init_app( API.app )
    API.cache.init_app( API.app )
    API.db.init_app( API.app )
    API.mm.init_app( API.app )
    #migrate.init_app( API.app, API.db )
    API.migrate.init_app( API.app, API.db, render_as_batch = True )
    API.jwt.init_app( API.app )


    # Set the auth callbacks
    if hasattr( module, 'registerJwt' ):
        module.registerJwt( API.app, API.jwt )

    else:
        API.app.logger.info( "Not registering JWT" )

    if hasattr( module, 'registerExtensions' ):
        module.registerExtensions( API.app, API.db )

    return


def registerBluePrints( module ):
    """Register Flask blueprints.

       :param app:          The application object.
       :param module:       The actual application module.
       :return:             None.
    """
    API.app.logger.info( "Registering blueprints" )
    if not API.app.config.get( "ALLOW_CORS_ORIGIN", False ):
        API.app.logger.info( "NOT allowing CORS" )

    registerAngular( API.app, API.cors )
    if not hasattr( module, 'registerApi' ):
        raise Exception( "Missing registerApi() in module {}".format( module ) )

    module.registerApi( API.app, API.cors )
    return


def registerErrorHandlers( module ):
    """Register Flask error handler.

       :param app:          The application object.
       :param module:       The actual application module.
       :return:             None.
    """
    API.app.logger.info( "Registering error handler" )

    if hasattr( module, 'registerErrorHandler' ):
        module.registerErrorHandler( API.app )

    else:
        def errorhandler( error ):
            response = error.to_json()
            response.status_code = error.status_code
            return response

        API.app.errorhandler( InvalidUsage )( errorhandler )

    return


def registerShellContext( app, module ):
    """Register shell context objects.

       :param app:          The application object.
       :param module:       The actual application module.
       :return:             None.
    """
    API.app.logger.info( "Registering SHELL context" )
    if hasattr( module, 'registerShellContext' ):
        module.registerShellContext( API.app, API.db )

    else:
        API.app.shell_context_processor( { 'db': API.db } )

    return


def registerCommands( app, module ):
    """Register Click commands.

       :param app:          The application object.
       :param module:       The actual application module.
       :return:             None.
    """
    API.app.logger.info( "Registering commands" )
    API.app.cli.add_command( commands.test )
    API.app.cli.add_command( commands.lint )
    API.app.cli.add_command( commands.clean )
    API.app.cli.add_command( commands.urls )
    API.app.cli.add_command( commands.runsslCommand )
    API.app.cli.add_command( commands.runProduction )
    if hasattr( module, 'registerCommands' ):
        module.registerCommands( API.app )

    return