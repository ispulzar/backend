from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pymongo import MongoClient
from pydantic import BaseModel
from bson import ObjectId
import pandas as pd
from io import BytesIO
import traceback
from datetime import datetime
from auth import router as auth_router, get_current_user, TokenData
from database import collection, clients_collection, inventario_collection
from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

app = FastAPI()

# Configuración CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir rutas de autenticación
app.include_router(auth_router)

# Resto de tus modelos y rutas
class Item(BaseModel):
    name: str
    description: str
    price: float

class Client(BaseModel):
    rif: str
    cliente: str
    direccion: str
    numero: str
    correo: str
    contraseña: str
    descuento_comercial: float
    descuento_adicional: float

class ProductoInventario(BaseModel):
    codigo: str
    descripcion: str
    dpto: str
    importado: str
    laboratorio: str
    fv: str
    existencia: int
    precio: float
    cantidad: int
    descuentoPorCantidad: int
    descuentoLineal: int

# Funciones CRUD
def insert_document(collection, document):
    result = collection.insert_one(document)
    return result.inserted_id is not None

def update_document(collection, filter_query, update_data):
    result = collection.update_one(filter_query, {"$set": update_data})
    return result.modified_count > 0

def delete_document(collection, filter_query):
    result = collection.delete_one(filter_query)
    return result.deleted_count > 0

# Resto de tus endpoints
@app.get("/")
async def root():
    return {"message": "Servidor conectado exitosamente"}

@app.post("/items/", response_model=Item, status_code=201)
async def create_item(item: Item):
    if insert_document(collection, item.dict()):
        return item
    raise HTTPException(status_code=500, detail="Error al crear ítem")

@app.get("/items/{item_id}")
async def read_item(item_id: str):
    item = collection.find_one({"_id": item_id})
    if item:
        item["_id"] = str(item["_id"])
        return item
    raise HTTPException(status_code=404, detail="Ítem no encontrado")

@app.put("/items/{item_id}")
async def update_item(item_id: str, item: Item):
    if update_document(collection, {"_id": item_id}, item.dict()):
        return {"message": "Ítem actualizado correctamente"}
    raise HTTPException(status_code=404, detail="Ítem no encontrado")

@app.delete("/items/{item_id}")
async def delete_item(item_id: str):
    if delete_document(collection, {"_id": item_id}):
        return {"message": "Ítem eliminado correctamente"}
    raise HTTPException(status_code=404, detail="Ítem no encontrado")

@app.post("/clientes/", response_model=Client, status_code=201)
async def create_client(client: Client):
    if insert_document(clients_collection, client.dict()):
        return client
    raise HTTPException(status_code=500, detail="Error al crear cliente")

@app.get("/clientes/{rif}")
async def read_client(rif: str):
    client = clients_collection.find_one({"rif": rif})
    if client:
        client["_id"] = str(client["_id"])
        return client
    raise HTTPException(status_code=404, detail="Cliente no encontrado")

@app.put("/clientes/{rif}")
async def update_client(rif: str, client: Client):
    if update_document(clients_collection, {"rif": rif}, client.dict()):
        return {"message": "Cliente actualizado correctamente"}
    raise HTTPException(status_code=404, detail="Cliente no encontrado")

@app.delete("/clientes/{rif}")
async def delete_client(rif: str):
    if delete_document(clients_collection, {"rif": rif}):
        return {"message": "Cliente eliminado correctamente"}
    raise HTTPException(status_code=404, detail="Cliente no encontrado")

@app.post("/subir_inventario/")
async def subir_inventario(file: UploadFile = File(...)):
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="El archivo debe ser un Excel (.xlsx o .xls)")
    
    try:
        contents = await file.read()
        df = pd.read_excel(BytesIO(contents))
        
        columnas_requeridas = ["codigo", "descripcion", "dpto", "nacional", "laboratorio", "f.v.", "existencia", "precio"]
        if not all(col in df.columns for col in columnas_requeridas):
            raise HTTPException(status_code=400, detail="Faltan columnas requeridas.")
        
        df = df.rename(columns={
            "nacional": "importado",
            "f.v.": "fv"
        })
        
        df["fv"] = pd.to_datetime(df["fv"], errors="coerce").dt.strftime('%d/%m/%Y')
        df["cantidad"] = 0
        df["descuentoPorCantidad"] = 0
        df["descuentoLineal"] = 0
        
        productos = df.to_dict(orient="records")
        fecha_subida = datetime.now().strftime("%d-%m-%Y")
        nombre_productos = f"inventario_{fecha_subida}"
        
        inventario_collection.delete_many({})
        inventario_collection.insert_one({nombre_productos: productos})
        
        return {"message": f"{len(productos)} productos cargados correctamente"}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/inventario/")
async def obtener_inventario():
    ultimo_inventario = inventario_collection.find_one(sort=[('_id', -1)])
    if not ultimo_inventario:
        return JSONResponse(content={"message": "No se encontró inventario"}, status_code=404)
    
    ultimo_inventario["_id"] = str(ultimo_inventario["_id"])
    return JSONResponse(content=jsonable_encoder(ultimo_inventario))

@app.get("/users/me")
async def read_users_me(current_user: TokenData = Depends(get_current_user)):
    return {"email": current_user.email}