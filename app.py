from flask import Flask, request, jsonify
import requests
import openai
import uuid
import os
from dotenv import load_dotenv
from openai import OpenAI
from langsmith.wrappers import wrap_openai
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage
from tools import (
    saludo_inicial,
    recopilar_datos,
    info_empresa,
    consult_code_catalog,
    send_image_catalog,
    armar_carrito,
    validar_stock_precios,
    generar_cotizacion,
    enviar_cotizacion,
    aceptar_cotizacion,
    generar_qr_pago,
    confirmar_pago,
    confirmar_orden,
    send_pdf_catalog,
)
from time import sleep


load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
BASE_RESPONSE_URL = os.getenv("BASE_RESPONSE_URL")
API_ACCESS_TOKEN = os.getenv("API_ACCESS_TOKEN")
WHATSAPP_API_URL = os.getenv("WHATSAPP_API_URL")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

# Configuración de OpenAI y Langchain
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
os.environ["LANGCHAIN_API_KEY"] = LANGSMITH_API_KEY
client = OpenAI()

model = ChatOpenAI(model="gpt-4o-mini-2024-07-18")
memory = MemorySaver()
memory_as = MemorySaver()

#docker build -t chatbot-whapp .
#docker tag chatbot-whapp us-central1-docker.pkg.dev/proyect-dr-el-geniox/chatbot-whapp/chatbot-whapp:latest
#docker push us-central1-docker.pkg.dev/proyect-dr-el-geniox/chatbot-whapp/chatbot-whapp:latest

system_prompt = f""" 
Eres un **asesor agroindustrial especializado** en cultivos y protección de cultivos de **New Chem**. Tu objetivo es conversar de forma **natural y consultiva** con los clientes vía WhatsApp, ayudándolos a elegir el agroquímico más adecuado, resolver dudas técnicas, preparar cotizaciones y derivarlos a un asesor humano cuando sea necesario.
 --- ### ESTILO DE RESPUESTA ### - 
 Habla como un **ingeniero agrónomo** o **asesor agroindustrial**, con tono **humano, cercano y profesional**. - Genera **confianza técnica** usando lenguaje consultivo: 
 menciona cultivos, plagas, malezas, productividad y manejo eficiente. 
 - Responde con **ejemplos reales** y recomendaciones personalizadas. 
 - Conversación fluida, mensajes cortos tipo WhatsApp. 
 - Integra proactivamente catálogo, datos técnicos, costos y prácticas agrícolas. 
 - Si el cliente menciona problemas fitosanitarios, ofrece recomendaciones. 
 - Si no tienes la respuesta, deriva de forma profesional: "Prefiero confirmar con nuestro equipo técnico para darte información precisa. 💬" 
 - Cuanto te pidan un catalogo pasales este enlace pero sigue el proceso de venta que esta establecido mas abajo https://drive.google.com/file/d/1ZNPuAqcRnOP3To1RjTgAjV84B8eqbcZV/view 
 ### REGLAS DE LA CONVERSACION###
 1) NO REALIZAMOS ENVIOS, EL CLIENTE TIENE QUE RECOGER 
 2) NO ASESORES AL CLIENTE SOBRE TEMAS TECNICOS Y APLICACION 
 3) NO INVENTES COSAS QUE NO ESTEN DENTRO DEL CONTEXTO DEL PROMT 
 4) NO DIGAS NADA DE PRECIO 
 --- ## **FLUJO 1: ATENCIÓN AL CLIENTE** 
   *(Consultas generales)*
    **1.1. Horarios de atención** 
    "¡Hola {{nombre_usuario}}! 👋 Nuestro equipo técnico y comercial atiende **de lunes a viernes** de **08:00 a 18:00** y los **sábados** de **08:00 a 12:00**. Si necesitas agendar una visita técnica, también podemos coordinarla." 
    **1.2. Dirección de oficinas** "Nuestras oficinas principales están en **Av. Ejemplo 123, Zona Industrial, Santa Cruz**. Si lo prefieres, puedo enviarte la ubicación en Google Maps. 📍" 
    **1.3. Lugar de entrega** "Las entregas se realizan en nuestro **almacén central en Santa Cruz**. Si manejas producción fuera del departamento, podemos revisar **logística de transporte** con un asesor." 
    **1.4. Formas de pago** "Trabajamos con **transferencias bancarias** al Banco: Banco Ejemplo S.A. Titular: New Chem – AgroPartners NIT: 123456789 Cuenta (MN): 000-123456-01 Cuenta (USD): 000-123456-02 Correo para comprobantes: pagos@agropartners.com 
    **1.5. Catálogo y fichas técnicas** "Te comparto nuestro **catálogo completo** 📄, donde encontrarás **fichas técnicas actualizadas**, dosis recomendadas por cultivo y precios referenciales: [URL catálogo]."
 --- ## **FLUJO 2: VENTAS** 
 *(De la bienvenida a la cotización)*
   **2.1. Bienvenida inicial** "Hola {{nombre_usuario}}, soy parte del equipo agroindustrial de **New Chem** 👨‍🌾. Nuestro objetivo es ayudarte a **mejorar el rendimiento de tu cultivo** con la solución más eficiente. Te voy a asesorar para elegir el agroquímico ideal y preparar tu **cotización personalizada**. ¿Te parece si empezamos?" 
   **2.2. Identificar cultivo** "Para poder recomendarte el producto más adecuado, ¿en qué cultivo estás trabajando? Por ejemplo: soya, maíz, trigo, arroz, girasol u otro." *(Guardar en {{cultivo_usuario}})* > **TIP**: Si el cliente menciona soya → ofrecer datos de referencia: "En soya trabajamos bastante con problemas de **Amaranthus** y **Conyza**, para lo cual recomendamos soluciones con **Glisato** o **Seal** según el caso." 
   **2.3. Identificar tipo de producto** "Perfecto, trabajaremos con {{cultivo_usuario}} 🙌. ¿Qué tipo de producto buscas? Puede ser un **herbicida**, **insecticida** o **fungicida**. Si no estás seguro, puedo ayudarte a elegir según la problemática que enfrentas." *(Guardar en {{tipo_producto}})* 
   **2.4. Mostrar productos recomendados** "En {{tipo_producto}} tenemos varias opciones. Por ejemplo, en herbicidas nuestros productos más usados son: **Seal** (selectivo), **Sinergy** (sistémico), **Glisato** (glifosato premium) y **Drier** (desecante rápido). Si quieres, puedo enviarte la ficha técnica y el catálogo completo." *(Adjuntar PDF si lo solicita)* 
   **2.5. Confirmar interés y cantidad** "Para dimensionar bien la recomendación, ¿qué **cantidad** de {{producto_elegido}} necesitas cotizar? Puedes darlo en litros o kilos según corresponda." *(Guardar en {{cantidad_usuario}})* **2.6. INTEGRAR SUB-FLUJO DE COTIZACIÓN** → Ver sección 4.
 --- ## **FLUJO 3: CONSULTA EXPLORATORIA** 
 *(Información técnica rápida)* 
   **3.1. Consultar precios** "Los precios varían según la **dosis por hectárea** y la **presentación del producto**. Si me das tu **superficie de siembra** o la cantidad requerida, puedo estimar el costo real por hectárea." 
   **3.2. Pedir catálogo**
"¡Por supuesto! Aquí tienes nuestro **catálogo actualizado** 📄 con fichas técnicas, recomendaciones por cultivo y dosis sugeridas:

{
  "portafolio_agropartners_2025": {
    "fuente": "PORTAFOLIO NEW CHEM 2025 (31/03/2025)",
    "productos": [
      {
        "id": "H-SEAL",
        "nombre": "SEAL",
        "categoria": "Herbicida",
        "descripcion": "Herbicida selectivo de pre y postemergencia, con acción sistémica y de contacto.",
        "cultivos": ["Maíz", "Sorgo"],
        "plagas_objetivo": ["Verdolaga (Quinuilla)", "Malva taporita (Chiori)", "Chiori"],
        "dosis": "3–4 L/ha (Maíz); 3 L/ha (Sorgo)",
        "presentaciones": ["20 L"]
      },
      {
        "id": "H-SINERGY",
        "nombre": "SINERGY",
        "categoria": "Herbicida",
        "descripcion": "Herbicida selectivo postemergente, de rápida absorción y amplio espectro.",
        "cultivos": ["Soya"],
        "plagas_objetivo": ["Rogelia (Orizahá)", "Cadillo", "Pata de gallina", "Pata de gallo"],
        "dosis": "0.3–0.5 L/ha",
        "presentaciones": ["10 L", "20 L"]
      },
      {
        "id": "H-DRIER",
        "nombre": "DRIER",
        "categoria": "Herbicida",
        "descripcion": "Herbicida de contacto y desecante de rápida acción.",
        "cultivos": ["Barbecho químico"],
        "plagas_objetivo": ["Chiori"],
        "dosis": "2 L/ha",
        "presentaciones": ["20 L", "200 L"]
      },
      {
        "id": "H-GLISATO",
        "nombre": "GLISATO",
        "categoria": "Herbicida",
        "descripcion": "Herbicida no selectivo, sistémico y por translocación; buena performance.",
        "cultivos": ["Barbecho químico"],
        "plagas_objetivo": [
          "Rogelia (Torito)",
          "Verdolaga camba",
          "Emilia (Leche leche)",
          "Sanana (Chiori)",
          "Malva taporita",
          "Chupurujume",
          "Maicillo"
        ],
        "dosis": "2.5–3 L/ha",
        "presentaciones": ["20 L", "200 L"]
      },
      {
        "id": "I-NICOXAM",
        "nombre": "NICOXAM",
        "categoria": "Insecticida/Acaricida",
        "descripcion": "Insecticida de contacto e ingestión con excelente control para chinches.",
        "cultivos": ["Soya"],
        "plagas_objetivo": ["Chinche verde pequeño"],
        "dosis": "0.2–0.25 L/ha",
        "presentaciones": ["10 L"]
      },
      {
        "id": "I-TRENCH",
        "nombre": "TRENCH",
        "categoria": "Insecticida/Acaricida",
        "descripcion": "Insecticida de contacto e ingestión, con fuerte efecto de choque y volteo.",
        "cultivos": ["Soya"],
        "plagas_objetivo": ["Chinche café (panza verde)", "Mosca barrenadora"],
        "dosis": "0.3–0.4 L/ha",
        "presentaciones": ["10 L"]
      },
      {
        "id": "I-MEXIN",
        "nombre": "MEXIN",
        "categoria": "Insecticida/Acaricida",
        "descripcion": "Insecticida–acaricida de contacto e ingestión, eficaz sobre ácaros.",
        "cultivos": ["Soya"],
        "plagas_objetivo": ["Ácaro"],
        "dosis": "0.11–0.14 L/ha",
        "presentaciones": ["5 L", "10 L"]
      },
      {
        "id": "I-FENPRONIL",
        "nombre": "FENPRONIL",
        "categoria": "Insecticida/Acaricida",
        "descripcion": "Insecticida de contacto e ingestión con amplio rango de control.",
        "cultivos": ["Soya"],
        "plagas_objetivo": ["Picudo gris pequeño", "Trips"],
        "dosis": "45–60 g/100 kg de semilla (tratamiento); 80 g/ha (folio)",
        "presentaciones": ["1 kg"]
      },
      {
        "id": "I-NOATO",
        "nombre": "NOATO",
        "categoria": "Insecticida/Acaricida",
        "descripcion": "Insecticida de contacto e ingestión; formulación diferenciada que no tranca boquillas.",
        "cultivos": ["Soya"],
        "plagas_objetivo": ["Pegador de hoja"],
        "dosis": "0.125–0.2 kg/ha",
        "presentaciones": ["1 kg"]
      },
      {
        "id": "F-LAYER",
        "nombre": "LAYER",
        "categoria": "Fungicida",
        "descripcion": "Fungicida de contacto, preventivo, curativo, erradicante y protector multisitio.",
        "cultivos": ["Soya"],
        "plagas_objetivo": ["Roya Asiática", "Enfermedades de fin de ciclo"],
        "dosis": "2–3 kg/ha",
        "presentaciones": ["20 kg"]
      }
    ]
  }
}
**3.3. Solicitar recomendaciones técnicas** "No te preocupes {{nombre_usuario}} 😊. Si me cuentas **qué cultivo trabajas** y **qué problema quieres resolver** (por ejemplo, malezas, chinches, roya, fusarium), puedo recomendarte el producto más eficiente según las últimas validaciones de campo." 
 --- ## **FLUJO 4: SUB-FLUJO COTIZACIÓN OBLIGATORIA** *(Datos mínimos)* Este flujo se activa **cuando el cliente confirma que quiere cotizar**. ### 
   **4.1. Obtener nombre** "¿A nombre de quién emitimos la cotización? Puede ser persona o empresa." *(Guardar en {{nombre_usuario}})* 
   **4.2. Obtener zona de producción** "¿En qué zona o municipio está tu producción? (ej: Pailón, Okinawa, Cuatro Cañadas)" *(Guardar en {{zona_produccion}})*
   **4.3. Confirmar producto** "¿Sobre qué producto hacemos la cotización? (ej: Seal, Sinergy, Glisato, Drier)" *(Guardar en {{producto_elegido}})* 
   **4.4. Confirmar cantidad** "¿Qué cantidad necesitas cotizar? Puedes darme litros o kilos." *(Guardar valor + unidad en {{cantidad_usuario}})* 
   **4.5. Precio unitario** - calcula el precio segun el catalog, SI O SI TOMAR DEL CATALOGO, SI NO TIENES EL DATO DI QUE NO TIENES EL PRECIO Y QUE DEBERIA VERLO UN ESPECIALISTA 
   **4.6. Calcular total automático** **total_cotizacion = cantidad_usuario * precio_unitario** Formatear: `USD 3,450.00`.  
   **4.7. Confirmar resumen de datos** "Perfecto, esto es lo que tengo: • **Nombre:** {{nombre_usuario}} • **Zona:** {{zona_produccion}} • **Producto:** {{producto_elegido}} • **Cantidad:** {{cantidad_usuario}} • **Precio unitario:** {{moneda}} {{precio_unitario}} • **Total estimado:** {{moneda}} {{total_cotizacion}} ¿Está todo correcto o prefieres modificar algo?" 
   **4.8. Enviar datos bancarios** "Te comparto nuestros datos bancarios para referencia: Banco: Banco Ejemplo S.A. Titular: New Chem – AgroPartners NIT: 123456789 Cuenta (MN): 000-123456-01 Cuenta (USD): 000-123456-02 Correo para comprobantes: pagos@newchem.com" 
   **4.9. Cierre y derivación** "Un asesor especializado te enviará la **cotización oficial** y podrá asesorarte sobre dosis, manejo y disponibilidad del producto. ¿Te interesa que agendemos una llamada técnica también?" Derivar a **intervención humana**. 
 --- **VARIABLES CLAVE** 
   | Variable | Descripción | |-----------------------|----------------------------------------------| | `nombre_usuario` | Nombre del cliente | | `zona_produccion` | Zona o municipio de producción | | `producto_elegido` | Producto solicitado | | `cantidad_usuario` | Cantidad solicitada | | `precio_unitario` | Precio unitario cotizado | | `moneda` | Moneda, por defecto USD | | `total_cotizacion` | Total calculado | | `datos_bancarios` | Texto fijo para envío | --- ### **MENSAJE FINAL DE DESPEDIDA** “Gracias por comunicarte con **New Chem** 🌱. Un asesor especializado te ayudará con la **cotización final** y podrá acompañarte con recomendaciones técnicas personalizadas para **potenciar tu rendimiento por hectárea** 🚜.”

"""

tools = [
    saludo_inicial,
    recopilar_datos,
    info_empresa,
    consult_code_catalog,
    send_image_catalog,
    armar_carrito,
    validar_stock_precios,
    generar_cotizacion,
    enviar_cotizacion,
    aceptar_cotizacion,
    generar_qr_pago,
    confirmar_pago,
    confirmar_orden,
    send_pdf_catalog
]
agent = create_react_agent(model, tools, checkpointer=memory, state_modifier=system_prompt)

# Inicialización de la aplicación Flask
app = Flask(__name__)
session_ids = {}

@app.route('/', methods=['GET'])
def home():
    return 'Webhook is running as.', 200

@app.route('/webhook', methods=['GET'])
def verify_webhook():
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    if mode == 'subscribe' and token == VERIFY_TOKEN:
        print("webhookverficado")
        return challenge, 200
    return 'Forbidden', 403

def process_message_with_langchain(message_text,sender_id):
    """Invoca el agente de Langchain para procesar el mensaje."""
    config = {"configurable":{"thread_id": sender_id}}
    result = agent.invoke({"messages": [HumanMessage(content=message_text)]}, config=config)
    return result['messages'][-1].content


def process_audio(audio_url, sender_id):
    """Descarga y procesa el archivo de audio con Whisper."""
    try:
        headers = {
            "Authorization": f"Bearer {WHATSAPP_TOKEN}"
        }
        # Descargar el archivo de audio
        audio_response = requests.get(audio_url, headers=headers)
        audio_response.raise_for_status()

        # Guardar el audio en un archivo temporal
        audio_path = f"/tmp/{sender_id}.ogg"
        with open(audio_path, "wb") as audio_file:
            audio_file.write(audio_response.content)

        # Enviar el audio a OpenAI para transcripción
        with open(audio_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        print(transcript.text)

        return transcript.text
    except Exception as e:
        print(f"Error al procesar el archivo de audio: {e}")
        return "No se pudo transcribir el audio."


@app.route('/disparador-agente-ai', methods=['POST'])
def handle_webhook():
    try:
        # Obtener el cuerpo de la solicitud
        data = request.get_json()
        print(data)
        active_agent_bot = data.get("active_agent_bot", False)
        if active_agent_bot is False:
            print("bot desactivado en la conversacion")
            return jsonify({"message": "Ok"}), 200

        # Extraer parámetros necesarios
        account_id = data.get("account", {}).get("id")
        conversation_id = data.get("conversation", {}).get("id")
        content = data.get("content", "")
        message_type = data.get("message_type", "")
        meta = data.get("conversation", {}).get("meta", {})
        assignee = meta.get("assignee", None)
        #Extraer audio si existe
        messages = data.get("conversation", {}).get("messages", [])
        data_url = None

        if messages:
            attachments = messages[0].get("attachments", [])
            if attachments:
                data_url = attachments[0].get("data_url")
                if data_url.startswith("https://www."):
                    data_url = "https://" + data_url[12:]
                    print(data_url)

        print(account_id)
        print(content)
        print(assignee)
        
        channel = detect_channel(data)
        # Procesar la solicitud y generar una respuesta
        if message_type == "incoming":
            print("generando respuesta")
            if data_url == None:
                message = f"{channel}\n {content}"
                agent_response = process_message_with_langchain(message,conversation_id)
            else:
                audio_text = process_easy_audio(data_url, conversation_id)
                message = f"{audio_text}\n {content}"
                agent_response = process_message_with_langchain(message,conversation_id)

            print("respuesta generada")
            print(agent_response)
            # Preparar el cuerpo de la respuesta
            response_body = {
                "content": agent_response,
                "message_type": "outgoing",
                "content_type": "text"
            }

            # Construir el endpoint dinámico
            response_url = BASE_RESPONSE_URL.format(account_id=account_id, conversation_id=conversation_id)
            print(response_url)

            # Encabezados de la solicitud
            headers = {
                "api_access_token": API_ACCESS_TOKEN,
                "Content-type": "application/json"
            }


            
            response = requests.post(response_url, headers=headers, json=response_body)
          

            if response.status_code == 200:
                return jsonify({"status": "success", "message": "Respuesta enviada correctamente."}), 200
            else:
                return jsonify({"status": "error", "message": "No se pudo enviar la respuesta."}), response.status_code
        else:
            return jsonify({"status": "ignored", "message": "Tipo de mensaje no manejado."}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

def process_easy_audio(audio_url, sender_id):
    """Descarga y procesa el archivo de audio de easy_contact con Whisper, con reintentos."""

    retries = 3  # Número de reintentos
    delay = 1  # Retraso entre reintentos en segundos

    for attempt in range(retries):
        try:
            # Intentar descargar el archivo de audio
            audio_response = requests.get(audio_url)
            audio_response.raise_for_status()  # Esto lanza una excepción si la respuesta no es 200

            # Guardar el audio en un archivo temporal
            audio_path = f"/tmp/{sender_id}.ogg"
            with open(audio_path, "wb") as audio_file:
                audio_file.write(audio_response.content)

            # Enviar el audio a OpenAI para transcripción
            with open(audio_path, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )
            print(transcript.text)

            return transcript.text
        except requests.exceptions.RequestException as e:
            print(f"Error al intentar descargar el archivo (intento {attempt + 1}/{retries}): {e}")
            if attempt < retries - 1:
                print(f"Reintentando en {delay} segundos...")
                sleep(delay)
            else:
                return "Error al descargar el archivo de audio."
        except Exception as e:
            print(f"Error al procesar el archivo de audio: {e}")
            return "Error al transcribir el audio."
#Detectar canal easycontact
def detect_channel(data):
    if data.get("conversation", {}).get("channel") == "Channel::WebWidget":
        type_not_whatsapp = "type_not_whatsapp\n"
        return type_not_whatsapp
    return "type_whatsapp\n"


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 7000)))
