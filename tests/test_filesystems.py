import json
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory, TemporaryFile
from time import time_ns

import pytest
from fs import ResourceType, errors, open_fs
from fs.opener.errors import OpenerError
from fs.test import FSTestCases
from synapseclient import Folder, Synapse
from synapseclient.core.exceptions import SynapseFileNotFoundError, SynapseHTTPError

from dcqc.filesystems.remote_file import RemoteFile
from dcqc.filesystems.synapsefs import SynapseFS, synapse_errors


def test_for_error_when_providing_invalid_url_to_open_fs():
    with pytest.raises(OpenerError):
        open_fs("syn://")


def test_for_fs_errors_when_using_synapse_errors_context_manager():
    with pytest.raises(errors.FSError):
        with synapse_errors("foo"):
            raise SynapseFileNotFoundError("bar")
    with pytest.raises(errors.FSError):
        with synapse_errors("foo"):
            raise SynapseHTTPError("does not exist")
    with pytest.raises(errors.FSError):
        with synapse_errors("foo"):
            raise SynapseHTTPError("already exists")
    with pytest.raises(SynapseHTTPError):
        with synapse_errors("foo"):
            raise SynapseHTTPError("something else")
    with pytest.warns(UserWarning):
        with synapse_errors("foo"):
            raise SynapseHTTPError("File size must be at least one byte")


def test_that_a_remote_file_without_a_close_on_callable_can_be_closed():
    with TemporaryFile() as temp_file:
        remote_file = RemoteFile(temp_file, "foo", "w", on_close=None)
        remote_file.close()


def test_that_staging_a_local_file_creates_a_copy(get_data):
    path = get_data("test.txt")
    local_fs = open_fs(f"osfs://{path.parent}")
    with TemporaryDirectory() as tmp_dir_name:
        tmp_dir_path = Path(tmp_dir_name)
        target_path = tmp_dir_path / "test.txt"
        assert not target_path.exists()
        target_file = target_path.open("wb")
        local_fs.download(path.name, target_file)
        target_file.close()
        assert target_path.exists()


@pytest.mark.integration
def test_that_staging_a_synapse_file_creates_a_copy(mocker):
    mocked_synapse = mocker.patch("synapseclient.Synapse")
    synapse_fs = open_fs("syn://syn50545516")
    with TemporaryDirectory() as tmp_dir_name:
        tmp_dir_path = Path(tmp_dir_name)
        tmp_file_path = tmp_dir_path / "mocked.txt"
        with tmp_file_path.open("w") as tmp_file:
            tmp_file.write("foobar")
        mocked_entity = mocker.PropertyMock(tmp_file_path)
        mocked_synapse.get.return_value = mocked_entity
        target_path = tmp_dir_path / "test.txt"
        assert not target_path.exists()
        target_file = target_path.open("wb")
        synapse_fs.download("test.txt", target_file)
        target_file.close()
        assert target_path.exists()


@pytest.mark.integration
class TestSynapseFS(FSTestCases, unittest.TestCase):
    TEST_ROOT = "syn50555278"

    @classmethod
    def setUpClass(cls):
        cls.auth_token = os.environ.get("SYNAPSE_AUTH_TOKEN")
        if cls.auth_token is None:
            cls.skipTest(cls, "'SYNAPSE_AUTH_TOKEN' not set in environment.")
        cls.synapse = Synapse()
        cls.synapse.login(authToken=cls.auth_token)
        cls._empty_project()

    @classmethod
    def tearDownClass(cls):
        cls._empty_project()

    @classmethod
    def _empty_project(cls):
        # Empty project before running tests
        for child in cls.synapse.getChildren(cls.TEST_ROOT):
            cls.synapse.delete(child["id"])

    def make_fs(self):
        folder_name = str(time_ns())
        self.folder = Folder(folder_name, parent=self.TEST_ROOT)
        self.folder = self.synapse.store(self.folder)
        synapse_fs = SynapseFS(self.folder.id, self.auth_token)
        return synapse_fs

    def destroy_fs(self, fs):
        fs.close()
        self.synapse.delete(self.folder)

    def test_getsize(self):
        self.fs.writebytes("empty", b"")
        self.fs.writebytes("one", b"a")
        self.fs.writebytes("onethousand", ("b" * 1000).encode("ascii"))

        # Start of modification -----------------------------------------------------
        #
        # Synapse doesn't support empty files, so SynapseFS uploads
        # files with a single null byte to bypass this restriction
        self.assertEqual(self.fs.getsize("empty"), 1)
        #
        # End of modification -------------------------------------------------------

        self.assertEqual(self.fs.getsize("one"), 1)
        self.assertEqual(self.fs.getsize("onethousand"), 1000)
        with self.assertRaises(errors.ResourceNotFound):
            self.fs.getsize("doesnotexist")

    def test_getinfo(self):
        # Test special case of root directory
        # Root directory has a name of ''
        root_info = self.fs.getinfo("/")
        # Start of modification -----------------------------------------------------
        #
        # In SynapseFS, the root will have the name of the project/folder
        self.assertEqual(root_info.name, self.folder.name)
        #
        # End of modification -------------------------------------------------------
        self.assertTrue(root_info.is_dir)
        self.assertIn("basic", root_info.namespaces)

        # Make a file of known size
        self.fs.writebytes("foo", b"bar")
        self.fs.makedir("dir")

        # Check basic namespace
        info = self.fs.getinfo("foo").raw
        self.assertIn("basic", info)
        self.assertIsInstance(info["basic"]["name"], str)
        self.assertEqual(info["basic"]["name"], "foo")
        self.assertFalse(info["basic"]["is_dir"])

        # Check basic namespace dir
        info = self.fs.getinfo("dir").raw
        self.assertIn("basic", info)
        self.assertEqual(info["basic"]["name"], "dir")
        self.assertTrue(info["basic"]["is_dir"])

        # Get the info
        info = self.fs.getinfo("foo", namespaces=["details"]).raw
        self.assertIn("basic", info)
        self.assertIsInstance(info, dict)
        self.assertEqual(info["details"]["size"], 3)
        self.assertEqual(info["details"]["type"], int(ResourceType.file))

        # Test getdetails
        self.assertEqual(info, self.fs.getdetails("foo").raw)

        # Raw info should be serializable
        try:
            json.dumps(info)
        except (TypeError, ValueError):
            raise AssertionError("info should be JSON serializable")

        # Non existant namespace is not an error
        no_info = self.fs.getinfo("foo", "__nosuchnamespace__").raw
        self.assertIsInstance(no_info, dict)
        self.assertEqual(no_info["basic"], {"name": "foo", "is_dir": False})

        # Check a number of standard namespaces
        # FS objects may not support all these, but we can at least
        # invoke the code
        info = self.fs.getinfo("foo", namespaces=["access", "stat", "details"])

        # Check that if the details namespace is present, times are
        # of valid types.
        if "details" in info.namespaces:
            details = info.raw["details"]
            self.assertIsInstance(details.get("accessed"), (type(None), int, float))
            self.assertIsInstance(details.get("modified"), (type(None), int, float))
            self.assertIsInstance(details.get("created"), (type(None), int, float))
            self.assertIsInstance(
                details.get("metadata_changed"), (type(None), int, float)
            )

    def test_create(self):
        # Test create new file
        self.assertFalse(self.fs.exists("foo"))
        self.fs.create("foo")
        self.assertTrue(self.fs.exists("foo"))
        self.assertEqual(self.fs.gettype("foo"), ResourceType.file)
        # Start of modification -------------------------------------------------------
        #
        # Synapse doesn't support empty files, so empty
        # files are created with a single null byte
        self.assertEqual(self.fs.getsize("foo"), 1)
        #
        # End of modification -------------------------------------------------------

        # Test wipe existing file
        self.fs.writebytes("foo", b"bar")
        self.assertEqual(self.fs.getsize("foo"), 3)
        self.fs.create("foo", wipe=True)
        # Start of modification -------------------------------------------------------
        #
        # Synapse doesn't support empty files, so empty
        # files are created with a single null byte
        self.assertEqual(self.fs.getsize("foo"), 1)
        #
        # End of modification -------------------------------------------------------

        # Test create with existing file, and not wipe
        self.fs.writebytes("foo", b"bar")
        self.assertEqual(self.fs.getsize("foo"), 3)
        self.fs.create("foo", wipe=False)
        self.assertEqual(self.fs.getsize("foo"), 3)

    def test_getinfo_synapse(self):
        # Test with file
        self.fs.create("foo")
        file_info = self.fs.getinfo("foo", namespaces=["synapse", "annotations"])
        self.assertIn("synapse", file_info.namespaces)
        self.assertIn("annotations", file_info.namespaces)
        self.assertIsNot(file_info.get("synapse", "content_type"), None)
        # Test with folder
        self.fs.makedir("bar")
        folder_info = self.fs.getinfo("bar", namespaces=["synapse", "annotations"])
        self.assertIn("synapse", folder_info.namespaces)
        self.assertIn("annotations", folder_info.namespaces)
        self.assertIs(folder_info.get("synapse", "content_type"), None)

    def test_valid_types(self):
        with self.assertRaises(errors.ResourceInvalid):
            self.fs._synapse_id_to_entity("syn50557522")  # TestTable

    def test_double_period_in_path_while_remaining_in_the_given_path(self):
        self.fs.makedirs("foo/bar/baz")
        synapse_id_1 = self.fs._path_to_synapse_id("foo/bar/baz")
        synapse_id_2 = self.fs._path_to_synapse_id("foo/bar/../bar/baz")
        self.assertEqual(synapse_id_1, synapse_id_2)

    def test_that_an_fs_can_be_created_with_a_double_period_after_a_folder(self):
        fs = SynapseFS("syn50557597/..", self.auth_token)
        info = fs.getinfo(".", namespaces=["synapse"])
        assert info.get("synapse", "id") == "syn50545516"

    def test_that_the_parent_folder_of_a_file_can_be_opened_using_double_periods(self):
        fs = SynapseFS("syn50555279/..", self.auth_token)
        info = fs.getinfo(".", namespaces=["synapse"])
        assert info.get("synapse", "id") == "syn50545516"

    def test_for_an_error_when_opening_a_synapse_fs_with_a_file_root(self):
        with pytest.raises(errors.CreateFailed):
            SynapseFS("syn50555279", self.auth_token)

    def test_for_error_when_double_period_reaches_outside_of_sub_fs(self):
        self.fs.makedirs("foo")
        sub_fs = self.fs.opendir("foo")
        with pytest.raises(errors.IllegalBackReference):
            sub_fs.getinfo("..")

    def test_double_period_after_file_in_path(self):
        self.fs.makedirs("foo")
        self.fs.touch("foo/test.txt")
        info_1 = self.fs.getinfo("foo", namespaces=["synapse"])
        info_2 = self.fs.getinfo("foo/test.txt/..", namespaces=["synapse"])
        synapse_id_1 = info_1.get("synapse", "id")
        synapse_id_2 = info_2.get("synapse", "id")
        self.assertEqual(synapse_id_1, synapse_id_2)
