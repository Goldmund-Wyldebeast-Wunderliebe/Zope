#!/bin/env python
############################################################################## 
#
#     Copyright 
#
#       Copyright 1998 Digital Creations, Inc., 910 Princess Anne
#       Street, Suite 300, Fredericksburg, Virginia 22401 U.S.A. All
#       rights reserved.
#
############################################################################## 
__doc__='''Principia Factories

$Id: Factory.py,v 1.3 1998/09/08 18:28:39 jim Exp $'''
__version__='$Revision: 1.3 $'[11:-2]

import OFS.SimpleItem, Acquisition, Globals

class Factory(OFS.SimpleItem.Item, Acquisition.Implicit):
    "Model factory meta-data"
    meta_type='Principia Factory'
    icon='p_/Factory_icon'

    manage_options=(
        {'label':'Edit', 'action':'manage_main'},
        {'label':'Security', 'action':'manage_access'},
    )
    
    def __init__(self, id, title, object_type, initial, product):
        self.id=id
        self.title=title
        self.object_type=object_type
        self.initial=initial
        self.__of__(product)._register()

    def manage_edit(self, title, object_type, initial, REQUEST=None):
        "Modify factory properties."
        self._unregister()
        self.title=title
        self.object_type=object_type
        self.initial=initial
        self._register()
        if REQUEST is not None: return self.manage_main(self, REQUEST)

    def _notifyOfCopyTo(self, container, op=0):
        if container.__class__ is not Product:
            raise TypeError, (
                'Factories can only be copied to <b>products</b>.')

    def _postCopy(self, container, op=0):
        self._register()

    def _register(self):
        # Register with the product folder
        product=self.aq_parent
        product.aq_acquire('_manage_add_product_meta_type')(
            product, self.id, self.object_type)

    def _unregister(self):
        # Unregister with the product folder
        product=self.aq_parent
        product.aq_acquire('_manage_remove_product_meta_type')(
            product, self.id, self.object_type)
        

    manage_main=Globals.HTMLFile('editFactory',globals())

    def index_html(self, REQUEST):
        " "
        return getattr(self, self.initial)(self.aq_parent, REQUEST)

############################################################################## 
#
# $Log: Factory.py,v $
# Revision 1.3  1998/09/08 18:28:39  jim
# Added manage_edit.
#
# Revision 1.2  1998/08/14 16:48:52  brian
# Updated copy support in leverish things
#
# Revision 1.1  1998/08/03 13:43:27  jim
# new folderish control panel and product management
#
#
