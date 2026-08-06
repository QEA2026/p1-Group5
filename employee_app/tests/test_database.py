import unittest
import sqlite3
import os
import tempfile

import database
from pathlib import Path


class TestDatabase(unittest.TestCase):

    def setUp(self):

        self.test_db = tempfile.NamedTemporaryFile(delete=False)
        self.test_db.close()

        self.original_db_path = database.DB_PATH

        database.DB_PATH = self.test_db.name

        project_root = Path(__file__).resolve().parents[2]

        schema_path = project_root / "db" / "schema.sql"
        seed_path = project_root / "db" / "seed.sql"

        conn = sqlite3.connect(database.DB_PATH)

        with open(schema_path, "r") as schema_file:
            conn.executescript(schema_file.read())

        with open(seed_path, "r") as seed_file:
            conn.executescript(seed_file.read())

        conn.commit()
        conn.close()



    def tearDown(self):

        database.DB_PATH = self.original_db_path

        if os.path.exists(self.test_db.name):
            os.remove(self.test_db.name)


    def test_create_expense_success(self):

        expense_id = database.create_expense(
            1,
            75.50,
            "Hotel stay",
            "2026-07-20"
        )


        self.assertIsNotNone(expense_id)


        conn = sqlite3.connect(database.DB_PATH)
        cursor = conn.cursor()


        cursor.execute(
            """
            SELECT amount, exp_description
            FROM expenses
            WHERE expense_id = ?
            """,
            (expense_id,)
        )

        expense = cursor.fetchone()


        self.assertEqual(expense[0], 75.50)
        self.assertEqual(expense[1], "Hotel stay")


        conn.close()


    def test_get_employee_expenses_success(self):

        expenses = database.get_employee_expenses(1)


        self.assertGreater(
            len(expenses),
            0
        )


        self.assertEqual(
            expenses[0]["expense"].user_id,
            1
        )


    def test_update_pending_expense_success(self):

        updated = database.update_expense(
            2,
            150.00,
            "Updated training course",
            "2026-07-22"
        )


        self.assertTrue(updated)


        expense = database.get_expense_by_id(2)


        self.assertEqual(
            expense.amount,
            150.00
        )

        self.assertEqual(
            expense.description,
            "Updated training course"
        )



    def test_delete_pending_expense_success(self):

        deleted = database.delete_expense(5)


        self.assertTrue(deleted)


        expense = database.get_expense_by_id(5)


        self.assertIsNone(expense)



    def test_delete_approved_expense_fails(self):

        deleted = database.delete_expense(1)


        self.assertFalse(deleted)



if __name__ == "__main__":
    unittest.main()