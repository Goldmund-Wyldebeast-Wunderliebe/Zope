##############################################################################
#
# Zope Public License (ZPL) Version 0.9.4
# ---------------------------------------
# 
# Copyright (c) Digital Creations.  All rights reserved.
# 
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
# 
# 1. Redistributions in source code must retain the above
#    copyright notice, this list of conditions, and the following
#    disclaimer.
# 
# 2. Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions, and the following
#    disclaimer in the documentation and/or other materials
#    provided with the distribution.
# 
# 3. Any use, including use of the Zope software to operate a
#    website, must either comply with the terms described below
#    under "Attribution" or alternatively secure a separate
#    license from Digital Creations.
# 
# 4. All advertising materials, documentation, or technical papers
#    mentioning features derived from or use of this software must
#    display the following acknowledgement:
# 
#      "This product includes software developed by Digital
#      Creations for use in the Z Object Publishing Environment
#      (http://www.zope.org/)."
# 
# 5. Names associated with Zope or Digital Creations must not be
#    used to endorse or promote products derived from this
#    software without prior written permission from Digital
#    Creations.
# 
# 6. Redistributions of any form whatsoever must retain the
#    following acknowledgment:
# 
#      "This product includes software developed by Digital
#      Creations for use in the Z Object Publishing Environment
#      (http://www.zope.org/)."
# 
# 7. Modifications are encouraged but must be packaged separately
#    as patches to official Zope releases.  Distributions that do
#    not clearly separate the patches from the original work must
#    be clearly labeled as unofficial distributions.
# 
# Disclaimer
# 
#   THIS SOFTWARE IS PROVIDED BY DIGITAL CREATIONS ``AS IS'' AND
#   ANY EXPRESSED OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
#   LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
#   FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.  IN NO EVENT
#   SHALL DIGITAL CREATIONS OR ITS CONTRIBUTORS BE LIABLE FOR ANY
#   DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
#   CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
#   PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
#   DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
#   ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
#   LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING
#   IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF
#   THE POSSIBILITY OF SUCH DAMAGE.
# 
# Attribution
# 
#   Individuals or organizations using this software as a web site
#   must provide attribution by placing the accompanying "button"
#   and a link to the accompanying "credits page" on the website's
#   main entry point.  In cases where this placement of
#   attribution is not feasible, a separate arrangment must be
#   concluded with Digital Creations.  Those using the software
#   for purposes other than web sites must provide a corresponding
#   attribution in locations that include a copyright using a
#   manner best suited to the application environment.
# 
# This software consists of contributions made by Digital
# Creations and many individuals on behalf of Digital Creations.
# Specific attributions are listed in the accompanying credits
# file.
# 
##############################################################################

"""WebDAV xml request objects."""

__version__='$Revision: 1.3 $'[11:-2]

import sys, os, string
from common import absattr, aq_base, urlfix
from xmltools import XmlParser
from cStringIO import StringIO




class PropFind:
    """Model a PROPFIND request."""
    def __init__(self, request):
        self.request=request
        data=request.get('BODY', '')
        self.depth=request.get_header('Depth', 'infinity')
        self.allprop=(not len(data))
        self.propname=0
        self.propnames=[]
        self.parse(data)
        
    def parse(self, data, dav='DAV:'):
        if not data: return
        root=XmlParser().parse(data)
        e=root.elements('propfind', ns=dav)[0]
        if e.elements('allprop', ns=dav):
            self.allprop=1
            return
        if e.elements('propname', ns=dav):
            self.propname=1
            return
        prop=e.elements('prop', ns=dav)[0]
        for val in prop.elements():
            self.propnames.append((val.name(), val.namespace()))
        return

    def apply(self, obj, url=None, depth=0, result=None, top=1):
        if result is None:
            result=StringIO()
            depth=self.depth
            url=urlfix(self.request['URL'], 'PROPFIND')
            result.write('<?xml version="1.0" encoding="utf-8"?>\n' \
                         '<d:multistatus xmlns:d="DAV:">\n')
        iscol=hasattr(obj, '__dav_collection__')
        if iscol and url[-1] != '/': url=url+'/'
        result.write('<d:response>\n<d:href>%s</d:href>\n' % url)
        if hasattr(obj, '__propsets__'):
            for ps in obj.propertysheets.values():
                if hasattr(aq_base(ps), 'dav__propstat'):
                    stat=ps.dav__propstat(self.allprop, self.propnames)
                    result.write(stat)
        result.write('</d:response>\n')
        if depth in ('1', 'infinity') and iscol:
            for ob in obj.objectValues():
                dflag=hasattr(ob, '_p_changed') and (ob._p_changed == None)
                if hasattr(ob, '__dav_resource__'):
                    uri=os.path.join(url, absattr(ob.id))
                    depth=depth=='infinity' and depth or 0
                    self.apply(ob, uri, depth, result, top=0)
                    if dflag: ob._p_deactivate()
        if not top: return result
        result.write('</d:multistatus>')
        return result.getvalue()


class PropPatch:
    """Model a PROPPATCH request."""
    def __init__(self, request):
        self.request=request
        data=request.get('BODY', '')
        self.values=[]
        self.parse(data)

    def parse(self, data, dav='DAV:'):
        root=XmlParser().parse(data)
        e=root.elements('propertyupdate', ns=dav)[0]
        for ob in e.elements():
            if ob.name()=='set' and ob.namespace()==dav:
                prop=ob.elements('prop', ns=dav)[0]
                for val in prop.elements():
                    # We have to ensure that all tag attrs (including
                    # an xmlns attr for all xml namespaces used by the
                    # element and its children) are saved, per rfc2518.
                    attrs={}
                    val.remap({})
                    for attr in val.attrs():
                        md[attr.name()]=attr.value()
                    md={'attrs':attrs, 'nsid': val.__nskey__}
                    item=(val.name(), val.namespace(), val.strval(), md)
                    self.values.append(item)
            if ob.name()=='remove' and ob.namespace()==dav:
                prop=ob.elements('prop', ns=dav)[0]
                for val in prop.elements():
                    item=(val.name(), val.namespace())
                    self.values.append(item)

    def apply(self, obj):
        url=urlfix(self.request['URL'], 'PROPPATCH')
        if hasattr(obj, '__dav_collection__'):
            url=url+'/'
        result=StringIO()
        errors=[]
        result.write('<?xml version="1.0" encoding="utf-8"?>\n' \
                     '<d:multistatus xmlns:d="DAV:">\n' \
                     '<d:response>\n' \
                     '<d:href>%s</d:href>\n' % url)
        propsets=obj.propertysheets
        for value in self.values:
            status='200 OK'
            if len(value) > 2:
                name, ns, val, md=value
                propset=propsets.get(ns, None)
                if propset is None:
                    obj.propertysheets.manage_addPropertySheet('', ns)
                    propsets=obj.propertysheets.values()
                    propset=propsets.get(ns)
                if propset.hasProperty(name):
                    try: propset._updateProperty(name, val, meta=md)
                    except:
                        errors.append(str(sys.exc_value))
                        status='409 Conflict'
                else:
                    try: propset._setProperty(name, val, meta=md)
                    except:
                        errors.append(str(sys.exc_value))
                        status='409 Conflict'
            else:
                name, ns=value
                propset=propsets.get(ns, None)
                if propset is None or not propset.hasProperty(name):
                    errors.append('Property not found: %s' % name)
                    status='404 Not Found'
                else:
                    try: propset._delProperty(name)
                    except:
                        errors.append('%s cannot be deleted.' % name)
                        status='409 Conflict'
            if result != '200 OK': abort=1
            result.write('<d:propstat xmlns:n="%s">\n' \
                         '  <d:prop>\n' \
                         '  <n:%s/>\n' \
                         '  </d:prop>\n' \
                         '  <d:status>HTTP/1.1 %s</d:status>\n' \
                         '</d:propstat>\n' % (ns, name, status))
        errmsg=string.join(errors, '\n') or 'The operation succeded.'
        result.write('<d:responsedescription>\n' \
                     '%s\n' \
                     '</d:responsedescription>\n' \
                     '</d:response>\n' \
                     '</d:multistatus>' % errmsg)
        result=result.getvalue()
        if not errors: return result
        get_transaction().abort()
        result=string.replace(result, '200 OK', '424 Failed Dependency')
        return result




class Lock:
    """Model a LOCK request."""
    def __init__(self, request):
        self.request=request
        data=request.get('BODY', '')
        self.scope='exclusive'
        self.type='write'
        self.owner=''
        self.parse(data)

    def parse(self, data, dav='DAV:'):
        root=XmlParser().parse(data)
        info=root.elements('lockinfo', ns=dav)[0]
        ls=info.elements('lockscope', ns=dav)[0]
        self.scope=ls.elements()[0].name()
        lt=info.elements('locktype', ns=dav)[0]
        self.type=lt.elements()[0].name()
        lo=info.elements('owner', ns=dav)
        if lo: self.owner=lo[0].toxml()
