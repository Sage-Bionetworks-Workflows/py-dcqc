import pytest
from hypothesis import given
from hypothesis.strategies import integers

from dcqc.targets.base_qc_target import BaseQcTarget


def test_that_targets_created_without_the_index_parameter_have_unique_indices():
    BaseQcTarget.reset_memory()
    targets = [BaseQcTarget(f"file://file_{num}.txt") for num in range(3)]
    assert len(targets) == len(set(targets))


@given(integers(min_value=0))
def test_that_the_index_parameter_is_set_as_a_property_in_target_object(index):
    BaseQcTarget.reset_memory()
    target = BaseQcTarget("file://file_1.txt", index=index)
    assert target.index == index


@given(integers(max_value=-1))
def test_for_an_error_when_creating_a_target_with_a_negative_index(index):
    BaseQcTarget.reset_memory()
    with pytest.raises(ValueError):
        BaseQcTarget("file://file_1.txt", index=index)


@given(integers(min_value=0))
def test_for_an_error_when_creating_a_target_with_duplicate_indices(index):
    BaseQcTarget.reset_memory()
    BaseQcTarget("file://file_1.txt", index=index)
    with pytest.raises(ValueError):
        BaseQcTarget("file://file_2.txt", index=index)


def test_for_a_warning_when_creating_a_target_with_duplicate_uris():
    BaseQcTarget.reset_memory()
    BaseQcTarget("file://file_1.txt")
    with pytest.warns(UserWarning):
        BaseQcTarget("file://file_1.txt")


def test_that_a_target_can_be_saved_and_restored_without_changing():
    uri = "file://file_1.txt"
    metadata = {"foo": "bar"}
    index = 100
    target_1 = BaseQcTarget(uri, metadata, index)
    target_1_dict = target_1.to_dict()
    BaseQcTarget.reset_memory()
    target_2 = BaseQcTarget.from_dict(target_1_dict)
    target_2_dict = target_2.to_dict()
    assert vars(target_1) == vars(target_2)
    assert target_1_dict == target_2_dict
