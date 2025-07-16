
# Octopus Energy Spain - Home Assistant Integration

Integración para conectar tu cuenta de Octopus Energy España con Home Assistant y monitorizar tu consumo, saldo y estado de cargador EV.

## Requisitos
- Home Assistant 2025.1 o superior
- Cuenta activa en Octopus Energy España
- Tarifa de carga EV Octopus Intelligent GO.

## Instalación

### Instalación manual
1. Descarga o clona este repositorio en tu carpeta `custom_components`:
   ```
   custom_components/octopus_spain
   ```
2. Reinicia Home Assistant.

### Instalación con HACS
1. Abre HACS en Home Assistant.
2. Ve a "Integraciones" y haz clic en "Explorar y descargar repositorios".
3. Busca "Octopus Energy Spain" y haz clic en "Descargar".
4. Reinicia Home Assistant.

[![Instalar con HACS](https://img.shields.io/badge/HACS-Instalar-41BDF5?logo=home-assistant&style=for-the-badge)](https://hacs.xyz/)


**Ventajas de HACS:**
- Actualizaciones automáticas y gestión sencilla.
- Integración directa en la interfaz de Home Assistant.

## Configuración
1. Ve a **Ajustes > Dispositivos y servicios** en Home Assistant.
2. Haz clic en **Añadir integración** y busca "Octopus Energy Spain".
3. Introduce tu correo electrónico y contraseña de Octopus Energy España.

## Características
- Sensores de saldo de electricidad, gas y monedero solar
- Estado y control del cargador EV
- Servicios para iniciar/detener carga rápida, refrescar datos y comprobar estado
- Notificaciones automáticas sobre cambios de estado del cargador
- Eventos personalizados para automatizaciones avanzadas
- Compatible con automatizaciones y scripts de Home Assistant

## Servicios disponibles
- `octopus_spain.start_boost`: Inicia la carga rápida en el cargador EV
- `octopus_spain.stop_boost`: Detiene la carga rápida
- `octopus_spain.refresh_charger`: Refresca los datos del cargador
- `octopus_spain.check_charger`: Comprueba el estado del cargador y notifica cambios
- `octopus_spain.car_connected`: Marca el coche como conectado y refresca estado
- `octopus_spain.car_disconnected`: Marca el coche como desconectado

## Soporte
¿Tienes dudas o sugerencias? Abre un issue en [GitHub](https://github.com/tuusuario/ha-octopus-ev-spain/issues) o pregunta en la comunidad de Home Assistant.

## Enlaces útiles
- [Octopus Energy España](https://octopusenergy.es/)
- [Documentación Home Assistant](https://www.home-assistant.io/integrations/)
- Basado en la idea original https://github.com/MiguelAngelLV/ha-octopus-spain
- [HACS](https://hacs.xyz/)

## Licencia
Este proyecto está bajo la licencia MIT.
---
Desarrollado por la comunidad, basado en la idea original de (https://github.com/MiguelAngelLV/ha-octopus-spain). No es una integración oficial de Octopus Energy. Cualquier uso de este código/integración corre bajo la absoluta responsabilidad del usuario (incluyendo errores en el código, iteracción con octopus, consumos mayores de lo previsto en caso de errores ya sean por causa del uso o de errores/mal funcionamiento de la integració, etc). En ningún caso, el desarrollador o la comunidad tiene ninguna responsabilidad en el uso de la misma. Si no estás de acuerdo con este punto no puedes usar la integración. 
