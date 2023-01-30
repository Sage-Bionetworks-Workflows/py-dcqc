import pytest

from dcqc.target import Target


def test_that_a_target_can_be_saved_and_restored_without_changing(test_files):
    test_file = test_files["good"]
    target_1 = Target(test_file)
    target_1_dict = target_1.to_dict()
    target_2 = Target.from_dict(target_1_dict)
    target_2_dict = target_2.to_dict()
    assert target_1 == target_2
    assert target_1_dict == target_2_dict


def test_for_an_error_when_restoring_a_target_with_a_discordant_type(test_files):
    test_file = test_files["good"]
    target_1 = Target(test_file)
    target_1_dict = target_1.to_dict()
    target_1_dict["type"] = "UnexpectedQcTarget"
    with pytest.raises(ValueError):
        Target.from_dict(target_1_dict)


def test_for_an_error_when_accessing_the_file_type_for_a_multifile_target(test_files):
    file = test_files["good"]
    target = Target(file, file)
    with pytest.raises(NotImplementedError):
        target.get_file_type()
