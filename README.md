# 🤖 Dashboard de Bots

Dashboard web para gestionar y monitorear bots de trading de criptomonedas y búsqueda de gangas en Wallapop.

## Características

- ✅ Gestión de bots (Iniciar/Detener)
- 📊 Estadísticas en tiempo real
- 📋 Visualización de logs
- 🔄 Actualización automática cada 3 segundos

## Bots Soportados

- **Bot de Crypto**: Trading automatizado con IA (DeepSeek)
- **Bot de Wallapop**: Búsqueda automática de gangas

## Despliegue

### Local
```bash
pip install -r requirements.txt
python app.py
```

### Render.com
Este proyecto está configurado para desplegarse automáticamente en Render.com con el archivo `render.yaml`.

## Tecnologías

- Flask
- Python 3.11
- Bootstrap (frontend)
- Gunicorn (production server)
