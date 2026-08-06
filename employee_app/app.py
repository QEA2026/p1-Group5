from datetime import date

from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from werkzeug.exceptions import HTTPException

import database
from auth import login_required
from logging_config import logger

app = Flask(__name__)
app.secret_key = "dev"


@app.errorhandler(Exception)
def handle_unexpected_error(error):
    if isinstance(error, HTTPException):
        return error
    logger.exception("Unhandled error: %s", error)
    raise error


def _validate_expense_form(form):
    """Returns (amount, description, date) from the form, or None if invalid (flashes the reason)."""
    description = form["description"].strip()
    expense_date = form["date"]
    amount_raw = form["amount"]

    try:
        amount = float(amount_raw)
    except ValueError:
        flash("Amount must be a number.")
        return None

    if amount <= 0:
        flash("Amount must be greater than zero.")
        return None

    if not description:
        flash("Description is required.")
        return None

    if not expense_date:
        flash("Date is required.")
        return None

    return amount, description, expense_date


@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        user = database.login(username, password)
        if user is None:
            logger.warning("Failed login attempt for username '%s'", username)
            flash("Invalid username or password.")
            return render_template("login.html")
        session["user_id"] = user.user_id
        session["username"] = user.username
        logger.info("User '%s' (id=%s) logged in", user.username, user.user_id)
        return redirect(url_for("dashboard"))
    return render_template("login.html")


@app.route("/logout")
def logout():
    if "user_id" in session:
        logger.info("User '%s' (id=%s) logged out", session.get("username"), session.get("user_id"))
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    expenses = database.get_employee_expenses(session["user_id"])
    return render_template("dashboard.html", expenses=expenses, today=date.today().isoformat())


@app.route("/expenses", methods=["POST"])
@login_required
def submit_expense():
    parsed = _validate_expense_form(request.form)
    if parsed is None:
        return redirect(url_for("dashboard"))
    amount, description, expense_date = parsed

    expense_id = database.create_expense(session["user_id"], amount, description, expense_date)
    logger.info("User id=%s created expense id=%s amount=%s", session["user_id"], expense_id, amount)
    flash("Expense submitted.")
    return redirect(url_for("dashboard"))


def _get_own_expense_or_404(expense_id):
    record = database.get_expense_with_status(expense_id)
    if record is None or record["expense"].user_id != session["user_id"]:
        abort(404)
    return record


@app.route("/expenses/<int:expense_id>/edit", methods=["GET", "POST"])
@login_required
def edit_expense(expense_id):
    record = _get_own_expense_or_404(expense_id)
    if record["status"] != "pending":
        flash("Only pending expenses can be edited.")
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        parsed = _validate_expense_form(request.form)
        if parsed is None:
            return redirect(url_for("edit_expense", expense_id=expense_id))
        amount, description, expense_date = parsed

        if database.update_expense(expense_id, amount, description, expense_date):
            logger.info("User id=%s updated expense id=%s", session["user_id"], expense_id)
            flash("Expense updated.")
        else:
            flash("Expense could no longer be edited.")
        return redirect(url_for("dashboard"))

    return render_template("edit_expense.html", expense=record["expense"])


@app.route("/expenses/<int:expense_id>/delete", methods=["POST"])
@login_required
def delete_expense(expense_id):
    record = _get_own_expense_or_404(expense_id)
    if record["status"] != "pending":
        flash("Only pending expenses can be deleted.")
        return redirect(url_for("dashboard"))

    database.delete_expense(expense_id)
    flash("Expense deleted.")
    return redirect(url_for("dashboard"))


# new api routes for postman testing
@app.route("/api/login", methods=["POST"])
def api_login():
    """
    API login endpoint for Postman testing.
    Returns JSON responses with status codes.
    """

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    user = database.login(username, password)

    if user is None:
        logger.warning("Failed API login attempt for username '%s'", username)

        return {
            "error": "Invalid username or password."
        }, 401

    session["user_id"] = user.user_id
    session["username"] = user.username

    return {
        "message": "Login successful",
        "user_id": user.user_id,
        "username": user.username
    }, 200


@app.route("/api/expenses", methods=["POST"])
@login_required
def api_submit_expense():
    """
    API endpoint for creating expenses.
    """

    amount = request.form.get("amount")
    description = request.form.get("description", "").strip()
    expense_date = request.form.get("date")

    # Validate amount
    try:
        amount = float(amount)
    except (ValueError, TypeError):
        return {
            "error": "Amount must be a number."
        }, 400

    if amount <= 0:
        return {
            "error": "Amount must be greater than zero."
        }, 400

    if not description:
        return {
            "error": "Description is required."
        }, 400

    if not expense_date:
        return {
            "error": "Date is required."
        }, 400


    expense_id = database.create_expense(
        session["user_id"],
        amount,
        description,
        expense_date
    )

    return {
        "message": "Expense created successfully",
        "expense_id": expense_id
    }, 201


@app.route("/api/expenses", methods=["GET"])
@login_required
def api_get_expenses():
    """
    API endpoint for retrieving employee expenses.
    """

    expenses = database.get_employee_expenses(
        session["user_id"]
    )

    expense_list = []

    for item in expenses:
        expense_list.append({
            "expense_id": item["expense"].expense_id,
            "amount": item["expense"].amount,
            "description": item["expense"].description,
            "date": item["expense"].date,
            "status": item["status"],
            "comment": item["comment"]
        })

    return {
        "expenses": expense_list
    }, 200


@app.route("/api/expenses/<int:expense_id>", methods=["PUT"])
@login_required
def api_update_expense(expense_id):
    """
    API endpoint for editing pending expenses.
    """

    record = _get_own_expense_or_404(expense_id)

    if record["status"] != "pending":
        return {
            "error": "Only pending expenses can be edited."
        }, 403


    amount = request.form.get("amount")
    description = request.form.get("description", "").strip()
    expense_date = request.form.get("date")


    try:
        amount = float(amount)
    except (ValueError, TypeError):
        return {
            "error": "Amount must be a number."
        }, 400


    updated = database.update_expense(
        expense_id,
        amount,
        description,
        expense_date
    )


    if updated:
        return {
            "message": "Expense updated successfully"
        }, 200

    return {
        "error": "Expense could not be updated."
    }, 400



@app.route("/api/expenses/<int:expense_id>", methods=["DELETE"])
@login_required
def api_delete_expense(expense_id):
    """
    API endpoint for deleting pending expenses.
    """

    record = _get_own_expense_or_404(expense_id)

    if record["status"] != "pending":
        return {
            "error": "Only pending expenses can be deleted."
        }, 403


    deleted = database.delete_expense(expense_id)

    if deleted:
        return {
            "message": "Expense deleted successfully"
        }, 200


    return {
        "error": "Expense could not be deleted."
    }, 400

if __name__ == "__main__":
    app.run(debug=True)
