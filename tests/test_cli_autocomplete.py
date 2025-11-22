import unittest

from cli import _decorate_category


class CliAutocompleteTest(unittest.TestCase):

    def test_reserved_category_is_decorated(self) -> None:
        self.assertEqual(_decorate_category("Income"), "Income*")

    def test_non_reserved_category_unchanged(self) -> None:
        self.assertEqual(_decorate_category("groceries"), "groceries")
