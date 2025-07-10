import os
import pymongo
from pymongo import MongoClient
from dotenv import load_dotenv
from flask_login import UserMixin

# Load environment variables
load_dotenv()

# Initialize MongoDB
mongo_uri = os.getenv('MONGODB_URI') or os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
client = MongoClient(mongo_uri)
db = client[os.getenv('DB_NAME', 'investment_db')]

def calculate_simple_interest(principal, rate, time):
    return (principal * rate * time) / 100

class User(UserMixin):
    def __init__(self, user_data):
        self.user_data = user_data
        self.id = str(user_data['_id'])

# Handle MongoDB authentication error
try:
    # Attempt to fetch a document to trigger authentication
    db.collection_name.find_one()
except pymongo.errors.OperationFailure as e:
    if 'authentication failed' in str(e):
        print("MongoDB authentication failed. Please check your credentials.")
    else:
        print(f"An error occurred: {e}")
    # Additional handling for bad auth error
    if 'bad auth' in str(e):
        print("MongoDB authentication failed: bad auth. Please check your username and password.")
