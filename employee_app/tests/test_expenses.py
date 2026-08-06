import unittest
from unittest.mock import patch, Mock

from app import app

#Following the Arrange, Act, Assert pattern

class TestExpenseRoutes(unittest.TestCase):

    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

        with self.client.session_transaction() as session:
            session["user_id"] = 1
            session["username"] = "alice"


    @patch("app.database.create_expense")
    def test_submit_expense_success(self, mock_create_expense):

        # Arrange
        mock_create_expense.return_value = 1

        # Act
        response = self.client.post(
            "/expenses",
            data={
                "amount": "50.00",
                "description": "Hotel",
                "date": "2026-07-20"
            },
            follow_redirects=False
        )

        # Assert
        self.assertEqual(response.status_code, 302)

        mock_create_expense.assert_called_once_with(
            1,
            50.0,
            "Hotel",
            "2026-07-20"
        )


    @patch("app.database.create_expense")
    def test_submit_expense_invalid_amount(self, mock_create_expense):

        # Act
        response = self.client.post(
            "/expenses",
            data={
                "amount": "-50",
                "description": "Hotel",
                "date": "2026-07-20"
            },
            follow_redirects=False
        )

        # Assert
        self.assertEqual(response.status_code, 302)

        mock_create_expense.assert_not_called()


    @patch("app.database.update_expense")
    @patch("app.database.get_expense_with_status")
    def test_edit_pending_expense_success(
            self,
            mock_get_expense,
            mock_update_expense):

        # Arrange
        mock_get_expense.return_value = {
            "expense": Mock(
                expense_id=1,
                user_id=1,
                amount=25,
                description="Lunch",
                date="2026-07-20"
            ),
            "status": "pending"
        }

        mock_update_expense.return_value = True


        # Act
        response = self.client.post(
            "/expenses/1/edit",
            data={
                "amount": "50",
                "description": "Updated hotel",
                "date": "2026-07-21"
            },
            follow_redirects=False
        )


        # Assert
        self.assertEqual(response.status_code, 302)

        mock_update_expense.assert_called_once_with(
            1,
            50.0,
            "Updated hotel",
            "2026-07-21"
        )



    @patch("app.database.get_expense_with_status")
    def test_edit_approved_expense_not_allowed(
            self,
            mock_get_expense):

        # Arrange
        mock_get_expense.return_value = {
            "expense": Mock(
                expense_id=1,
                user_id=1,
                amount=25,
                description="Lunch",
                date="2026-07-20"
            ),
            "status": "approved"
        }


        # Act
        response = self.client.post(
            "/expenses/1/edit",
            data={
                "amount": "50",
                "description": "Changed",
                "date": "2026-07-21"
            },
            follow_redirects=False
        )


        # Assert
        self.assertEqual(response.status_code, 302)


    @patch("app.database.delete_expense")
    @patch("app.database.get_expense_with_status")
    def test_delete_pending_expense_success(
            self,
            mock_get_expense,
            mock_delete_expense):

        # Arrange
        mock_get_expense.return_value = {
            "expense": Mock(
                expense_id=1,
                user_id=1
            ),
            "status": "pending"
        }

        mock_delete_expense.return_value = True


        # Act
        response = self.client.post(
            "/expenses/1/delete",
            follow_redirects=False
        )


        # Assert
        self.assertEqual(response.status_code, 302)

        mock_delete_expense.assert_called_once_with(1)



    @patch("app.database.delete_expense")
    @patch("app.database.get_expense_with_status")
    def test_delete_approved_expense_not_allowed(
            self,
            mock_get_expense,
            mock_delete_expense):

        # Arrange
        mock_get_expense.return_value = {
            "expense": Mock(
                expense_id=1,
                user_id=1
            ),
            "status": "approved"
        }


        # Act
        response = self.client.post(
            "/expenses/1/delete",
            follow_redirects=False
        )


        # Assert
        self.assertEqual(response.status_code, 302)

        mock_delete_expense.assert_not_called()



if __name__ == "__main__":
    unittest.main()