
import os
from decimal import Decimal, InvalidOperation

import mysql.connector
from flask import (
    Flask, render_template, request, jsonify,
    session, redirect, url_for
)
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")



def get_db_connection():
    return mysql.connector.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        user=os.environ.get("DB_USER", "root"),
       password=os.environ.get("DB_PASSWORD"),
        database=os.environ.get("DB_NAME", "shopease_db"),
        port=int(os.environ.get("DB_PORT", "3306"))
    )


def admin_required():
    return session.get("role") == "admin"


def error_response(message, status):
    return jsonify({"message": message}), status



@app.route("/")
def home():
    if "user_id" in session:
        return render_template("index.html")
    return redirect(url_for("login"))


@app.route("/checkout")
def checkout():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("checkout.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return render_template("signup.html")

    full_name = request.form.get("full_name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not full_name or not email or not password:
        return error_response("Please fill in all fields.", 400)

    if len(full_name) > 100 or len(email) > 150:
        return error_response("Name or email is too long.", 400)

    if len(password) < 8:
        return error_response(
            "Password must be at least 8 characters.", 400
        )

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            "SELECT user_id FROM users WHERE email = %s",
            (email,)
        )
        if cursor.fetchone():
            return error_response(
                "An account with this email already exists.", 409
            )

        cursor.execute(
            """
            INSERT INTO users (full_name, email, password_hash)
            VALUES (%s, %s, %s)
            """,
            (full_name, email, generate_password_hash(password))
        )
        connection.commit()

        return jsonify({
            "message": "Account created successfully! You can now log in."
        }), 201

    except mysql.connector.Error:
        if connection and connection.is_connected():
            connection.rollback()
        app.logger.exception("Signup failed.")
        return error_response("Unable to create your account.", 500)

    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not email or not password:
        return error_response(
            "Please enter your email and password.", 400
        )

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT user_id, full_name, email, password_hash, role
            FROM users
            WHERE email = %s
            """,
            (email,)
        )
        user = cursor.fetchone()

        if not user or not check_password_hash(
            user["password_hash"], password
        ):
            return error_response("Invalid email or password.", 401)

        session.clear()
        session["user_id"] = user["user_id"]
        session["full_name"] = user["full_name"]
        session["role"] = user["role"]

        destination = (
            url_for("admin_orders")
            if user["role"] == "admin"
            else url_for("home")
        )

        return jsonify({
            "message": "Login successful!",
            "redirect": destination
        })

    except mysql.connector.Error:
        app.logger.exception("Login failed.")
        return error_response("Unable to log in. Please try again.", 500)

    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/my-orders")
def my_orders():
    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT order_id, customer_name, total_amount, order_date
            FROM orders
            WHERE user_id = %s
            ORDER BY order_date DESC
            """,
            (session["user_id"],)
        )
        orders = cursor.fetchall()

        for order in orders:
            cursor.execute(
                """
                SELECT product_name, price, quantity
                FROM order_items
                WHERE order_id = %s
                """,
                (order["order_id"],)
            )
            order["items"] = cursor.fetchall()

        return render_template("my_orders.html", orders=orders)

    except mysql.connector.Error:
        app.logger.exception("Unable to load orders.")
        return "Unable to load orders. Check the Flask terminal.", 500

    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


@app.route("/api/products", methods=["GET"])
def list_products():
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT product_id, name, description, price, image_url
            FROM products
            WHERE is_active = TRUE
            ORDER BY product_id
            """
        )
        products = cursor.fetchall()

        for product in products:
            product["price"] = float(product["price"])

        return jsonify(products)

    except mysql.connector.Error:
        app.logger.exception("Unable to list products.")
        return error_response("Unable to load products.", 500)

    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


@app.route("/api/admin/products", methods=["POST"])
def create_product():
    if not admin_required():
        return error_response("Admin access required.", 403)

    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    description = str(data.get("description", "")).strip()
    image_url = str(data.get("image_url", "")).strip()

    try:
        price = Decimal(str(data.get("price", "")))
    except (InvalidOperation, ValueError):
        return error_response("Enter a valid product price.", 400)

    if not name or len(name) > 150 or price <= 0 or not price.is_finite():
        return error_response("Enter a valid name and positive price.", 400)

    if len(description) > 500 or len(image_url) > 500:
        return error_response("Description or image URL is too long.", 400)

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO products (name, description, price, image_url)
            VALUES (%s, %s, %s, %s)
            """,
            (name, description, price, image_url)
        )
        connection.commit()

        return jsonify({
            "message": "Product created.",
            "product_id": cursor.lastrowid
        }), 201

    except mysql.connector.IntegrityError:
        return error_response("A product with this name already exists.", 409)

    except mysql.connector.Error:
        if connection and connection.is_connected():
            connection.rollback()
        app.logger.exception("Product creation failed.")
        return error_response("Unable to create product.", 500)

    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


@app.route("/api/admin/products/<int:product_id>", methods=["PUT", "DELETE"])
def manage_product(product_id):
    if not admin_required():
        return error_response("Admin access required.", 403)

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        if request.method == "DELETE":
            # Preserve products referenced by existing orders.
            cursor.execute(
                "UPDATE products SET is_active = FALSE WHERE product_id = %s",
                (product_id,)
            )
            if cursor.rowcount == 0:
                connection.rollback()
                return error_response("Product not found.", 404)

            connection.commit()
            return jsonify({"message": "Product deactivated."})

        data = request.get_json(silent=True) or {}
        name = str(data.get("name", "")).strip()
        description = str(data.get("description", "")).strip()
        image_url = str(data.get("image_url", "")).strip()

        try:
            price = Decimal(str(data.get("price", "")))
        except (InvalidOperation, ValueError):
            return error_response("Enter a valid product price.", 400)

        if (
            not name or len(name) > 150 or
            not price.is_finite() or price <= 0 or
            len(description) > 500 or len(image_url) > 500
        ):
            return error_response("Invalid product information.", 400)

        cursor.execute(
            """
            UPDATE products
            SET name = %s, description = %s, price = %s, image_url = %s
            WHERE product_id = %s AND is_active = TRUE
            """,
            (name, description, price, image_url, product_id)
        )

        if cursor.rowcount == 0:
            connection.rollback()
            return error_response(
                "Product not found or no changes were made.", 404
            )

        connection.commit()
        return jsonify({"message": "Product updated."})

    except mysql.connector.IntegrityError:
        return error_response("A product with this name already exists.", 409)

    except mysql.connector.Error:
        if connection and connection.is_connected():
            connection.rollback()
        app.logger.exception("Product update failed.")
        return error_response("Unable to manage product.", 500)

    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


@app.route("/api/admin/orders")
def admin_orders():
    if not admin_required():
        return error_response("Admin access required.", 403)

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT order_id, user_id, customer_name, customer_address,
                   customer_phone, total_amount, order_date
            FROM orders
            ORDER BY order_date DESC
            """
        )
        orders = cursor.fetchall()

        for order in orders:
            order["total_amount"] = float(order["total_amount"])
            cursor.execute(
                """
                SELECT product_name, price, quantity
                FROM order_items
                WHERE order_id = %s
                """,
                (order["order_id"],)
            )
            order["items"] = cursor.fetchall()
            for item in order["items"]:
                item["price"] = float(item["price"])

        return jsonify(orders)

    except mysql.connector.Error:
        app.logger.exception("Unable to load admin orders.")
        return error_response("Unable to load orders.", 500)

    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


@app.route("/test-db")
def test_db():
    connection = None
    try:
        connection = get_db_connection()
        return "ShopEase MySQL connection successful!"
    except mysql.connector.Error:
        app.logger.exception("Database connection failed.")
        return "Database connection failed. Check the Flask terminal.", 500
    finally:
        if connection is not None and connection.is_connected():
            connection.close()


@app.route("/place-order", methods=["POST"])
def place_order():
    if "user_id" not in session:
        return error_response("Please log in before placing an order.", 401)

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return error_response("Invalid order data.", 400)

    customer_name = str(data.get("customer_name", "")).strip()
    customer_address = str(data.get("customer_address", "")).strip()
    customer_phone = str(data.get("customer_phone", "")).strip()
    items = data.get("items")

    if not customer_name or not customer_address:
        return error_response("Name and address are required.", 400)

    if (
        len(customer_name) > 100 or len(customer_address) > 500 or
        not customer_phone.isdigit() or len(customer_phone) != 10
    ):
        return error_response("Enter valid customer details.", 400)

    if not isinstance(items, list) or not items or len(items) > 100:
        return error_response("Your cart is empty or invalid.", 400)

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        connection.start_transaction()
        cursor = connection.cursor(dictionary=True)

        validated_items = []
        total_amount = Decimal("0.00")

        for item in items:
            if not isinstance(item, dict):
                connection.rollback()
                return error_response("Invalid product information.", 400)

            name = str(item.get("name", "")).strip()

            try:
                quantity = int(item.get("quantity", 0))
            except (ValueError, TypeError):
                connection.rollback()
                return error_response("Invalid product quantity.", 400)

            if not name or quantity < 1 or quantity > 999:
                connection.rollback()
                return error_response("Invalid product information.", 400)

            cursor.execute(
                """
                SELECT name, price
                FROM products
                WHERE name = %s AND is_active = TRUE
                """,
                (name,)
            )
            product = cursor.fetchone()

            if not product:
                connection.rollback()
                return error_response(
                    f"Product '{name}' is unavailable.", 400
                )

            price = product["price"]
            total_amount += price * quantity

            validated_items.append({
                "product_name": product["name"],
                "price": price,
                "quantity": quantity
            })

        cursor.execute(
            """
            INSERT INTO orders
                (user_id, customer_name, customer_address,
                 customer_phone, total_amount)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                session["user_id"], customer_name, customer_address,
                customer_phone, total_amount
            )
        )
        order_id = cursor.lastrowid

        for item in validated_items:
            cursor.execute(
                """
                INSERT INTO order_items
                    (order_id, product_name, price, quantity)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    order_id, item["product_name"],
                    item["price"], item["quantity"]
                )
            )

        connection.commit()
        return jsonify({
            "message": "Your order has been saved successfully!",
            "order_id": order_id
        }), 201

    except mysql.connector.Error:
        if connection and connection.is_connected():
            connection.rollback()
        app.logger.exception("Unable to save order.")
        return error_response("Unable to save your order. Please try again.", 500)

    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


if __name__ == "__main__":
    app.run(debug=False)
