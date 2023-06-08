import pytest

from dcqc.target import PairedTarget, SingleTarget


def test_that_a_target_can_be_saved_and_restored_without_changing(test_files):
    test_file = test_files["good"]
    target_1 = SingleTarget(test_file)
    target_1_dict = target_1.to_dict()
    target_2 = SingleTarget.from_dict(target_1_dict)
    target_2_dict = target_2.to_dict()
    assert target_1 == target_2
    assert target_1_dict == target_2_dict


def test_for_an_error_when_restoring_a_target_with_a_discordant_type(test_files):
    test_file = test_files["good"]
    target_1 = SingleTarget(test_file)
    target_1_dict = target_1.to_dict()
    target_1_dict["type"] = "UnexpectedQcTarget"
    with pytest.raises(ValueError):
        SingleTarget.from_dict(target_1_dict)


def test_for_an_error_when_creating_single_file_target_with_two_files(test_files):
    test_file = test_files["good"]
    with pytest.raises(ValueError):
        SingleTarget([test_file, test_file])


def test_that_paired_file_target_can_be_created_with_two_files(test_files):
    test_file = test_files["good"]
    target = PairedTarget([test_file, test_file])
    assert len(target.files) == 2


def test_for_an_error_when_creating_paired_file_target_with_one_file(test_files):
    test_file = test_files["good"]
    with pytest.raises(ValueError):
        PairedTarget(test_file)


def test_for_an_error_when_creating_paired_file_target_with_one_file_in_list(
    test_files,
):
    test_file = test_files["good"]
    with pytest.raises(ValueError):
        PairedTarget([test_file])
