##############################################################################
# 
# Zope Public License (ZPL) Version 1.0
# -------------------------------------
# 
# Copyright (c) Digital Creations.  All rights reserved.
# 
# This license has been certified as Open Source(tm).
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
# 
# 1. Redistributions in source code must retain the above copyright
#    notice, this list of conditions, and the following disclaimer.
# 
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions, and the following disclaimer in
#    the documentation and/or other materials provided with the
#    distribution.
# 
# 3. Digital Creations requests that attribution be given to Zope
#    in any manner possible. Zope includes a "Powered by Zope"
#    button that is installed by default. While it is not a license
#    violation to remove this button, it is requested that the
#    attribution remain. A significant investment has been put
#    into Zope, and this effort will continue if the Zope community
#    continues to grow. This is one way to assure that growth.
# 
# 4. All advertising materials and documentation mentioning
#    features derived from or use of this software must display
#    the following acknowledgement:
# 
#      "This product includes software developed by Digital Creations
#      for use in the Z Object Publishing Environment
#      (http://www.zope.org/)."
# 
#    In the event that the product being advertised includes an
#    intact Zope distribution (with copyright and license included)
#    then this clause is waived.
# 
# 5. Names associated with Zope or Digital Creations must not be used to
#    endorse or promote products derived from this software without
#    prior written permission from Digital Creations.
# 
# 6. Modified redistributions of any form whatsoever must retain
#    the following acknowledgment:
# 
#      "This product includes software developed by Digital Creations
#      for use in the Z Object Publishing Environment
#      (http://www.zope.org/)."
# 
#    Intact (re-)distributions of any official Zope release do not
#    require an external acknowledgement.
# 
# 7. Modifications are encouraged but must be packaged separately as
#    patches to official Zope releases.  Distributions that do not
#    clearly separate the patches from the original work must be clearly
#    labeled as unofficial distributions.  Modifications which do not
#    carry the name Zope may be packaged in any form, as long as they
#    conform to all of the clauses above.
# 
# 
# Disclaimer
# 
#   THIS SOFTWARE IS PROVIDED BY DIGITAL CREATIONS ``AS IS'' AND ANY
#   EXPRESSED OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
#   IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
#   PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL DIGITAL CREATIONS OR ITS
#   CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
#   SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
#   LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
#   USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
#   ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
#   OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
#   OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
#   SUCH DAMAGE.
# 
# 
# This software consists of contributions made by Digital Creations and
# many individuals on behalf of Digital Creations.  Specific
# attributions are listed in the accompanying credits file.
# 
##############################################################################

"""
Medusa HTTP server for Zope

changes from Medusa's http_server

    Request Threads -- Requests are processed by threads from a thread
    pool.
    
    Output Handling -- Output is pushed directly into the producer
    fifo by the request-handling thread. The HTTP server does not do
    any post-processing such as chunking.

    Pipelineable -- This is needed for protocols such as HTTP/1.1 in
    which mutiple requests come in on the same channel, before
    responses are sent back. When requests are pipelined, the client
    doesn't wait for the response before sending another request. The
    server must ensure that responses are sent back in the same order
    as requests are received.
    
""" 
import sys
import regex
import string
import os
import types
import thread
import time
from cStringIO import StringIO

from PubCore import handle
from HTTPResponse import make_response
from ZPublisher.HTTPRequest import HTTPRequest

from medusa.http_server import http_server, http_channel
from medusa import counter, producers, asyncore, max_sockets
from medusa.default_handler import split_path, unquote, get_header

from ZServer import CONNECTION_LIMIT, ZOPE_VERSION, ZSERVER_VERSION

from zLOG import LOG, register_subsystem, BLATHER, INFO, WARNING, ERROR
import DebugLogger

register_subsystem('ZServer HTTPServer')

CONTENT_LENGTH = regex.compile('Content-Length: \([0-9]+\)',regex.casefold)
CONNECTION = regex.compile ('Connection: \(.*\)', regex.casefold)

# maps request some headers to environment variables.
# (those that don't start with 'HTTP_')
header2env={'content-length'    : 'CONTENT_LENGTH',
            'content-type'      : 'CONTENT_TYPE',
            'connection'        : 'CONNECTION_TYPE',
            }


class zhttp_handler:
    "A medusa style handler for zhttp_server"
        
    def __init__ (self, module, uri_base=None, env=None):
        """Creates a zope_handler
        
        module -- string, the name of the module to publish
        uri_base -- string, the base uri of the published module
                    defaults to '/<module name>' if not given.
        env -- dictionary, environment variables to be overridden.        
                    Replaces standard variables with supplied ones.
        """
        
        self.module_name=module
        self.env_override=env or {}
        self.hits = counter.counter()
        # if uri_base is unspecified, assume it
        # starts with the published module name
        #
        if uri_base is None:
            uri_base='/%s' % module
        elif uri_base == '':
            uri_base='/'
        else:
            if uri_base[0] != '/':
              uri_base='/'+uri_base
            if uri_base[-1] == '/':
              uri_base=uri_base[:-1]
        self.uri_base=uri_base
        uri_regex='%s.*' % self.uri_base
        self.uri_regex = regex.compile(uri_regex)

    def match(self, request):
        uri = request.uri
        if self.uri_regex.match(uri) == len(uri):
            return 1
        else:
            return 0

    def handle_request(self,request):
        self.hits.increment()

        DebugLogger.log('B', id(request), '%s %s' % (string.upper(request.command), request.uri))

        size=get_header(CONTENT_LENGTH, request.header)
        if size and size != '0':
            size=string.atoi(size)
            if size > 524288:
                # write large upload data to a file
                from tempfile import TemporaryFile
                self.data = TemporaryFile('w+b')
            else:
                self.data = StringIO()
            self.request = request
            request.channel.set_terminator(size)
            request.collector=self
        else:
            sin=StringIO()
            self.continue_request(sin,request)

    def get_environment(self, request,
                        # These are strictly performance hackery...
                        split=string.split,
                        strip=string.strip,
                        join =string.join,
                        upper=string.upper,
                        lower=string.lower,
                        h2ehas=header2env.has_key,
                        h2eget=header2env.get,
                        workdir=os.getcwd(),
                        ospath=os.path,
                        ):
        [path, params, query, fragment] = split_path(request.uri)
        while path and path[0] == '/':
            path = path[1:]
        if '%' in path:
            path = unquote(path)
        if query:
            # ZPublisher doesn't want the leading '?'
            query = query[1:]

        server=request.channel.server
        env = {}
        env['REQUEST_METHOD']=upper(request.command)
        env['SERVER_PORT']=str(server.port)
        env['SERVER_NAME']=server.server_name
        env['SERVER_SOFTWARE']=server.SERVER_IDENT
        env['SERVER_PROTOCOL']=request.version
        env['channel.creation_time']=request.channel.creation_time
        if self.uri_base=='/':
            env['SCRIPT_NAME']=''
            env['PATH_INFO']='/' + path
        else:
            env['SCRIPT_NAME'] = self.uri_base
            try:
                path_info=split(path,self.uri_base[1:],1)[1]
            except:
                path_info=''
            env['PATH_INFO']=path_info
        env['PATH_TRANSLATED']=ospath.normpath(ospath.join(
                workdir, env['PATH_INFO']))
        if query:
            env['QUERY_STRING'] = query
        env['GATEWAY_INTERFACE']='CGI/1.1'
        env['REMOTE_ADDR']=request.channel.addr[0]

        # If we're using a resolving logger, try to get the
        # remote host from the resolver's cache.
        if hasattr(server.logger, 'resolver'):
            dns_cache=server.logger.resolver.cache
            if dns_cache.has_key(env['REMOTE_ADDR']):
                remote_host=dns_cache[env['REMOTE_ADDR']][2]
                if remote_host is not None:
                    env['REMOTE_HOST']=remote_host

        env_has=env.has_key
        for header in request.header:
            key,value=split(header,":",1)
            key=lower(key)
            value=strip(value)
            if h2ehas(key) and value:
                env[h2eget(key)]=value
            else:
                key='HTTP_%s' % upper(join(split(key, "-"), "_"))
                if value and not env_has(key):
                    env[key]=value
        env.update(self.env_override)
        return env

    def continue_request(self, sin, request):
        "continue handling request now that we have the stdin"
       
        s=get_header(CONTENT_LENGTH, request.header)
        if s:
            s=string.atoi(s)
        else:
            s=0    
        DebugLogger.log('I', id(request), s)

        env=self.get_environment(request)
        zresponse=make_response(request,env)
        zrequest=HTTPRequest(sin, env, zresponse)
        request.channel.current_request=None
        request.channel.queue.append(self.module_name, zrequest, zresponse)
        request.channel.work()

    def status(self):
        return producers.simple_producer("""
            <li>Zope Handler
            <ul>
            <li><b>Published Module:</b> % s
            <li><b>Hits:</b> %d
            </ul>""" %(self.module_name,int(self.hits))
            )

    # put and post collection methods
    #
    def collect_incoming_data (self, data):
        self.data.write(data)

    def found_terminator(self):
        # reset collector
        self.request.channel.set_terminator('\r\n\r\n')
        self.request.collector=None
        # finish request
        self.data.seek(0)
        r=self.request
        d=self.data
        del self.request
        del self.data
        self.continue_request(d,r)


class zhttp_channel(http_channel):
    "http channel"
    
    def __init__(self, server, conn, addr):
        http_channel.__init__(self, server, conn, addr)
        self.queue=[]
        self.working=0
    
    def push(self, producer, send=1):
        # this is thread-safe when send is false
        # note, that strings are not wrapped in 
        # producers by default
        self.producer_fifo.push(producer)
        if send: self.initiate_send()
        
    push_with_producer=push

    def work(self):
        "try to handle a request"
        if not self.working:
            if self.queue:
                self.working=1
                try: module_name, request, response=self.queue.pop(0)
                except: return
                handle(module_name, request, response)
        
    def done(self):
        "Called when a publishing request is finished"
        self.working=0
        self.work()

    def kill_zombies(self):
        now = int (time.time())
        for channel in asyncore.socket_map.keys():
            if channel.__class__ == self.__class__:
                if (now - channel.creation_time) > channel.zombie_timeout:
                    channel.close()


class zhttp_server(http_server):    
    "http server"
    
    SERVER_IDENT='Zope/%s ZServer/%s' % (ZOPE_VERSION,ZSERVER_VERSION)
    
    channel_class = zhttp_channel

    def readable(self):
        return self.accepting and \
                len(asyncore.socket_map) < CONNECTION_LIMIT

    def listen(self, num):
        # override asyncore limits for nt's listen queue size
        self.accepting = 1
        return self.socket.listen (num)

