# Authors: David Goodger
# Contact: goodger@users.sourceforge.net
# Revision: $Revision: 2223 $
# Date: $Date: 2004-06-05 21:32:15 +0200 (Sat, 05 Jun 2004) $
# Copyright: This module has been placed in the public domain.

"""
Simple internal document tree Writer, writes Docutils XML.
"""

__docformat__ = 'reStructuredText'


import docutils
from docutils import frontend, writers


class Writer(writers.Writer):

    supported = ('xml',)
    """Formats this writer supports."""

    settings_spec = (
        '"Docutils XML" Writer Options',
        'Warning: the --newlines and --indents options may adversely affect '
        'whitespace; use them only for reading convenience.',
        (('Generate XML with newlines before and after tags.',
          ['--newlines'],
          {'action': 'store_true', 'validator': frontend.validate_boolean}),
         ('Generate XML with indents and newlines.',
          ['--indents'],
          {'action': 'store_true', 'validator': frontend.validate_boolean}),
         ('Omit the XML declaration.  Use with caution.',
          ['--no-xml-declaration'],
          {'dest': 'xml_declaration', 'default': 1, 'action': 'store_false',
           'validator': frontend.validate_boolean}),
         ('Omit the DOCTYPE declaration.',
          ['--no-doctype'],
          {'dest': 'doctype_declaration', 'default': 1,
           'action': 'store_false', 'validator': frontend.validate_boolean}),))

    config_section = 'docutils_xml writer'
    config_section_dependencies = ('writers',)

    output = None
    """Final translated form of `document`."""

    xml_declaration = '<?xml version="1.0" encoding="%s"?>\n'
    #xml_stylesheet = '<?xml-stylesheet type="text/xsl" href="%s"?>\n'
    doctype = (
        '<!DOCTYPE document PUBLIC'
        ' "+//IDN docutils.sourceforge.net//DTD Docutils Generic//EN//XML"'
        ' "http://docutils.sourceforge.net/docs/ref/docutils.dtd">\n')
    generator = '<!-- Generated by Docutils %s -->\n'

    def translate(self):
        settings = self.document.settings
        indent = newline = ''
        if settings.newlines:
            newline = '\n'
        if settings.indents:
            newline = '\n'
            indent = '    '
        output_prefix = []
        if settings.xml_declaration:
            output_prefix.append(
                self.xml_declaration % settings.output_encoding)
        if settings.doctype_declaration:
            output_prefix.append(self.doctype)
        output_prefix.append(self.generator % docutils.__version__)
        docnode = self.document.asdom().childNodes[0]
        self.output = (''.join(output_prefix)
                       + docnode.toprettyxml(indent, newline))
