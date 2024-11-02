from flask import Flask, render_template, request, url_for, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
import logging

# Initialize the Flask application
app = Flask(__name__)

# Configure logging to track application events and errors
logging.basicConfig(filename='app.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Configure the SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventory.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Define the InventoryItem model for the database
class InventoryItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # Inventory item name
    amount = db.Column(db.Integer, nullable=False)     # Amount of the item
    supplier = db.Column(db.String(100), nullable=True) # Supplier name, if any

# Create the database tables
with app.app_context():
    db.create_all()

@app.route("/", methods=["GET", "POST"])
def home():
    """Handle the home page where inventory items are listed and added."""
    logging.info("Accessed home page.")
    if request.method == "POST":
        inventory_name = request.form.get("inventory_name")
        inventory_amount = request.form.get("inventory_amount")

        # Check for missing fields
        if not inventory_name or not inventory_amount:
            logging.error("Missing inventory name or amount.")
            return render_template('index.html', items=[], error="Please provide both an item name and an amount.")

        try:
            # Convert the amount to an integer and create a new inventory item
            inventory_amount = int(inventory_amount)
            new_item = InventoryItem(name=inventory_name, amount=inventory_amount)
            db.session.add(new_item)
            db.session.commit()
            logging.info(f"Added new item: {new_item.name}, Amount: {new_item.amount}")

        except ValueError:
            logging.error("Invalid amount provided.")
            return render_template('index.html', items=[], error="Amount must be a valid integer.")
        except Exception as e:
            logging.error("An unexpected error occurred: %s", str(e))
            return render_template('index.html', items=[], error="An error occurred: " + str(e))

    # Retrieve all inventory items to display
    items = InventoryItem.query.all()
    return render_template('index.html', items=items)

@app.route("/delete/<int:inventory_id>", methods=["POST"])
def delete_inventory(inventory_id):
    """Delete an inventory item by its ID."""
    logging.info("Attempting to delete item with ID: %d", inventory_id)
    item = InventoryItem.query.get(inventory_id)
    if item:
        db.session.delete(item)
        db.session.commit()
        logging.info("Deleted item: %s", item.name)
    return redirect(url_for("home"))

@app.route("/edit/<int:inventory_id>", methods=["GET", "POST"])
def edit_inventory(inventory_id):
    """Edit an existing inventory item."""
    item_to_edit = InventoryItem.query.get(inventory_id)
    if request.method == "POST":
        new_name = request.form.get("inventory_name")
        new_amount = request.form.get("new_amount", type=int)

        # Check for missing fields
        if not new_name or new_amount is None:
            logging.error("Missing name or amount for editing.")
            return "Error: Please provide both a name and an amount.", 400

        # Update item details and commit to the database
        item_to_edit.name = new_name
        item_to_edit.amount = new_amount
        db.session.commit()
        logging.info("Updated item ID %d: Name: %s, Amount: %d", inventory_id, new_name, new_amount)
        return redirect(url_for("home"))

    return render_template('edit.html', item=item_to_edit)

@app.route("/add_supplier/<int:inventory_id>", methods=["GET", "POST"])
def add_supplier_inventory(inventory_id):
    """Add a supplier to an inventory item."""
    item = InventoryItem.query.get(inventory_id)
    if request.method == "POST":
        new_supplier = request.form.get("supplier_name")

        # Check for missing supplier name
        if not new_supplier:
            logging.error("Missing supplier name.")
            return "Error: Please provide a supplier's name.", 400

        item.supplier = new_supplier
        db.session.commit()
        logging.info("Added supplier '%s' to item ID %d", new_supplier, inventory_id)
        return redirect(url_for("home"))

    return render_template('add_supplier.html', inventory_id=inventory_id)

# API endpoints
@app.route("/items", methods=["POST"])
def add_item():
    """API endpoint to add a new item."""
    logging.info("Attempting to add a new item via API.")
    data = request.get_json()
    inventory_name = data.get('name')
    inventory_amount = data.get('amount')

    # Check for missing fields
    if not inventory_name or inventory_amount is None:
        logging.error("Missing item name or amount in request.")
        return jsonify({'error': 'Please provide both name and amount.'}), 400

    try:
        inventory_amount = int(inventory_amount)
    except ValueError:
        logging.error("Invalid amount provided in request.")
        return jsonify({'error': 'Amount must be a valid integer.'}), 400

    # Create and save the new item
    new_item = InventoryItem(name=inventory_name, amount=inventory_amount)
    db.session.add(new_item)
    db.session.commit()
    logging.info(f"Added new item via API: {new_item.name}, Amount: {new_item.amount}")
    return jsonify({'id': new_item.id, 'name': new_item.name, 'amount': new_item.amount}), 201

@app.route("/items", methods=["GET"])
def get_items():
    """API endpoint to retrieve all items."""
    items = InventoryItem.query.all()
    return jsonify([{'id': item.id, 'name': item.name, 'amount': item.amount, 'supplier': item.supplier} for item in items])

@app.route("/items/<int:item_id>", methods=["GET"])
def get_item(item_id):
    """API endpoint to retrieve a specific item by ID."""
    item = InventoryItem.query.get(item_id)
    if item:
        return jsonify({'id': item.id, 'name': item.name, 'amount': item.amount, 'supplier': item.supplier})
    return jsonify({'error': 'Item not found'}), 404

@app.route("/items/<int:item_id>", methods=["PUT"])
def update_item(item_id):
    """API endpoint to update an existing item."""
    data = request.get_json()
    item = InventoryItem.query.get(item_id)

    if item:
        item.name = data.get('name', item.name)
        if 'amount' in data:
            try:
                item.amount = int(data['amount'])
            except ValueError:
                return jsonify({'error': 'Amount must be a valid integer.'}), 400
        db.session.commit()
        logging.info("Updated item ID %d: Name: %s, Amount: %d", item_id, item.name, item.amount)
        return jsonify({'id': item.id, 'name': item.name, 'amount': item.amount, 'supplier': item.supplier})
    
    return jsonify({'error': 'Item not found'}), 404

@app.route("/items/<int:item_id>", methods=["DELETE"])
def delete_item(item_id):
    """API endpoint to delete an item by ID."""
    item = InventoryItem.query.get(item_id)
    if item:
        db.session.delete(item)
        db.session.commit()
        logging.info("Deleted item ID %d: Name: %s", item_id, item.name)
        return jsonify({'result': 'Item deleted'}), 204
    
    return jsonify({'error': 'Item not found'}), 404

if __name__ == "__main__":
    # Run the application in debug mode
    app.run(debug=True)
