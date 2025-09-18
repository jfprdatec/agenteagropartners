# Imagen base de Python 3.9 o superior
FROM python:3.9-slim

# Establecer el directorio de trabajo en el contenedor
WORKDIR /app

# Copiar los archivos necesarios al contenedor
COPY . /app

# Instalar las dependencias del proyecto
RUN pip install --no-cache-dir -r requirements.txt

# Exponer el puerto 7000
EXPOSE 7000

# Comando para ejecutar la aplicación
CMD ["python", "app.py"]