import tempfile
from pathlib import Path

from pdf_mass_unlock.passwords import iter_passwords


def test_iter_passwords_single():
    """Test that single password is yielded first."""
    passwords = list(iter_passwords(single="mypassword"))

    assert passwords == [("mypassword", "single")]


def test_iter_passwords_dictionary():
    """Test that dictionary file passwords are yielded."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        f.write("password1\npassword2\npassword3\n")
        dict_path = Path(f.name)

    try:
        passwords = list(iter_passwords(dictionary_path=dict_path))

        assert passwords == [
            ("password1", "dictionary"),
            ("password2", "dictionary"),
            ("password3", "dictionary"),
        ]
    finally:
        dict_path.unlink()


def test_iter_passwords_dictionary_with_comments_and_blanks():
    """Test that dictionary parsing handles comments and blank lines."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        f.write("password1\n\n# This is a comment\npassword2\n   \npassword3\n")
        dict_path = Path(f.name)

    try:
        passwords = list(iter_passwords(dictionary_path=dict_path))

        assert passwords == [
            ("password1", "dictionary"),
            ("password2", "dictionary"),
            ("password3", "dictionary"),
        ]
    finally:
        dict_path.unlink()


def test_iter_passwords_dictionary_preserves_whitespace():
    """Test that dictionary parsing preserves leading/trailing whitespace."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        f.write("  password1  \n password2\npassword3 \n")
        dict_path = Path(f.name)

    try:
        passwords = list(iter_passwords(dictionary_path=dict_path))

        # Should preserve whitespace as it might be part of legitimate passwords
        assert passwords == [
            ("  password1  ", "dictionary"),
            (" password2", "dictionary"),
            ("password3 ", "dictionary"),
        ]
    finally:
        dict_path.unlink()


def test_iter_passwords_env_var():
    """Test that environment variable password is yielded."""
    env = {"PDFMASSUNLOCK_PASSWORD": "envpassword"}
    passwords = list(iter_passwords(env=env))

    assert passwords == [("envpassword", "environment")]


def test_iter_passwords_try_empty():
    """Test that empty password is yielded when requested."""
    passwords = list(iter_passwords(try_empty=True))

    assert passwords == [("", "empty")]


def test_iter_passwords_order():
    """Test that passwords are yielded in the correct order."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        f.write("dictpass\n")
        dict_path = Path(f.name)

    try:
        env = {"PDFMASSUNLOCK_PASSWORD": "envpass"}
        passwords = list(
            iter_passwords(single="singlepass", dictionary_path=dict_path, env=env, try_empty=True)
        )

        # Should be: single, dictionary, env, empty
        assert passwords == [
            ("singlepass", "single"),
            ("dictpass", "dictionary"),
            ("envpass", "environment"),
            ("", "empty"),
        ]
    finally:
        dict_path.unlink()


def test_iter_passwords_no_duplicates():
    """Test that duplicate passwords are not yielded."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        f.write("duplicate\nanother\nduplicate\n")
        dict_path = Path(f.name)

    try:
        passwords = list(iter_passwords(single="duplicate", dictionary_path=dict_path))

        # Should only have unique passwords, preserving order
        assert passwords == [("duplicate", "single"), ("another", "dictionary")]
    finally:
        dict_path.unlink()


def test_iter_passwords_env_var_override():
    """Test that env var doesn't duplicate if already provided as single."""
    env = {"PDFMASSUNLOCK_PASSWORD": "duplicate"}
    passwords = list(iter_passwords(single="duplicate", env=env))

    # Should only have unique passwords, preserving order
    assert passwords == [("duplicate", "single")]


if __name__ == "__main__":
    test_iter_passwords_single()
    test_iter_passwords_dictionary()
    test_iter_passwords_dictionary_with_comments_and_blanks()
    test_iter_passwords_dictionary_preserves_whitespace()
    test_iter_passwords_env_var()
    test_iter_passwords_try_empty()
    test_iter_passwords_order()
    test_iter_passwords_no_duplicates()
    test_iter_passwords_env_var_override()
    print("All passwords tests passed!")
