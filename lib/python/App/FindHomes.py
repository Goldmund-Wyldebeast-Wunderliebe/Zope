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

"""Commonly used utility functions."""

__version__='$Revision: 1.4 $'[11:-2]

import os, sys, Products, string
from Common import package_home
path_join = os.path.join
path_split = os.path.split

try: home=os.environ['SOFTWARE_HOME']
except:
    home=package_home(Products.__dict__)
    if not os.path.isabs(home):
        home=path_join(os.getcwd(), home)
        
    home,e=path_split(home)
    if path_split(home)[1]=='.': home=path_split(home)[0]
    if path_split(home)[1]=='..':
        home=path_split(path_split(home)[0])[0]

sys.modules['__builtin__'].SOFTWARE_HOME=SOFTWARE_HOME=home

try: chome=os.environ['INSTANCE_HOME']
except:
    chome=home
    d,e=path_split(chome)
    if e=='python':
        d,e=path_split(d)
        if e=='lib': chome=d or os.getcwd()
    
sys.modules['__builtin__'].INSTANCE_HOME=INSTANCE_HOME=chome

# If there is a Products package in INSTANCE_HOME, add it to the
# Products package path
ip=path_join(INSTANCE_HOME, 'Products')
ippart = 0
ppath = Products.__path__
if os.path.isdir(ip) and ip not in ppath:
    disallow=string.lower(os.environ.get('DISALLOW_LOCAL_PRODUCTS',''))
    if disallow in ('no', 'off', '0', ''):
        ppath.insert(0, ip)
        ippart = 1
        
ppathpat = os.environ.get('PRODUCTS_PATH', None)
if ppathpat is not None:
    psep = os.pathsep
    if string.find(ppathpat, '%(') >= 0:
        newppath = string.split(ppathpat % {
            'PRODUCTS_PATH': string.join(ppath, psep),
            'SOFTWARE_PRODUCTS': string.join(ppath[ippart:], psep),
            'INSTANCE_PRODUCTS': ip,
            }, psep)
    else:
        newppath = string.split(ppathpat, psep)
    del ppath[:]
    for p in filter(None, newppath):
        p = os.path.abspath(p)
        if os.path.isdir(p) and p not in ppath:
            ppath.append(p)
