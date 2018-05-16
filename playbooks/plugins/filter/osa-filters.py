#!/usr/bin/env python
# Copyright 2015, Rackspace US, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# (c) 2015, Kevin Carter <kevin.carter@rackspace.com>

import hashlib
import logging
import os
import re
import urlparse

from ansible import errors
from jinja2.runtime import Undefined

"""Filter usage:

Simple filters that may be useful from within the stack
"""


def _deprecated(new_var, old_var=None, old_var_name=None,
                new_var_name=None, removed_in=None, fatal=False):
    """Provide a deprecation warning on deprecated variables.

    This filter will return the old_var value if defined along with a
    deprecation warning that will inform the user that the old variable
    should no longer be used.

    In order to use this filter the old and new variable names must be provided
    to the filter as a string which is used to render the warning message. The
    removed_in option is used to give a date or release name where the old
    option will be removed. Optionally, if fatal is set to True, the filter
    will raise an exception if the old variable is used.

    USAGE: {{ new_var | deprecated(old_var,
                                   "old_var_name",
                                   "new_var_name",
                                   "removed_in",
                                   false) }}

    :param new_var: ``object``
    :param old_var: ``object``
    :param old_var_name: ``str``
    :param new_var_name: ``str``
    :param removed_in: ``str``
    :param fatal: ``bol``
    """
    _usage = (
        'USAGE: '
        '{{ new_var | deprecated(old_var=old_var, old_var_name="old_var_name",'
        ' new_var_name="new_var_name", removed_in="removed_in",'
        ' fatal=false) }}'
    )

    if not old_var_name:
        raise errors.AnsibleUndefinedVariable(
            'To use this filter you must provide the "old_var_name" option'
            ' with the string name of the old variable that will be'
            ' replaced. ' + _usage
        )
    if not new_var_name:
        raise errors.AnsibleUndefinedVariable(
            'To use this filter you must provide the "new_var_name" option'
            ' with the string name of the new variable that will replace the'
            ' deprecated one. ' + _usage
        )
    if not removed_in:
        raise errors.AnsibleUndefinedVariable(
            'To use this filter you must provide the "removed_in" option with'
            ' the string name of the release where the old_var will be'
            ' removed. ' + _usage
        )

    # If old_var is undefined or has a None value return the new_var value
    if isinstance(old_var, Undefined) or not old_var:
        return new_var

    name = 'Ansible-Warning| '
    log = logging.getLogger(name)
    for handler in log.handlers:
        if name == handler.name:
            break
    else:
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.DEBUG)
        stream_handler.name = name
        stream_format = logging.Formatter(
            '%(asctime)s - %(name)s%(levelname)s => %(message)s'
        )
        stream_handler.setFormatter(stream_format)

        log.setLevel(logging.DEBUG)
        log.addHandler(stream_handler)

    message = (
        'Deprecated Option provided: Deprecated variable: "%(old)s", Removal'
        ' timeframe: "%(removed_in)s", Future usage: "%(new)s"'
        % {'old': old_var_name, 'new': new_var_name, 'removed_in': removed_in}
    )

    if str(fatal).lower() in ['yes', 'true']:
        message = 'Fatally %s' % message
        log.fatal(message)
        raise RuntimeError(message)
    else:
        log.warn(message)
        return old_var


def _pip_requirement_split(requirement):
    version_descriptors = "(>=|<=|>|<|==|~=|!=)"
    requirement = requirement.split(';')
    requirement_info = re.split(r'%s\s*' % version_descriptors, requirement[0])
    name = requirement_info[0]
    marker = None
    if len(requirement) > 1:
        marker = requirement[1]
    versions = None
    if len(requirement_info) > 1:
        versions = requirement_info[1]

    return name, versions, marker


def _lower_set_lists(list_one, list_two):

    _list_one = set([i.lower() for i in list_one])
    _list_two = set([i.lower() for i in list_two])
    return _list_one, _list_two


def bit_length_power_of_2(value):
    """Return the smallest power of 2 greater than a numeric value.

    :param value: Number to find the smallest power of 2
    :type value: ``int``
    :returns: ``int``
    """
    return 2**(int(value)-1).bit_length()


def get_netloc(url):
    """Return the netloc from a URL.

    If the input value is not a value URL the method will raise an Ansible
    filter exception.

    :param url: the URL to parse
    :type url: ``str``
    :returns: ``str``
    """
    try:
        netloc = urlparse.urlparse(url).netloc
    except Exception as exp:
        raise errors.AnsibleFilterError(
            'Failed to return the netloc of: "%s"' % str(exp)
        )
    else:
        return netloc


def get_netloc_no_port(url):
    """Return the netloc without a port from a URL.

    If the input value is not a value URL the method will raise an Ansible
    filter exception.

    :param url: the URL to parse
    :type url: ``str``
    :returns: ``str``
    """
    return get_netloc(url=url).split(':')[0]


def get_netorigin(url):
    """Return the netloc from a URL.

    If the input value is not a value URL the method will raise an Ansible
    filter exception.

    :param url: the URL to parse
    :type url: ``str``
    :returns: ``str``
    """
    try:
        parsed_url = urlparse.urlparse(url)
        netloc = parsed_url.netloc
        scheme = parsed_url.scheme
    except Exception as exp:
        raise errors.AnsibleFilterError(
            'Failed to return the netorigin of: "%s"' % str(exp)
        )
    else:
        return '%s://%s' % (scheme, netloc)


def string_2_int(string):
    """Return the an integer from a string.

    The string is hashed, converted to a base36 int, and the modulo of 10240
    is returned.

    :param string: string to retrieve an int from
    :type string: ``str``
    :returns: ``int``
    """
    # Try to encode utf-8 else pass
    try:
        string = string.encode('utf-8')
    except AttributeError:
        pass
    hashed_name = hashlib.sha256(string).hexdigest()
    return int(hashed_name, 36) % 10240


def pip_requirement_names(requirements):
    """Return a ``str`` of requirement name and list of versions.
    :param requirement: Name of a requirement that may have versions within
                        it. This will use the constant,
                        VERSION_DESCRIPTORS.
    :type requirement: ``str``
    :return: ``str``
    """

    named_requirements = list()
    for requirement in requirements:
        name = _pip_requirement_split(requirement)[0]
        if name and not name.startswith('#'):
            named_requirements.append(name.lower())

    return sorted(set(named_requirements))


def pip_constraint_update(list_one, list_two):

    _list_one, _list_two = _lower_set_lists(list_one, list_two)
    _list_one, _list_two = list(_list_one), list(_list_two)
    for item2 in _list_two:
        item2_name, item2_versions, _ = _pip_requirement_split(item2)
        if item2_versions:
            for item1 in _list_one:
                if item2_name == _pip_requirement_split(item1)[0]:
                    item1_index = _list_one.index(item1)
                    _list_one[item1_index] = item2
                    break
            else:
                _list_one.append(item2)

    return sorted(_list_one)


def splitlines(string_with_lines):
    """Return a ``list`` from a string with lines."""

    return string_with_lines.splitlines()


def filtered_list(list_one, list_two):

    _list_one, _list_two = _lower_set_lists(list_one, list_two)
    return list(_list_one-_list_two)


def git_link_parse(repo):
    """Return a dict containing the parts of a git repository.

    :param repo: git repo string to parse.
    :type repo: ``str``
    :returns: ``dict``
    """

    if 'git+' in repo:
        _git_url = repo.split('git+', 1)[-1]
    else:
        _git_url = repo

    if '@' in _git_url:
        url, branch = _git_url.split('@', 1)
    else:
        url = _git_url
        branch = 'master'

    name = os.path.basename(url.rstrip('/'))
    _branch = branch.split('#')
    branch = _branch[0]

    plugin_path = None
    # Determine if the package is a plugin type
    if len(_branch) > 1 and 'subdirectory=' in _branch[-1]:
        plugin_path = _branch[-1].split('subdirectory=')[-1].split('&')[0]

    return {
        'name': name.split('.git')[0].lower(),
        'version': branch,
        'plugin_path': plugin_path,
        'url': url,
        'original': repo
    }


def git_link_parse_name(repo):
    """Return the name of a git repo."""

    return git_link_parse(repo)['name']


class FilterModule(object):
    """Ansible jinja2 filters."""

    @staticmethod
    def filters():
        return {
            'bit_length_power_of_2': bit_length_power_of_2,
            'netloc': get_netloc,
            'netloc_no_port': get_netloc_no_port,
            'netorigin': get_netorigin,
            'string_2_int': string_2_int,
            'pip_requirement_names': pip_requirement_names,
            'pip_constraint_update': pip_constraint_update,
            'splitlines': splitlines,
            'filtered_list': filtered_list,
            'git_link_parse': git_link_parse,
            'git_link_parse_name': git_link_parse_name,
            'deprecated': _deprecated
        }
