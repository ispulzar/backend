from fastapi import FastAPI, HTTPException, UploadFile, File, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pymongo import MongoClient
from pydantic import BaseModel
from dotenv import load_dotenv
import pandas as pd
from io import BytesIO
from datetime import datetime
import os
import traceback
from fastapi import FastAPI, HTTPException
from pymongo import MongoClient
from pydantic import BaseModel
from passlib.context import CryptContext
from dotenv import load_dotenv
import os
import jwt
from datetime import datetime, timedelta
from typing import List
import math
from bson import ObjectId

# Cargar variables de entorno
load_dotenv()

# Configuración de conexión a MongoDB
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)

# Acceso a las colecciones de la base de datos
db = client["DROCOLVEN"]
collection = db["mi_coleccion"]
inventario_collection = db["INVENTARIO"]
users_collection = db["USUARIOS"]
usuarios_admin_collection = db["USUARIOSADMINISTRATIVOS"]
ventas_collection = db["VENTAS"]
pedidos_collection = db["PEDIDOS"]
# Configuración de cifrado de contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Inicializar FastAPI
app = FastAPI()
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
# Habilitar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Definir modelos de datos
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
    password: str
    descuento_comercial: float
    descuento_adicional: float

class ProductoInventario(BaseModel):
    codigo: str
    descripcion: str
    dpto: str
    nacional: str
    laboratorio: str
    fv: str
    existencia: int
    precio: float
    cantidad: int
    descuento1: float
    descuento2: float
    descuento3: float

class UserRegister(BaseModel):
    email: str
    password: str
    rif: str
    direccion: str
    telefono: str
    encargado: str
    activo: bool = True
    descuento1: float = 0.0
    descuento2: float = 0.0
    descuento3: float = 0.0
# Modelo para el inicio de sesión
class UserLogin(BaseModel):
    email: str
    password: str

class UserAdminRegister(BaseModel):
    usuario: str
    password: str
    rol: str
    modulos: List[str]

class AdminLogin(BaseModel):
    usuario: str
    password: str

class ProductoPedido(BaseModel):
    id: str
    descripcion: str
    precio: float
    descuento1: float
    descuento2: float
    descuento3: float
    descuento4: float
    cantidad_pedida: int
    subtotal: float

class PedidoResumen(BaseModel):
    cliente: str
    rif: str
    observacion: str
    total: float
    subtotal: float
    productos: list[ProductoPedido]

class PedidoArmado(BaseModel):
    cliente: str
    rif: str
    observacion: str
    total: float
    productos: list[ProductoPedido]

class EstadoPedido(BaseModel):
    nuevo_estado: str

def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(user: dict, expires_delta: timedelta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)):
    to_encode = {
        "id": str(user["_id"]),
        "name": user["rif"],
        "email": user["email"],
        "exp": datetime.utcnow() + expires_delta,
    }
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_admin_access_token(admin: dict, expires_delta: timedelta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)):
    to_encode = {
        "id": str(admin["_id"]),
        "usuario": admin["usuario"],
        "rol": admin.get("rol", "admin"),
        "modulos": admin.get("modulos", []),
        "exp": datetime.utcnow() + expires_delta,
    }
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Funciones de MongoDB
def insert_document(collection, document):
    result = collection.insert_one(document)
    if result.inserted_id:
        return True, document
    return False, "Error al insertar el documento"

def update_document(collection, filter_query, update_data):
    result = collection.update_one(filter_query, {"$set": update_data})
    if result.modified_count:
        return True, "Documento actualizado correctamente"
    return False, "Documento no encontrado o no se realizaron cambios"

def delete_document(collection, filter_query):
    result = collection.delete_one(filter_query)
    if result.deleted_count:
        return True, "Documento eliminado correctamente"
    return False, "Documento no encontrado"

# Rutas CRUD
@app.get("/")
async def root():
    return {"message": "Servidor conectado exitosamente"}

@app.post("/items/", response_model=Item, status_code=201)
async def create_item(item: Item):
    success, result = insert_document(collection, item.dict())
    if success:
        return result
    raise HTTPException(status_code=500, detail=result)

@app.get("/items/{item_id}")
async def read_item(item_id: str):
    item = collection.find_one({"_id": item_id})
    if item:
        item["_id"] = str(item["_id"])
        return item
    raise HTTPException(status_code=404, detail="Ítem no encontrado")

@app.put("/items/{item_id}")
async def update_item(item_id: str, item: Item):
    success, result = update_document(collection, {"_id": item_id}, item.dict())
    if success:
        return {"message": result}
    raise HTTPException(status_code=404, detail=result)

@app.delete("/items/{item_id}")
async def delete_item(item_id: str):
    success, result = delete_document(collection, {"_id": item_id})
    if success:
        return {"message": result}
    raise HTTPException(status_code=404, detail=result)

@app.post("/clientes/", response_model=Client, status_code=201)
async def create_client(client: Client):
    success, result = insert_document(users_collection, client.dict())
    if success:
        return result
    raise HTTPException(status_code=500, detail=result)

@app.get("/clientes/{rif}")
async def read_client(rif: str):
    client = users_collection.find_one({"rif": rif})
    if client:
        client["_id"] = str(client["_id"])
        return client
    raise HTTPException(status_code=404, detail="Cliente no encontrado")

@app.put("/clientes/{rif}")
async def update_client(rif: str, client: Client):
    success, result = update_document(users_collection, {"rif": rif}, client.dict())
    if success:
        return {"message": result}
    raise HTTPException(status_code=404, detail=result)

@app.delete("/clientes/{rif}")
async def delete_client(rif: str):
    success, result = delete_document(users_collection, {"rif": rif})
    if success:
        return {"message": result}
    raise HTTPException(status_code=404, detail=result)

# Endpoint para subir inventario
@app.post("/subir_inventario/")
async def subir_inventario(file: UploadFile = File(...)):
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="El archivo debe ser un Excel (.xlsx o .xls)")
    try:
        contents = await file.read()
        df = pd.read_excel(BytesIO(contents))

        columnas_requeridas = ["codigo", "descripcion", "dpto", "nacional", "laboratorio", "f.v.", "existencia", "precio","descuento1","descuento2","descuento3"]
        if not all(col in df.columns for col in columnas_requeridas):
            raise HTTPException(status_code=400, detail="Faltan columnas requeridas.")

        df = df.rename(columns={
            "codigo": "codigo",
            "descripcion": "descripcion",
            "dpto": "dpto",
            "nacional": "nacional",
            "laboratorio": "laboratorio",
            "f.v.": "fv",
            "existencia": "existencia",
            "precio": "precio",
            "descuento1": "descuento1",
            "descuento2": "descuento2",
            "descuento3": "descuento3",
        })

        df["fv"] = pd.to_datetime(df["fv"], errors="coerce").dt.strftime('%d/%m/%Y')
        # df["cantidad"] = 0
        # df["descuento1"] = 0
        # df["descuento2"] = 0
        df["codigo"] = df["codigo"].astype(str).str.strip()
        productos = df.to_dict(orient="records")

        fecha_subida = datetime.now().strftime("%d-%m-%Y")
        nombre_productos = f"inventario_{fecha_subida}"
        inventario1 = {"nombre_productos":nombre_productos, "inventario": productos}

        inventario_collection.delete_many({})
        inventario_collection.insert_one(inventario1)

        return {"message": f"{len(productos)} productos cargados correctamente dentro de {nombre_productos}."}
    except pd.errors.ExcelFileError:
        raise HTTPException(status_code=400, detail="Archivo Excel no válido.")
    except Exception as e:
        print(f"Error inesperado: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/inventario/")
async def obtener_inventario():
    inventario = inventario_collection.find_one(sort=[('_id', -1)])
    print("Respuesta cruda de MongoDB:", inventario)

    if not inventario:
        return JSONResponse(content={"message": "No se encontró inventario"}, status_code=404)

    inventario["_id"] = str(inventario["_id"])


    inventario_list = inventario["inventario"]
    print("Lista de productos antes de limpiar:", inventario_list)

    for producto in inventario_list:
        for key, value in producto.items():
            if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
                producto[key] = None  # limpiar NaN

            # Extra: limpiar precios tipo string con coma
            if key == "precio" and isinstance(value, str):
                value = value.replace(",", ".")
                try:
                    producto[key] = float(value)
                except ValueError:
                    producto[key] = 0.0  # Si falla la conversión, poner 0

    print("Lista de productos después de limpiar:", inventario_list)

    return JSONResponse(content={"inventario":jsonable_encoder(inventario_list)})

@app.post("/register/")
async def register(user: UserRegister):
    if users_collection.find_one({"email": user.email}):
        raise HTTPException(status_code=400, detail="Correo ya registrado")

    hashed_password = get_password_hash(user.password)
    new_user = user.dict()
    new_user["password"] = hashed_password

    result = users_collection.insert_one(new_user)
    if result.inserted_id:
        return {"message": "Usuario registrado exitosamente"}
    raise HTTPException(status_code=500, detail="Error al registrar el usuario")

@app.post("/login/")
async def login(user: UserLogin):
    db_user = users_collection.find_one({"email": user.email})
    if not db_user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")

    print(f"Contraseña ingresada: {user.password}")
    print(f"Hash almacenado: {db_user['password']}")

    if not verify_password(user.password, db_user["password"]):
        print("Verificación de password fallida")
        raise HTTPException(status_code=401, detail="Contraseña incorrectas")
    else:
        print("Verificación de password exitosa")

    access_token = create_access_token(db_user)
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/register/admin/")
async def register_admin(user: UserAdminRegister):
    print(f"Usuario administrativo a registrar: {user.usuario}")
    if usuarios_admin_collection.find_one({"usuario": user.usuario}):
        raise HTTPException(status_code=400, detail="Usuario ya registrado")

    hashed_password = get_password_hash(user.password)
    new_admin = user.dict()
    print(new_admin)
    new_admin["password"] = hashed_password

    result = usuarios_admin_collection.insert_one(new_admin)
    if result.inserted_id:
        return {"message": "Usuario administrativo registrado exitosamente"}

    raise HTTPException(status_code=500, detail="Error al registrar el usuario administrativo")

@app.get("/modulos/admin/")
async def get_admin_modules():
    config = usuarios_admin_collection.find_one({"_id": "modulos_config"})
    if config and "modulos_disponibles" in config:
        return config["modulos_disponibles"]
    raise HTTPException(status_code=404, detail="No se encontraron módulos disponibles")

@app.post("/login/admin/")
async def admin_login(admin: AdminLogin):
    db_admin = usuarios_admin_collection.find_one({"usuario": admin.usuario})
    if not db_admin:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")

    if not verify_password(admin.password, db_admin["password"]):
        raise HTTPException(status_code=401, detail="Contraseña incorrecta")

    access_token = create_admin_access_token(db_admin)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "modulos": db_admin["modulos"],
        "usuario": db_admin["usuario"]
    }

# Endpoint para obtener la lista de clientes
@app.get("/api/clientes/")
async def obtener_clientes():
    try:
        clientes = list(users_collection.find({}, {"_id": 1, "email": 1, "rif": 1, "encargado": 1}))
        for cliente in clientes:
            cliente["_id"] = str(cliente["_id"])  # Convertir ObjectId a string
        return JSONResponse(content=clientes, status_code=200)
    except Exception as e:
        print(f"Error al obtener clientes: {e}")
        raise HTTPException(status_code=500, detail="Error al obtener la lista de clientes")

# Endpoint para obtener los detalles de un cliente específico por su RIF
@app.get("/api/clientes/{rif}")
async def obtener_cliente_por_rif(rif: str):
    try:
        cliente = users_collection.find_one({"rif": rif})
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        
        cliente["_id"] = str(cliente["_id"])  # Convertir ObjectId a string
        return JSONResponse(content=cliente, status_code=200)
    except Exception as e:
        print(f"Error al obtener cliente por RIF: {e}")
        raise HTTPException(status_code=500, detail="Error al obtener el cliente")

@app.post("/pedidos/")
async def registrar_pedido(resumen: PedidoResumen):
    """
    Endpoint para registrar una pedido en la colección PEDIDOS.
    """
    try:
        # Preparar los datos de la pedido
        pedido = resumen.dict()
        pedido["fecha"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        pedido["estado"] = "pedido_creado"  # Añadir el estado al documento

        # Insertar la pedido en la colección PEDIDOS
        result = db["PEDIDOS"].insert_one(pedido)
        if result.inserted_id:
            return {
                "message": "Venta registrada exitosamente",
                "venta_id": str(result.inserted_id),
                "estado": pedido["estado"],
            }
        else:
            raise HTTPException(status_code=500, detail="Error al registrar la pedido")
    except Exception as e:
        print(f"Error al registrar la pedido: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@app.get("/obtener_pedidos/")
async def obetener_pedidos():
    try:
        pedidos = list(pedidos_collection.find(
            {}
        ))
        print("pedidos recibidos:", pedidos)
        for pedido in pedidos:
            pedido["_id"] = str(pedido["_id"])  # Convertir ObjectId a string

        return JSONResponse(content=pedidos, status_code=200)
    except Exception as e:
        print(f"Error al obtener ventas: {e}")
        raise HTTPException(status_code=500, detail="Error al obtener la lista de pedidos")

@app.post("/pedidos/armados/")
async def registrar_pedido_armado(resumen: PedidoArmado):
    """
    Endpoint para registrar un pedido armado en la colección PEDIDOS_ARMADOS.
    """
    try:
        # Preparar los datos del pedido
        pedido = resumen.dict()
        pedido["fecha_armado"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Insertar el pedido en la colección PEDIDOS_ARMADOS
        result = db["PEDIDOS_ARMADOS"].insert_one(pedido)
        if result.inserted_id:
            return {
                "message": "Pedido armado registrado exitosamente",
                "pedido_id": str(result.inserted_id),
                "cliente": resumen.cliente,
                "total": resumen.total,
            }
        else:
            raise HTTPException(status_code=500, detail="Error al registrar el pedido armado")
    except Exception as e:
        print(f"Error al registrar el pedido armado: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@app.put("/pedidos/actualizar_estado/{pedido_id}")
async def actualizar_estado_pedido(pedido_id: str, estado: EstadoPedido):
    """
    Endpoint para actualizar el estado de un pedido en la colección PEDIDOS.
    """
    print(f"Pedido ID: {pedido_id}, Nuevo estado: {estado.nuevo_estado}")
    try:
        # Convertir el ID del pedido a ObjectId
        pedido_object_id = ObjectId(pedido_id)

        # Actualizar el estado del pedido
        result = db["PEDIDOS"].update_one(
            {"_id": pedido_object_id},
            {"$set": {"estado": estado.nuevo_estado}}
        )

        if result.modified_count:
            return {"message": f"Estado del pedido actualizado a {estado.nuevo_estado}"}
        else:
            raise HTTPException(status_code=404, detail="Pedido no encontrado o no se realizaron cambios")
    except Exception as e:
        print(f"Error al actualizar el estado del pedido: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")