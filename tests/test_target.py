import pytest

from dcqc.target import BaseTarget, PairedTarget, SingleTarget


def test_that_a_target_can_be_saved_and_restored_without_changing(test_files):
    test_file = test_files["good_txt"]
    target_1 = SingleTarget([test_file])
    target_1_dict = target_1.to_dict()
    target_2 = SingleTarget.from_dict(target_1_dict)
    target_2_dict = target_2.to_dict()
    assert target_1 == target_2
    assert target_1_dict == target_2_dict


def test_for_an_error_when_restoring_a_target_with_a_discordant_type(test_files):
    test_file = test_files["good_txt"]
    target_1 = SingleTarget([test_file])
    target_1_dict = target_1.to_dict()
    target_1_dict["type"] = "UnexpectedQcTarget"
    with pytest.raises(ValueError):
        SingleTarget.from_dict(target_1_dict)


def test_for_an_error_when_creating_single_file_target_with_two_files(test_files):
    test_file = test_files["good_txt"]
    with pytest.raises(ValueError):
        SingleTarget([test_file, test_file])


def test_that_paired_file_target_can_be_created_with_two_files(test_files):
    test_file = test_files["good_txt"]
    target = PairedTarget([test_file, test_file])
    assert len(target.files) == 2


def test_that_a_paired_target_can_be_saved_and_restored_without_changing(test_files):
    test_file = test_files["good_txt"]
    target_1 = PairedTarget([test_file, test_file])
    target_1_dict = target_1.to_dict()
    target_2 = PairedTarget.from_dict(target_1_dict)
    target_2_dict = target_2.to_dict()
    assert target_1 == target_2
    assert target_1_dict == target_2_dict


def test_for_an_error_when_creating_paired_file_target_with_one_file(test_files):
    test_file = test_files["good_txt"]
    with pytest.raises(TypeError):
        PairedTarget(test_file)


def test_for_an_error_when_creating_single_file_target_with_a_bare_file(test_files):
    test_file = test_files["good_txt"]
    with pytest.raises(TypeError):
        SingleTarget(test_file)


def test_for_an_error_when_creating_paired_file_target_with_one_file_in_list(
    test_files,
):
    test_file = test_files["good_txt"]
    with pytest.raises(ValueError):
        PairedTarget([test_file])


def test_for_an_error_when_creating_paired_file_target_with_different_file_types(
    test_files,
):
    txt_file = test_files["good_txt"]
    fastq_file = test_files["good_fastq"]
    with pytest.raises(ValueError, match="must have the same file type"):
        PairedTarget([txt_file, fastq_file])


def test_that_a_paired_target_returns_the_file_type_of_its_files(test_files):
    fastq_file = test_files["good_fastq"]
    target = PairedTarget([fastq_file, fastq_file])
    assert target.get_file_type() == fastq_file.get_file_type()


def test_that_a_single_target_returns_the_file_type_of_its_file(test_files):
    txt_file = test_files["good_txt"]
    target = SingleTarget([txt_file])
    assert target.get_file_type() == txt_file.get_file_type()


def test_that_the_target_classes_set_their_file_count():
    assert BaseTarget.n_files is None
    assert SingleTarget.n_files == 1
    assert PairedTarget.n_files == 2


def test_that_validate_files_finds_no_problem_with_good_files(test_files):
    fastq_file = test_files["good_fastq"]
    assert SingleTarget.validate_files([fastq_file]) == []
    assert PairedTarget.validate_files([fastq_file, fastq_file]) == []


def test_that_validate_files_reports_a_wrong_file_count(test_files):
    txt_file = test_files["good_txt"]
    problems = PairedTarget.validate_files([txt_file, txt_file, txt_file])
    expected = "has a file count of 3. A PairedTarget must have exactly 2 files."
    assert problems == [expected]


def test_that_validate_files_does_not_check_file_types_after_a_wrong_count(
    test_files,
):
    txt_file = test_files["good_txt"]
    fastq_file = test_files["good_fastq"]
    problems = SingleTarget.validate_files([txt_file, fastq_file])
    assert problems == [
        "has a file count of 2. A SingleTarget must have exactly 1 file."
    ]


def test_that_validate_files_reports_different_file_types(test_files):
    txt_file = test_files["good_txt"]
    fastq_file = test_files["good_fastq"]
    problems = PairedTarget.validate_files([txt_file, fastq_file])
    assert len(problems) == 1
    assert problems[0].startswith("has different file types: ['TXT', 'FASTQ'].")


def test_that_validate_files_reports_no_files_for_any_target_class():
    # The base class accepts any file count, but not zero files
    assert BaseTarget.validate_files([]) == [
        "has no files. A target must have at least one file."
    ]


def test_that_the_target_error_message_starts_with_the_class_name(test_files):
    txt_file = test_files["good_txt"]
    message = "PairedTarget has a file count of 1."
    with pytest.raises(ValueError, match=message):
        PairedTarget([txt_file])
