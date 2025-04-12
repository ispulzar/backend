from pymongo import MongoClient
import os

MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["DROCOLVEN"]

users_collection = db["USUARIOS"]
clients_collection = db["CLIENTES"]
inventario_collection = db["INVENTARIO"]
collection = db["mi_coleccion"]