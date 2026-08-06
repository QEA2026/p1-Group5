import unittest
from app import app, _validate_expense_form


class TestExpenseValidation(unittest.TestCase):

    def setUp(self):
        self.app = app
        self.app.config["TESTING"] = True
        self.context = self.app.test_request_context()
        self.context.push()

    def tearDown(self):
        self.context.pop()

    def test_valid_expense_form(self):
        """
        Happy path:
        User enters valid expense information.
        """

        form = {
            "amount": "50.25",
            "description": "Hotel for conference",
            "date": "2026-07-20"
        }

        result = _validate_expense_form(form)

        self.assertEqual(
            result,
            (50.25, "Hotel for conference", "2026-07-20")
        )


    def test_expense_amount_not_number(self):
        """
        Sad path:
        User enters text instead of a number.
        """

        form = {
            "amount": "haha",
            "description": "Hotel",
            "date": "2026-07-20"
        }

        result = _validate_expense_form(form)

        self.assertIsNone(result)


    def test_expense_amount_negative(self):
        """
        Sad path:
        User enters a negative expense.
        """

        form = {
            "amount": "-10",
            "description": "Hotel",
            "date": "2026-07-20"
        }

        result = _validate_expense_form(form)

        self.assertIsNone(result)


    def test_expense_description_required(self):
        """
        Sad path:
        User leaves description blank.
        """

        form = {
            "amount": "25",
            "description": "   ",
            "date": "2026-07-20"
        }

        result = _validate_expense_form(form)

        self.assertIsNone(result)


    def test_expense_date_required(self):
        """
        Sad path:
        User does not provide a date.
        """

        form = {
            "amount": "25",
            "description": "Lunch",
            "date": ""
        }

        result = _validate_expense_form(form)

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()