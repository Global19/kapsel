# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © 2016, Continuum Analytics, Inc. All rights reserved.
#
# The full license is in the file LICENSE.txt, distributed with this software.
# ----------------------------------------------------------------------------
import hashlib
import os

from conda_kapsel.local_state_file import LocalStateFile
from conda_kapsel.plugins.registry import PluginRegistry
from conda_kapsel.plugins.requirement import UserConfigOverrides
from conda_kapsel.plugins.requirements.download import DownloadRequirement

from conda_kapsel.internal.test.tmpfile_utils import with_directory_contents

ENV_VAR = 'DATAFILE'


def test_filename_not_set():
    def check_not_set(dirname):
        local_state = LocalStateFile.load_for_directory(dirname)
        requirement = DownloadRequirement(registry=PluginRegistry(),
                                          env_var=ENV_VAR,
                                          url='http://example.com',
                                          filename=ENV_VAR)
        status = requirement.check_status(dict(PROJECT_DIR=dirname), local_state, 'default', UserConfigOverrides())
        assert not status
        assert "Environment variable {} is not set.".format(ENV_VAR) == status.status_description

    with_directory_contents({}, check_not_set)


def test_download_filename_missing():
    def check_missing_filename(dirname):
        local_state = LocalStateFile.load_for_directory(dirname)
        filename = '/data.zip'
        requirement = DownloadRequirement(registry=PluginRegistry(),
                                          env_var=ENV_VAR,
                                          url='http://localhost/data.zip',
                                          filename='data.zip')
        status = requirement.check_status({ENV_VAR: filename,
                                           'PROJECT_DIR': dirname}, local_state, 'default', UserConfigOverrides())
        assert not status
        assert 'File not found: {}'.format(filename) == status.status_description

    with_directory_contents({}, check_missing_filename)


def make_file_with_checksum():
    datafile = ("column1,column2,column3\n"
                "value11,value12,value13\n"
                "value21,value22,value23\n"
                "value31,value32,value33")
    checksum = hashlib.md5()
    checksum.update(datafile.encode('utf-8'))
    digest = checksum.hexdigest()
    return datafile, digest


def test_download_checksum():
    datafile, digest = make_file_with_checksum()

    def verify_checksum(dirname):
        local_state = LocalStateFile.load_for_directory(dirname)
        filename = os.path.join(dirname, 'data.zip')
        requirement = DownloadRequirement(registry=PluginRegistry(),
                                          env_var=ENV_VAR,
                                          url='http://localhost/data.zip',
                                          filename='data.zip',
                                          hash_algorithm='md5',
                                          hash_value=digest)
        status = requirement.check_status({ENV_VAR: filename,
                                           'PROJECT_DIR': dirname}, local_state, 'default', UserConfigOverrides())
        assert 'File downloaded to {}'.format(filename) == status.status_description
        assert status

    with_directory_contents({'data.zip': datafile}, verify_checksum)


def test_download_with_no_checksum():
    datafile, digest = make_file_with_checksum()

    def downloaded_file_valid(dirname):
        local_state = LocalStateFile.load_for_directory(dirname)
        filename = os.path.join(dirname, 'data.zip')
        requirement = DownloadRequirement(registry=PluginRegistry(),
                                          env_var=ENV_VAR,
                                          url='http://localhost/data.zip',
                                          filename='data.zip')
        status = requirement.check_status({ENV_VAR: filename,
                                           'PROJECT_DIR': dirname}, local_state, 'default', UserConfigOverrides())
        assert status
        assert 'File downloaded to {}'.format(filename) == status.status_description

    with_directory_contents({'data.zip': datafile}, downloaded_file_valid)


def test_use_variable_name_for_filename():
    problems = []
    requirements = []
    DownloadRequirement._parse(PluginRegistry(),
                               varname='FOO',
                               item='http://example.com/',
                               problems=problems,
                               requirements=requirements)
    assert [] == problems
    assert len(requirements) == 1
    assert requirements[0].filename == 'FOO'
    assert requirements[0].url == 'http://example.com/'
    assert not requirements[0].unzip


def test_checksum_is_not_a_string():
    problems = []
    requirements = []
    DownloadRequirement._parse(PluginRegistry(),
                               varname='FOO',
                               item=dict(url='http://example.com/',
                                         md5=[]),
                               problems=problems,
                               requirements=requirements)
    assert ['Checksum value for FOO should be a string not [].'] == problems
    assert len(requirements) == 0


def test_description_is_not_a_string():
    problems = []
    requirements = []
    DownloadRequirement._parse(PluginRegistry(),
                               varname='FOO',
                               item=dict(url='http://example.com/',
                                         description=[]),
                               problems=problems,
                               requirements=requirements)
    assert ["'description' field for download item FOO is not a string"] == problems
    assert len(requirements) == 0


def test_description_property():
    problems = []
    requirements = []
    DownloadRequirement._parse(PluginRegistry(),
                               varname='FOO',
                               item=dict(url='http://example.com/',
                                         description="hi"),
                               problems=problems,
                               requirements=requirements)
    assert [] == problems
    assert len(requirements) == 1
    assert requirements[0].title == 'FOO'
    assert requirements[0].description == 'hi'


def test_download_item_is_a_list_not_a_string_or_dict():
    problems = []
    requirements = []
    DownloadRequirement._parse(PluginRegistry(), varname='FOO', item=[], problems=problems, requirements=requirements)
    assert ["Download name FOO should be followed by a URL string or a dictionary describing the download."] == problems
    assert len(requirements) == 0


def test_download_item_is_none_not_a_string_or_dict():
    problems = []
    requirements = []
    DownloadRequirement._parse(PluginRegistry(), varname='FOO', item=None, problems=problems, requirements=requirements)
    assert ["Download name FOO should be followed by a URL string or a dictionary describing the download."] == problems
    assert len(requirements) == 0


def test_unzip_is_not_a_bool():
    problems = []
    requirements = []
    DownloadRequirement._parse(PluginRegistry(),
                               varname='FOO',
                               item=dict(url='http://example.com/',
                                         unzip=[]),
                               problems=problems,
                               requirements=requirements)
    assert ["Value of 'unzip' for download item FOO should be a boolean, not []."] == problems
    assert len(requirements) == 0


def test_use_unzip_if_url_ends_in_zip():
    problems = []
    requirements = []
    DownloadRequirement._parse(PluginRegistry(),
                               varname='FOO',
                               item='http://example.com/bar.zip',
                               problems=problems,
                               requirements=requirements)
    assert [] == problems
    assert len(requirements) == 1
    assert requirements[0].filename == 'bar'
    assert requirements[0].url == 'http://example.com/bar.zip'
    assert requirements[0].unzip


def test_allow_manual_override_of_use_unzip_if_url_ends_in_zip():
    problems = []
    requirements = []
    DownloadRequirement._parse(PluginRegistry(),
                               varname='FOO',
                               item=dict(url='http://example.com/bar.zip',
                                         unzip=False),
                               problems=problems,
                               requirements=requirements)
    assert [] == problems
    assert len(requirements) == 1
    assert requirements[0].filename == 'bar.zip'
    assert requirements[0].url == 'http://example.com/bar.zip'
    assert not requirements[0].unzip


def test_use_unzip_if_url_ends_in_zip_and_filename_does_not():
    problems = []
    requirements = []
    DownloadRequirement._parse(PluginRegistry(),
                               varname='FOO',
                               item=dict(url='http://example.com/bar.zip',
                                         filename='something'),
                               problems=problems,
                               requirements=requirements)
    assert [] == problems
    assert len(requirements) == 1
    assert requirements[0].filename == 'something'
    assert requirements[0].url == 'http://example.com/bar.zip'
    assert requirements[0].unzip


def test_no_unzip_if_url_ends_in_zip_and_filename_also_does():
    problems = []
    requirements = []
    DownloadRequirement._parse(PluginRegistry(),
                               varname='FOO',
                               item=dict(url='http://example.com/bar.zip',
                                         filename='something.zip'),
                               problems=problems,
                               requirements=requirements)
    assert [] == problems
    assert len(requirements) == 1
    assert requirements[0].filename == 'something.zip'
    assert requirements[0].url == 'http://example.com/bar.zip'
    assert not requirements[0].unzip
