from typing import List, Dict
from langchain_core.tools import tool
from typing import Optional
import requests

import os
import tempfile

API_EASY_CONTACT="3HEfwgZ9EQoRLJrkmCtUf4rY"

BASE_RESPONSE_URL = "https://easycontact.top/api/v1/accounts/{account_id}/conversations/{conversation_id}/messages"

from catalogo_agropartners import portafolio_agropartners_2025


# 1. Saludo inicial
@tool
def saludo_inicial(nombre_cliente: str = None) -> str:
    """
    Envía un mensaje de bienvenida automático en WhatsApp y Web.
    """
    if nombre_cliente:
        return f"👋 ¡Hola {nombre_cliente}! Bienvenido a AgroPartners. ¿En qué podemos ayudarte hoy?"
    return "👋 ¡Hola! Bienvenido a AgroPartners. ¿En qué podemos ayudarte hoy?"


# 2. Recopilación de datos
@tool
def recopilar_datos(nombre: str = None, ciudad: str = None, zona: str = None, cultivo: str = None) -> str:
    """
    Captura dinámica de nombre, ciudad, zona y cultivo.
    """
    if all([nombre, ciudad, zona, cultivo]):
        return f"✅ Datos registrados: Nombre: {nombre}, Ciudad: {ciudad}, Zona: {zona}, Cultivo: {cultivo}."
    return "Por favor proporcione nombre, ciudad, zona y cultivo para continuar."


# 2.1 Información de la empresa
@tool
def info_empresa() -> str:
    """
    Devuelve datos generales de la empresa: horarios, direcciones, etc.
    """
    return (
        "ℹ️ AgroPartners\n"
        "📍 Dirección: Av. Principal #123, Santa Cruz\n"
        "🕒 Horarios: Lunes a Viernes 8:00 - 18:00, Sábado 8:00 - 13:00\n"
        "📞 Tel: +591 700-00000\n"
        "🌐 www.agropartners.com"
    )


# 3. Presentación de catálogo
@tool
def consult_code_catalog() -> str:
    """
    Devuelve los productos del catálogo de AgroPartners con su código, nombre, marca y modelo.
    """
    if not portafolio_agropartners_2025:
        return "⚠️ Aún no tengo artículos en el catálogo."

    lista = "\n".join([
        f"- Código: {item['codigo']} | {item['nombre']} | Marca: {item['marca']} | Modelo: {item['modelo']}"
        for item in portafolio_agropartners_2025
    ])
    return f"📑 Catálogo de AgroPartners:\n{lista}"


@tool
def send_image_catalog(codigo: str, account_id: str, conversation_id: str, access_token: str) -> str:
    """
    Busca un producto por su código y envía la imagen al usuario mediante la API.
    """
    codigo = codigo.strip().lower()
    item = next(
        (prod for prod in portafolio_agropartners_2025 if prod["codigo"].lower() == codigo),
        None
    )

    if not item:
        return "❌ Lo siento, no pude encontrar la imagen que solicitas. Si necesitas información de otro artículo, coméntamelo por favor."

    success = send_file(account_id, conversation_id, item["imagen_url"], access_token)

    if success:
        return f"🖼️ Encontré la foto de **{item['nombre']}**. Si necesitas más información házmelo saber."
    else:
        return f"❌ Lo siento, pero tuve problemas al compartir la imagen de **{item['nombre']}**. Si necesitas información de otro artículo, coméntamelo por favor."

# 4. Armado de carrito
@tool
def armar_carrito(productos: List[str], cantidades: List[int]) -> str:
    """
    Construye un carrito en base a productos y cantidades seleccionadas.
    """
    if len(productos) != len(cantidades):
        return "⚠️ Error: la cantidad de productos y cantidades no coincide."
    carrito = "\n".join([f"- {p}: {c} unidades" for p, c in zip(productos, cantidades)])
    return f"🛒 Tu carrito:\n{carrito}"


# 5. Validación de stock y precios (simulado)
@tool
def validar_stock_precios(codigo: str, cantidad: int) -> str:
    """
    Consulta de disponibilidad de inventario (simulada) y devuelve precio fijo.
    """
    item = next(
        (prod for prod in portafolio_agropartners_2025 if prod["codigo"].lower() == codigo.lower()),
        None
    )
    if not item:
        return f"❌ No encontré el producto con código {codigo}."
    return f"✅ {cantidad} unidades de {item['nombre']} disponibles. Precio unitario: {item.get('precio', '50 Bs')} (simulado)."


# 7. Generación de cotización (simulada)
@tool
def generar_cotizacion(productos: List[str], cantidades: List[int], cliente: str) -> str:
    """
    Genera un documento PDF de cotización (simulada).
    """
    total = sum([c * 50 for c in cantidades])  # precio fijo simulado
    return f"📄 Cotización generada para {cliente}. Total: {total} Bs. Se enviará en PDF."


# 8. Envío de cotización
@tool
def enviar_cotizacion(email: str) -> str:
    """
    Envía la cotización al cliente (simulado).
    """
    return f"✉️ Cotización enviada al correo {email}."


# 9. Aceptación de cotización
@tool
def aceptar_cotizacion(confirmacion: str) -> str:
    """
    Cliente confirma la cotización.
    """
    if confirmacion.lower() == "sí":
        return "✅ Cotización aceptada. Procedemos al pago."
    return "❌ Cotización rechazada."


# 10. Pasarela de pago (simulada)
@tool
def generar_qr_pago(monto: float) -> str:
    """
    Genera un QR de pago (simulado).
    """
    return f"💳 Aquí tienes tu QR para pagar {monto} Bs: www.agropartners.com/pago/qr/{int(monto)}"


# 11. Cobro y confirmación (simulada)
@tool
def confirmar_pago(transaccion_id: str) -> str:
    """
    Procesa y confirma un pago en tiempo real (simulado).
    """
    return f"✅ Pago confirmado. Transacción {transaccion_id} registrada."


# 12. Confirmación final de orden
@tool
def confirmar_orden(cliente: str, productos: List[str], cantidades: List[int]) -> str:
    """
    Envía confirmación de orden y estado de entrega.
    """
    lista = "\n".join([f"- {p}: {c} unidades" for p, c in zip(productos, cantidades)])
    return f"📦 {cliente}, tu orden fue confirmada:\n{lista}\nEstado: En preparación. 🚚"

# 13. envío de pdf catálogo

@tool
def send_pdf_catalog(account_id: str, conversation_id: str, access_token: str) -> str:
    """
    Envía el catálogo PDF completo al usuario mediante EasyContact.
    """
    pdf_url = "https://drive.google.com/file/d/1Qdh9QTzN91EmdCXcYYxhuVW620DJaTTi/view?usp=drive_link"

    response_url = BASE_RESPONSE_URL.format(account_id=account_id, conversation_id=conversation_id)
    headers = {
        "api_access_token": access_token,
        "Content-type": "application/json"
    }

    response_body = {
        "content": pdf_url,
        "message_type": "outgoing",
        "content_type": "file"
    }

    r = requests.post(response_url, headers=headers, json=response_body)
    if r.status_code == 200:
        return "📄 Te envié el catálogo completo de productos."
    else:
        return "❌ No pude enviarte el catálogo, intenta más tarde."


def send_file(account_id: str, conversation_id: str, file_url: str, access_token: str) -> bool:
    """
    Descarga la imagen desde file_url y la envía a la conversación mediante la API de Easy Contact.
    """
    try:
        # Descargar el archivo temporalmente
        response = requests.get(file_url, stream=True)
        response.raise_for_status()
        
        mime_type = response.headers.get("content-type", "image/png")
        ext = mime_type.split("/")[-1] if "/" in mime_type else "png"

        with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as tmp_file:
            for chunk in response.iter_content(chunk_size=8192):
                tmp_file.write(chunk)
            tmp_file_path = tmp_file.name

        # Preparar form-data
        files = {"attachments[]": (os.path.basename(tmp_file_path), open(tmp_file_path, "rb"), mime_type)}
        data = {
            "message_type": "outgoing",
            "content_type": "text",
            "content": ""
        }

        url = f"{API_EASY_CONTACT}/api/v1/accounts/{account_id}/conversations/{conversation_id}/messages"
        headers = {"api_access_token": access_token}

        resp = requests.post(url, files=files, data=data, headers=headers)
        resp.raise_for_status()

        os.remove(tmp_file_path)
        return True

    except Exception as e:
        print("Error enviando el archivo:", e)
        return False