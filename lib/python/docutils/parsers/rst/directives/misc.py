# Authors: David Goodger, Dethe Elza
# Contact: goodger@users.sourceforge.net
# Revision: $Revision: 1.2.10.3.8.1 $
# Date: $Date: 2004/05/12 19:57:48 $
# Copyright: This module has been placed in the public domain.

"""Miscellaneous directives."""

__docformat__ = 'reStructuredText'

import sys
import os.path
import re
from docutils import io, nodes, statemachine, utils
from docutils.parsers.rst import directives, roles, states
from docutils.transforms import misc

try:
    import urllib2
except ImportError:
    urllib2 = None


def include(name, arguments, options, content, lineno,
            content_offset, block_text, state, state_machine):
    """Include a reST file as part of the content of this reST file."""
    source = state_machine.input_lines.source(
        lineno - state_machine.input_offset - 1)
    source_dir = os.path.dirname(os.path.abspath(source))
    path = ''.join(arguments[0].splitlines())
    if path.find(' ') != -1:
        error = state_machine.reporter.error(
              '"%s" directive path contains whitespace.' % name,
              nodes.literal_block(block_text, block_text), line=lineno)
        return [error]
    path = os.path.normpath(os.path.join(source_dir, path))
    path = utils.relative_path(None, path)
    try:
        include_file = io.FileInput(
            source_path=path, encoding=state.document.settings.input_encoding,
            handle_io_errors=None)
    except IOError, error:
        severe = state_machine.reporter.severe(
              'Problems with "%s" directive path:\n%s: %s.'
              % (name, error.__class__.__name__, error),
              nodes.literal_block(block_text, block_text), line=lineno)
        return [severe]
    include_text = include_file.read()
    if options.has_key('literal'):
        literal_block = nodes.literal_block(include_text, include_text,
                                            source=path)
        literal_block.line = 1
        return literal_block
    else:
        include_lines = statemachine.string2lines(include_text,
                                                  convert_whitespace=1)
        state_machine.insert_input(include_lines, path)
        return []

include.arguments = (1, 0, 1)
include.options = {'literal': directives.flag}

def raw(name, arguments, options, content, lineno,
        content_offset, block_text, state, state_machine):
    """
    Pass through content unchanged

    Content is included in output based on type argument

    Content may be included inline (content section of directive) or
    imported from a file or url.
    """
    attributes = {'format': arguments[0]}
    if content:
        if options.has_key('file') or options.has_key('url'):
            error = state_machine.reporter.error(
                  '"%s" directive may not both specify an external file and '
                  'have content.' % name,
                  nodes.literal_block(block_text, block_text), line=lineno)
            return [error]
        text = '\n'.join(content)
    elif options.has_key('file'):
        if options.has_key('url'):
            error = state_machine.reporter.error(
                  'The "file" and "url" options may not be simultaneously '
                  'specified for the "%s" directive.' % name,
                  nodes.literal_block(block_text, block_text), line=lineno)
            return [error]
        source_dir = os.path.dirname(
            os.path.abspath(state.document.current_source))
        path = os.path.normpath(os.path.join(source_dir, options['file']))
        path = utils.relative_path(None, path)
        try:
            raw_file = open(path)
        except IOError, error:
            severe = state_machine.reporter.severe(
                  'Problems with "%s" directive path:\n%s.' % (name, error),
                  nodes.literal_block(block_text, block_text), line=lineno)
            return [severe]
        text = raw_file.read()
        raw_file.close()
        attributes['source'] = path
    elif options.has_key('url'):
        if not urllib2:
            severe = state_machine.reporter.severe(
                  'Problems with the "%s" directive and its "url" option: '
                  'unable to access the required functionality (from the '
                  '"urllib2" module).' % name,
                  nodes.literal_block(block_text, block_text), line=lineno)
            return [severe]
        try:
            raw_file = urllib2.urlopen(options['url'])
        except (urllib2.URLError, IOError, OSError), error:
            severe = state_machine.reporter.severe(
                  'Problems with "%s" directive URL "%s":\n%s.'
                  % (name, options['url'], error),
                  nodes.literal_block(block_text, block_text), line=lineno)
            return [severe]
        text = raw_file.read()
        raw_file.close()
        attributes['source'] = options['file']
    else:
        error = state_machine.reporter.warning(
            'The "%s" directive requires content; none supplied.' % (name),
            nodes.literal_block(block_text, block_text), line=lineno)
        return [error]
    raw_node = nodes.raw('', text, **attributes)
    return [raw_node]

raw.arguments = (1, 0, 1)
raw.options = {'file': directives.path,
               'url': directives.path}
raw.content = 1

def replace(name, arguments, options, content, lineno,
            content_offset, block_text, state, state_machine):
    if not isinstance(state, states.SubstitutionDef):
        error = state_machine.reporter.error(
            'Invalid context: the "%s" directive can only be used within a '
            'substitution definition.' % (name),
            nodes.literal_block(block_text, block_text), line=lineno)
        return [error]
    text = '\n'.join(content)
    element = nodes.Element(text)
    if text:
        state.nested_parse(content, content_offset, element)
        if len(element) != 1 or not isinstance(element[0], nodes.paragraph):
            messages = []
            for node in element:
                if isinstance(node, nodes.system_message):
                    if node.has_key('backrefs'):
                        del node['backrefs']
                    messages.append(node)
            error = state_machine.reporter.error(
                'Error in "%s" directive: may contain a single paragraph '
                'only.' % (name), line=lineno)
            messages.append(error)
            return messages
        else:
            return element[0].children
    else:
        error = state_machine.reporter.error(
            'The "%s" directive is empty; content required.' % (name),
            line=lineno)
        return [error]

replace.content = 1

def unicode_directive(name, arguments, options, content, lineno,
                         content_offset, block_text, state, state_machine):
    r"""
    Convert Unicode character codes (numbers) to characters.  Codes may be
    decimal numbers, hexadecimal numbers (prefixed by ``0x``, ``x``, ``\x``,
    ``U+``, ``u``, or ``\u``; e.g. ``U+262E``), or XML-style numeric character
    entities (e.g. ``&#x262E;``).  Text following ".." is a comment and is
    ignored.  Spaces are ignored, and any other text remains as-is.
    """
    if not isinstance(state, states.SubstitutionDef):
        error = state_machine.reporter.error(
            'Invalid context: the "%s" directive can only be used within a '
            'substitution definition.' % (name),
            nodes.literal_block(block_text, block_text), line=lineno)
        return [error]
    codes = unicode_comment_pattern.split(arguments[0])[0].split()
    element = nodes.Element()
    for code in codes:
        try:
            decoded = directives.unicode_code(code)
        except ValueError, err:
            error = state_machine.reporter.error(
                'Invalid character code: %s\n%s: %s'
                % (code, err.__class__.__name__, err),
                nodes.literal_block(block_text, block_text), line=lineno)
            return [error]
        element += nodes.Text(decoded)
    return element.children

unicode_directive.arguments = (1, 0, 1)
unicode_comment_pattern = re.compile(r'( |\n|^).. ')

def class_directive(name, arguments, options, content, lineno,
                       content_offset, block_text, state, state_machine):
    """"""
    class_value = nodes.make_id(arguments[0])
    if class_value:
        pending = nodes.pending(misc.ClassAttribute,
                                {'class': class_value, 'directive': name},
                                block_text)
        state_machine.document.note_pending(pending)
        return [pending]
    else:
        error = state_machine.reporter.error(
            'Invalid class attribute value for "%s" directive: "%s".'
            % (name, arguments[0]),
            nodes.literal_block(block_text, block_text), line=lineno)
        return [error]

class_directive.arguments = (1, 0, 0)
class_directive.content = 1

role_arg_pat = re.compile(r'(%s)\s*(\(\s*(%s)\s*\)\s*)?$'
                          % ((states.Inliner.simplename,) * 2))
def role(name, arguments, options, content, lineno,
         content_offset, block_text, state, state_machine):
    """Dynamically create and register a custom interpreted text role."""
    if content_offset > lineno or not content:
        error = state_machine.reporter.error(
            '"%s" directive requires arguments on the first line.'
            % name, nodes.literal_block(block_text, block_text), line=lineno)
        return [error]
    args = content[0]
    match = role_arg_pat.match(args)
    if not match:
        error = state_machine.reporter.error(
            '"%s" directive arguments not valid role names: "%s".'
            % (name, args), nodes.literal_block(block_text, block_text),
            line=lineno)
        return [error]
    new_role_name = match.group(1)
    base_role_name = match.group(3)
    messages = []
    if base_role_name:
        base_role, messages = roles.role(
            base_role_name, state_machine.language, lineno, state.reporter)
        if base_role is None:
            error = state.reporter.error(
                'Unknown interpreted text role "%s".' % base_role_name,
                nodes.literal_block(block_text, block_text), line=lineno)
            return messages + [error]
    else:
        base_role = roles.generic_custom_role
    assert not hasattr(base_role, 'arguments'), (
        'Supplemental directive arguments for "%s" directive not supported'
        '(specified by "%r" role).' % (name, base_role))
    try:
        (arguments, options, content, content_offset) = (
            state.parse_directive_block(content[1:], content_offset, base_role,
                                        option_presets={}))
    except states.MarkupError, detail:
        error = state_machine.reporter.error(
            'Error in "%s" directive:\n%s.' % (name, detail),
            nodes.literal_block(block_text, block_text), line=lineno)
        return messages + [error]
    if not options.has_key('class'):
        try:
            options['class'] = directives.class_option(new_role_name)
        except ValueError, detail:
            error = state_machine.reporter.error(
                'Invalid argument for "%s" directive:\n%s.'
                % (name, detail),
                nodes.literal_block(block_text, block_text), line=lineno)
            return messages + [error]
    role = roles.CustomRole(new_role_name, base_role, options, content)
    roles.register_local_role(new_role_name, role)
    return messages

role.content = 1

def directive_test_function(name, arguments, options, content, lineno,
                            content_offset, block_text, state, state_machine):
    """This directive is useful only for testing purposes."""
    if content:
        text = '\n'.join(content)
        info = state_machine.reporter.info(
            'Directive processed. Type="%s", arguments=%r, options=%r, '
            'content:' % (name, arguments, options),
            nodes.literal_block(text, text), line=lineno)
    else:
        info = state_machine.reporter.info(
            'Directive processed. Type="%s", arguments=%r, options=%r, '
            'content: None' % (name, arguments, options), line=lineno)
    return [info]

directive_test_function.arguments = (0, 1, 1)
directive_test_function.options = {'option': directives.unchanged_required}
directive_test_function.content = 1
