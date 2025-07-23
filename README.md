# Octopus Energy España - Integración Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![GitHub release](https://img.shields.io/github/release/lockevod/ha-octopus-ev-spain.svg)](https://github.com/lockevod/ha-octopus-ev-spain/releases)
[![GitHub](https://img.shields.io/github/license/lockevod/ha-octopus-ev-spain.svg)](LICENSE)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://github.com/lockevod/ha-octopus-ev-spain/graphs/commit-activity)

Integración **no oficial** para conectar tu cuenta de **Octopus Energy España** con Home Assistant. Monitoriza tu consumo, saldos, facturas y controla tu cargador EV inteligente.

> ⚠️ **Importante**: Esta es una integración desarrollada por la comunidad, **no oficial** de Octopus Energy. El uso es bajo tu propia responsabilidad.

## 🚗 Características Principales

### 📊 **Información de Cuenta**
- **Saldos en tiempo real**: Electricidad y Monedero Solar
- **Información de contrato**: Número, tipo, fechas de validez
- **Datos de suministro**: Dirección, CUPS de electricidad
- **Facturas**: Importe y fechas de la última factura

### ⚡ **Control de Cargador EV**
- **Estado en tiempo real**: Conectado, desconectado, cargando
- **Control de carga rápida**: Iniciar/detener boost desde HA
- **Sesiones programadas**: Visualiza horarios de carga inteligente
- **Configuración avanzada**: Porcentaje máximo y hora objetivo
- **Historial de cargas**: Fecha, duración, energía y coste

### 🔧 **Servicios y Automatización**
- **Servicios integrados**: Control completo vía servicios de HA
- **Eventos personalizados**: Para automatizaciones avanzadas
- **Notificaciones**: Cambios de estado automáticos
- **Botones de acción**: Actualización manual del estado

### 💰 **Dispositivo Precios: "Octopus Energy EV España"**

| Sensor | Tipo | Descripción |
|---------|------|-------------|
| `sensor.octopus_precios_tarifa` | Sensor | Estructura de precios de la tarifa contratada |
| `sensor.octopus_precio_actual` | Sensor | Precio actual según horarios españoles |
| `sensor.octopus_precio_actual_ev` | Sensor | Precio actual con descuentos EV aplicados |

#### 🎯 **Detalles de los Sensores de Precios:**

##### 📋 **`sensor.octopus_precios_tarifa`**
- **Muestra**: `"Variable: 0.084 - 0.197 €/kWh"` (rango de tu tarifa)
- **Atributos clave**:
  - `rate_peak`: `"0.197 €/kWh"` (Precio punta)
  - `rate_standard`: `"0.122 €/kWh"` (Precio llano)  
  - `rate_offpeak`: `"0.084 €/kWh"` (Precio valle)
  - `all_variable_rates`: `[0.197, 0.122, 0.084]` (Para automatizaciones)

##### ⚡ **`sensor.octopus_precio_actual`**
- **Muestra**: `0.122` (precio actual en €/kWh)
- **Horarios aplicados**:
  - 🔴 **PUNTA** (0.197 €/kWh): L-V 10:00-14:00 y 18:00-22:00
  - 🟡 **LLANO** (0.122 €/kWh): L-V 8:00-10:00, 14:00-18:00, 22:00-24:00
  - 🟢 **VALLE** (0.084 €/kWh): L-V 0:00-8:00 + Sábados y Domingos completos
- **Atributos clave**:
  - `today[]`: Array con 48 intervalos de 30min para hoy
  - `tomorrow[]`: Array con 48 intervalos de 30min para mañana
  - `today_min_price`, `today_max_price`, `today_avg_price`
  - `current_period_start`, `current_period_end`, `current_period_value`

##### 🚗 **`sensor.octopus_precio_actual_ev`** ⭐ **¡REVOLUCIONARIO!**
- **Muestra**: `0.068` (durante carga EV) o precio normal
- **Lógica inteligente**:
  - **Sin coche conectado** → Precios normales
  - **Con coche conectado + carga programada** → **0.068 €/kWh fijo**
  - **Con coche conectado sin carga** → Precios normales  
  - **Se actualiza automáticamente** cuando cambian las `planned_dispatches`
- **Atributos únicos**:
  - `charger_connected`: `true/false`
  - `charging_periods[]`: Horarios exactos con descuento
  - `current_period_is_ev_discount`: `true/false`
  - `today_ev_discount_periods`: Número de períodos con descuento
  - `charging_sessions_count`: Sesiones programadas hoy

#### 📊 **Formato de datos (exacto a especificación API):**
```json
"today": [
  {
    "start": "2025-07-23T00:00:00+02:00",
    "end": "2025-07-23T00:30:00+02:00",
    "value": 0.084
  },
  {
    "start": "2025-07-23T00:30:00+02:00", 
    "end": "2025-07-23T01:00:00+02:00",
    "value": 0.084
  }
]
```

---

## 🏠 Instalación

### 📱 **Método 1: My Home Assistant (Recomendado)**

[![Abrir repositorio en HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=lockevod&repository=ha-octopus-ev-spain&category=integration)

1. **Haz clic en el botón de arriba** ↑
2. Se abrirá HACS directamente con el repositorio
3. Haz clic en **"Descargar"**
4. **Reinicia Home Assistant**
5. Ve a **Configuración → Dispositivos y Servicios → Agregar Integración**
6. Busca **"Octopus Energy EV Spain"**

### 🛠️ **Método 2: HACS Manual**

1. **Instala HACS** si no lo tienes: [Guía oficial HACS](https://hacs.xyz/docs/setup/download)
2. **Añade repositorio personalizado**:
   - Ve a **HACS → Integraciones → ⋮ → Repositorios personalizados**
   - **URL**: `https://github.com/lockevod/ha-octopus-ev-spain`
   - **Categoría**: `Integración`
   - Haz clic en **"Agregar"**
3. **Instala la integración**:
   - Busca **"Octopus Energy EV Spain"** en HACS
   - Haz clic en **"Descargar"**
4. **Reinicia Home Assistant**

### 💾 **Método 3: Instalación Manual**

```bash
# Descarga o clona en tu directorio custom_components
git clone https://github.com/lockevod/ha-octopus-ev-spain.git
mv ha-octopus-ev-spain/custom_components/octopus_ev_spain /config/custom_components/
```

---

## ⚙️ Configuración

### 🔑 **Configuración Inicial**

1. **Ve a Configuración → Dispositivos y Servicios**
2. **Haz clic en "Agregar Integración"**
3. **Busca "Octopus Energy EV Spain"**
4. **Introduce tus credenciales**:
   - Email de tu cuenta Octopus Energy España
   - Contraseña (se almacena de forma segura)

### ✅ **Requisitos**
- **Home Assistant 2025.1+**
- **Cuenta activa** en Octopus Energy España
- **Tarifa EV** (para funciones de cargador): Octopus Intelligent GO

---

## 📋 Entidades Disponibles

### 🏢 **Dispositivo Principal: "Octopus Energy EV España"**

| Sensor | Descripción | Unidad |
|--------|-------------|---------|
| `sensor.octopus_numero_de_contrato` | Número de contrato | - |
| `sensor.octopus_direccion` | Dirección del suministro | - |
| `sensor.octopus_cups_electricidad` | CUPS de electricidad | - |
| `sensor.octopus_tipo_de_contrato` | Tipo de tarifa contratada | - |
| `sensor.octopus_contrato_valido_desde` | Fecha inicio contrato | fecha |
| `sensor.octopus_contrato_valido_hasta` | Fecha fin contrato | fecha |
| `sensor.octopus_electricidad_saldo` | Saldo cuenta electricidad | € |
| `sensor.octopus_monedero_solar_saldo` | Saldo monedero solar | € |
| `sensor.ultima_factura_octopus` | Importe última factura | € |
| `sensor.octopus_precios_tarifa` | Estructura de precios de la tarifa | texto |
| `sensor.octopus_precio_actual` | Precio actual de la electricidad | €/kWh |
| `sensor.octopus_precio_actual_ev` | Precio actual con descuento EV | €/kWh |

### 🚗 **Dispositivo Cargador EV: "[Nombre Cargador]"**

| Entidad | Tipo | Descripción |
|---------|------|-------------|
| `sensor.[nombre]_contract_number` | Sensor | Número de contrato (referencia) |
| `sensor.[nombre]_address` | Sensor | Dirección (referencia) |
| `sensor.[nombre]_state` | Sensor | Estado actual del cargador |
| `sensor.[nombre]_planned_sessions` | Sensor | Sesiones de carga programadas |
| `sensor.[nombre]_next_session_start` | Sensor | Inicio próxima sesión |
| `sensor.[nombre]_last_session_end` | Sensor | Fin última sesión |
| `sensor.[nombre]_total_hours_today` | Sensor | Total horas programadas hoy |
| `sensor.[nombre]_last_charge_date` | Sensor | Fecha última carga |
| `sensor.[nombre]_last_session_duration` | Sensor | Duración última carga |
| `sensor.[nombre]_last_energy_added` | Sensor | Energía última carga (kWh) |
| `sensor.[nombre]_last_session_cost` | Sensor | Coste última carga (€) |
| `switch.[nombre]_carga_rapida` | Switch | Control carga rápida |
| `number.[nombre]_max_percentage` | Número | Porcentaje máximo de carga |
| `select.[nombre]_target_time` | Select | Hora objetivo (04:00-11:00) |
| `button.[nombre]_actualizar_y_verificar_estado` | Botón | Actualizar estado manualmente |

---

## 🎨 Ejemplos Lovelace

### 📊 **Tarjeta de Estado del Cargador**

```yaml
type: entities
title: 🚗 Estado Cargador EV
entities:
  - entity: sensor.cargador_ev_state
    name: Estado
    icon: mdi:ev-station
  - entity: sensor.cargador_ev_planned_sessions
    name: Sesiones Programadas
  - entity: sensor.cargador_ev_next_session_start
    name: Próxima Sesión
    format: time
  - entity: sensor.cargador_ev_total_hours_today
    name: Horas Programadas Hoy
  - type: divider
  - entity: switch.cargador_ev_carga_rapida
    name: Carga Rápida
  - entity: number.cargador_ev_max_percentage
    name: Porcentaje Máximo
  - entity: select.cargador_ev_target_time
    name: Hora Objetivo
```

### 💰 **Tarjeta de Saldos y Facturación**

```yaml
type: glance
title: 💰 Saldos Octopus Energy
entities:
  - entity: sensor.octopus_electricidad_saldo
    name: Electricidad
    icon: mdi:lightning-bolt
  - entity: sensor.octopus_monedero_solar_saldo
    name: Solar
    icon: mdi:solar-power
  - entity: sensor.ultima_factura_octopus
    name: Última Factura
    icon: mdi:receipt
columns: 3
```

### ⚡ **Tarjeta de Precios en Tiempo Real**

```yaml
type: entities
title: ⚡ Precios Electricidad
entities:
  - entity: sensor.octopus_precios_tarifa
    name: Estructura Tarifaria
    icon: mdi:currency-eur
  - entity: sensor.octopus_precio_actual
    name: Precio Actual Normal
    icon: mdi:flash
  - entity: sensor.octopus_precio_actual_ev
    name: Precio Actual EV
    icon: mdi:car-electric
  - type: divider
  - type: custom:template-entity-row
    entity: sensor.octopus_precio_actual_ev
    name: Ahorro EV Actual
    state: >
      {% set normal = states('sensor.octopus_precio_actual') | float %}
      {% set ev = states('sensor.octopus_precio_actual_ev') | float %}
      {% if normal > ev %}
        -{{ ((normal - ev) * 1000) | round(1) }} cts/kWh
      {% else %}
        Sin descuento
      {% endif %}
    icon: mdi:piggy-bank
```

### 📊 **Dashboard de Precios Avanzado**

```yaml
type: vertical-stack
cards:
  # Precios actuales
  - type: horizontal-stack
    cards:
      - type: gauge
        entity: sensor.octopus_precio_actual
        name: Precio Normal
        min: 0
        max: 0.3
        severity:
          green: 0.1
          yellow: 0.15
          red: 0.2
        needle: true
      - type: gauge  
        entity: sensor.octopus_precio_actual_ev
        name: Precio EV
        min: 0
        max: 0.3
        severity:
          green: 0.1
          yellow: 0.15
          red: 0.2
        needle: true
  
  # Información del periodo actual
  - type: entities
    entities:
      - type: custom:template-entity-row
        entity: sensor.octopus_precio_actual_ev
        name: Periodo Actual
        state: >
          {% set start = state_attr('sensor.octopus_precio_actual', 'current_period_start') %}
          {% set end = state_attr('sensor.octopus_precio_actual', 'current_period_end') %}
          {% if start and end %}
            {{ as_timestamp(start) | timestamp_custom('%H:%M') }} - {{ as_timestamp(end) | timestamp_custom('%H:%M') }}
          {% else %}
            No disponible
          {% endif %}
        icon: mdi:clock-outline
      - type: custom:template-entity-row
        entity: sensor.octopus_precio_actual_ev
        name: Descuento EV Activo
        state: >
          {% set is_ev = state_attr('sensor.octopus_precio_actual_ev', 'current_period_is_ev_discount') %}
          {{ 'Sí' if is_ev else 'No' }}
        icon: >
          {% set is_ev = state_attr('sensor.octopus_precio_actual_ev', 'current_period_is_ev_discount') %}
          {{ 'mdi:check-circle' if is_ev else 'mdi:close-circle' }}
```

### 📈 **Gráfico de Precios con ApexCharts**

```yaml
type: custom:apexcharts-card
header:
  title: 💰 Precios Octopus Hoy vs Mañana
  show: true
span:
  start: day
graph_span: 48h
series:
  - entity: sensor.octopus_precio_actual
    name: Precio Normal
    type: line
    color: blue
    data_generator: |
      const today = entity.attributes.today || [];
      const tomorrow = entity.attributes.tomorrow || [];
      const allPrices = [...today, ...tomorrow];
      return allPrices.map((entry) => {
        return [new Date(entry.start).getTime(), entry.value];
      });
  - entity: sensor.octopus_precio_actual_ev
    name: Precio EV (con descuento)
    type: line
    color: red
    data_generator: |
      const today = entity.attributes.today || [];
      const tomorrow = entity.attributes.tomorrow || [];
      const allPrices = [...today, ...tomorrow];
      return allPrices.map((entry) => {
        return [new Date(entry.start).getTime(), entry.value];
      });
yaxis:
  - title:
      text: €/kWh
    min: 0
    max: 0.25
annotations:
  yaxis:
    - y: 0.068
      borderColor: green
      label:
        text: "Precio EV (6.8cts)"
        style:
          color: white
          background: green
```

### 🎯 **Tarjeta de Ahorro EV Inteligente**

```yaml
type: vertical-stack
cards:
  - type: horizontal-stack
    cards:
      - type: custom:mushroom-entity-card
        entity: sensor.octopus_precio_actual
        name: Precio Normal
        icon: mdi:flash
        primary_info: state
        secondary_info: >
          {% set min_price = state_attr('sensor.octopus_precio_actual', 'today_min_price') %}
          {% set max_price = state_attr('sensor.octopus_precio_actual', 'today_max_price') %}
          Min: {{ min_price }}€ | Max: {{ max_price }}€
      - type: custom:mushroom-entity-card
        entity: sensor.octopus_precio_actual_ev
        name: Precio EV
        icon: mdi:car-electric
        primary_info: state
        secondary_info: >
          {% set discount_periods = state_attr('sensor.octopus_precio_actual_ev', 'today_ev_discount_periods') %}
          {{ discount_periods }} períodos con descuento
        
  - type: entities
    title: 🔋 Información EV Inteligente
    entities:
      - type: custom:template-entity-row
        entity: sensor.octopus_precio_actual_ev
        name: Estado Descuento EV
        state: >
          {% if state_attr('sensor.octopus_precio_actual_ev', 'current_period_is_ev_discount') %}
            🟢 ACTIVO ({{ states('sensor.octopus_precio_actual_ev') }}€/kWh)
          {% else %}
            ⚪ Inactivo
          {% endif %}
        icon: mdi:car-electric
      
      - type: custom:template-entity-row
        entity: sensor.octopus_precio_actual_ev
        name: Ahorro Instantáneo
        state: >
          {% set normal = states('sensor.octopus_precio_actual') | float %}
          {% set ev = states('sensor.octopus_precio_actual_ev') | float %}
          {% set savings = (normal - ev) * 1000 %}
          {% if savings > 0 %}
            💰 {{ savings | round(1) }} cts/kWh
          {% else %}
            Sin ahorro actual
          {% endif %}
        icon: mdi:piggy-bank
      
      - type: custom:template-entity-row
        entity: sensor.octopus_precio_actual_ev
        name: Próximas Cargas Hoy
        state: >
          {% set periods = state_attr('sensor.octopus_precio_actual_ev', 'charging_periods') %}
          {% if periods %}
            {% for period in periods %}
              {{ as_timestamp(period.start) | timestamp_custom('%H:%M') }}-{{ as_timestamp(period.end) | timestamp_custom('%H:%M') }}
              {%- if not loop.last %}, {% endif %}
            {% endfor %}
          {% else %}
            Sin cargas programadas
          {% endif %}
        icon: mdi:calendar-clock
```

### 🚨 **Alerta de Precios Críticos**

```yaml
type: conditional
conditions:
  - entity: sensor.octopus_precio_actual
    state_not: "unavailable"
card:
  type: vertical-stack
  cards:
    # Alerta precio alto
    - type: conditional
      conditions:
        - entity: sensor.octopus_precio_actual
          numeric_state:
            above: 0.17
      card:
        type: custom:mushroom-entity-card
        entity: sensor.octopus_precio_actual
        name: ⚠️ PRECIO ALTO
        primary_info: state
        secondary_info: "Evita consumos innecesarios"
        icon: mdi:alert
        icon_color: red
        tap_action:
          action: more-info
    
    # Oportunidad precio bajo
    - type: conditional
      conditions:
        - entity: sensor.octopus_precio_actual
          numeric_state:
            below: 0.09
      card:
        type: custom:mushroom-entity-card
        entity: sensor.octopus_precio_actual
        name: 💚 PRECIO MUY BAJO
        primary_info: state
        secondary_info: "¡Momento ideal para cargar!"
        icon: mdi:flash
        icon_color: green
        tap_action:
          action: call-service
          service: octopus_ev_spain.start_boost_charge
          service_data:
            device_id: "{{ state_attr('sensor.cargador_ev_state', 'device_id') }}"
    
    # Descuento EV activo
    - type: conditional
      conditions:
        - entity: sensor.octopus_precio_actual_ev
          attribute: current_period_is_ev_discount
          state: true
      card:
        type: custom:mushroom-entity-card
        entity: sensor.octopus_precio_actual_ev
        name: ⚡ DESCUENTO EV ACTIVO
        primary_info: state
        secondary_info: "Precio especial EV en curso"
        icon: mdi:car-electric
        icon_color: blue
```

### 🕐 **Planificador de Sesiones**

```yaml
type: custom:scheduler-card
title: 📅 Programación Carga EV
entities:
  - switch.cargador_ev_carga_rapida
discover_existing: true
time_step: 30
show_header_toggle: true
```

### 🎯 **Tarjeta de Control Rápido**

```yaml
type: horizontal-stack
cards:
  - type: button
    entity: button.cargador_ev_actualizar_y_verificar_estado
    name: Actualizar
    icon: mdi:refresh
    tap_action:
      action: call-service
      service: button.press
      target:
        entity_id: button.cargador_ev_actualizar_y_verificar_estado
  - type: button
    entity: switch.cargador_ev_carga_rapida
    name: Boost ON
    icon: mdi:flash
    tap_action:
      action: call-service
      service: switch.turn_on
      target:
        entity_id: switch.cargador_ev_carga_rapida
  - type: button
    entity: switch.cargador_ev_carga_rapida
    name: Boost OFF
    icon: mdi:flash-off
    tap_action:
      action: call-service
      service: switch.turn_off
      target:
        entity_id: switch.cargador_ev_carga_rapida
```

---

## 🤖 Automatizaciones

### 🔔 **Notificación cuando se conecta el coche**

```yaml
alias: "EV: Notificar conexión"
trigger:
  - platform: state
    entity_id: sensor.cargador_ev_state
    to: "connected"
action:
  - service: notify.mobile_app_tu_telefono
    data:
      title: "🔌 Coche Conectado"
      message: >
        Cargador {{ trigger.to_state.attributes.friendly_name }} 
        conectado. {{ states('sensor.cargador_ev_planned_sessions') }}
```

### 💰 **Notificación de precio EV barato**

```yaml
alias: "Precios: Notificar descuento EV activo"
trigger:
  - platform: state
    entity_id: sensor.octopus_precio_actual_ev
    attribute: current_period_is_ev_discount
    to: true
condition:
  - condition: numeric_state
    entity_id: sensor.octopus_precio_actual_ev
    below: 0.08  # Menor que 8 céntimos
action:
  - service: notify.mobile_app_tu_telefono
    data:
      title: "⚡ Precio EV súper barato"
      message: >
        Precio actual EV: {{ states('sensor.octopus_precio_actual_ev') }}€/kWh
        vs Normal: {{ states('sensor.octopus_precio_actual') }}€/kWh
        Ahorro: {{ ((states('sensor.octopus_precio_actual')|float - states('sensor.octopus_precio_actual_ev')|float) * 1000)|round(1) }} cts/kWh
```

### ⚡ **Inicio automático de carga en precio bajo**

```yaml
alias: "EV: Carga automática con precio valle"
trigger:
  - platform: numeric_state
    entity_id: sensor.octopus_precio_actual
    below: 0.09  # Precio valle muy barato
    for:
      minutes: 5
condition:
  - condition: state
    entity_id: sensor.cargador_ev_state
    state: "connected"
  - condition: numeric_state
    entity_id: sensor.coche_battery_level  # Tu sensor de batería del coche
    below: 80
  - condition: time
    after: "22:00:00"
    before: "06:00:00"  # Solo horario valle nocturno
action:
  - service: octopus_ev_spain.start_boost_charge
    data:
      device_id: "{{ state_attr('sensor.cargador_ev_state', 'device_id') }}"
  - service: notify.persistent_notification
    data:
      title: "🌙 Carga Nocturna Barata"
      message: >
        Precio valle detectado: {{ states('sensor.octopus_precio_actual') }}€/kWh
        Iniciando carga automática nocturna.
```

### 🏠 **Gestión energética basada en precios**

```yaml
alias: "Casa: Optimización según precios"
description: "Ajusta consumo según precios Octopus"
trigger:
  - platform: state
    entity_id: sensor.octopus_precio_actual
variables:
  precio_actual: "{{ states('sensor.octopus_precio_actual') | float }}"
  precio_ev: "{{ states('sensor.octopus_precio_actual_ev') | float }}"
  exceso_solar: "{{ states('sensor.inversor_potencia_exceso') | int }}"
  bateria_ev: "{{ states('sensor.coche_battery_level') | int }}"
action:
  - choose:
      # Precio muy caro: Solo cargas esenciales
      - conditions:
          - "{{ precio_actual > 0.18 }}"
        sequence:
          - service: switch.turn_off
            target:
              entity_id: switch.termo_electrico
          - service: switch.turn_off
            target:
              entity_id: switch.lavavajillas_delayed_start
          - service: notify.persistent_notification
            data:
              title: "⚠️ Precio Alto"
              message: >
                Precio actual: {{ precio_actual }}€/kWh
                Desactivando cargas no esenciales.
      
      # Precio barato: Aprovechar para cargas extras
      - conditions:
          - "{{ precio_actual < 0.10 }}"
          - "{{ bateria_ev < 90 }}"
        sequence:
          - service: switch.turn_on
            target:
              entity_id: switch.termo_electrico
          - service: octopus_ev_spain.start_boost_charge
            data:
              device_id: "{{ state_attr('sensor.cargador_ev_state', 'device_id') }}"
          - service: notify.persistent_notification
            data:
              title: "💚 Precio Bajo"
              message: >
                Precio valle: {{ precio_actual }}€/kWh
                Activando cargas aprovechando precio bajo.
```

### 📊 **Automatización de estadísticas de ahorro**

```yaml
alias: "Precios: Calcular ahorro diario EV"
trigger:
  - platform: time
    at: "23:59:00"  # Final del día
action:
  - service: input_number.set_value
    target:
      entity_id: input_number.ahorro_ev_hoy
    data:
      value: >
        {% set today_prices = state_attr('sensor.octopus_precio_actual', 'today') %}
        {% set today_ev_prices = state_attr('sensor.octopus_precio_actual_ev', 'today') %}
        {% set ahorro_total = 0 %}
        {% if today_prices and today_ev_prices %}
          {% for i in range(today_prices|length) %}
            {% set normal = today_prices[i].value %}
            {% set ev = today_ev_prices[i].value %}
            {% set ahorro_total = ahorro_total + (normal - ev) %}
          {% endfor %}
          {{ (ahorro_total / today_prices|length * 24) | round(3) }}
        {% else %}
          0
        {% endif %}
  - service: logbook.log
    data:
      name: "Ahorro EV"
      message: >
        Ahorro medio hoy: {{ states('input_number.ahorro_ev_hoy') }}€/kWh
        Periodos con descuento: {{ state_attr('sensor.octopus_precio_actual_ev', 'today_ev_discount_periods') }}
```

---

## ☀️ Integración Solar

### 🔋 **Optimización Carga Solar + EV**

La integración incluye soporte completo para el **Monedero Solar** de Octopus Energy, permitiendo optimizar la carga de tu EV con energía solar.

#### 📊 **Sensores Solar Disponibles**
- `sensor.octopus_monedero_solar_saldo` - Saldo del monedero solar (€)

#### ⚡ **Automatización: Carga EV con Exceso Solar**

```yaml
alias: "Solar: Cargar EV con exceso solar"
description: "Inicia carga cuando hay exceso de producción solar"
trigger:
  - platform: numeric_state
    entity_id: sensor.inversor_potencia_exceso  # Tu sensor de exceso solar
    above: 3000  # 3kW de exceso
    for:
      minutes: 5
condition:
  - condition: state
    entity_id: sensor.cargador_ev_state
    state: "connected"
  - condition: time
    after: "09:00:00"
    before: "17:00:00"  # Solo durante horas solares
  - condition: numeric_state
    entity_id: sensor.coche_battery_level
    below: 80  # Solo si batería < 80%
action:
  - service: octopus_ev_spain.start_boost_charge
    data:
      device_id: "{{ state_attr('sensor.cargador_ev_state', 'device_id') }}"
  - service: notify.persistent_notification
    data:
      title: "☀️ Carga Solar Activada"
      message: >
        Exceso solar detectado: {{ states('sensor.inversor_potencia_exceso') }}W.
        Iniciando carga EV con energía solar.
```

#### 🛑 **Automatización: Parar carga cuando no hay exceso**

```yaml
alias: "Solar: Detener carga sin exceso"
trigger:
  - platform: numeric_state
    entity_id: sensor.inversor_potencia_exceso
    below: 1000  # Menos de 1kW de exceso
    for:
      minutes: 10
condition:
  - condition: state
    entity_id: switch.cargador_ev_carga_rapida
    state: "on"
  - condition: state
    entity_id: binary_sensor.carga_solar_activa  # Sensor helper
    state: "on"
action:
  - service: octopus_ev_spain.stop_boost_charge
    data:
      device_id: "{{ state_attr('sensor.cargador_ev_state', 'device_id') }}"
  - service: input_boolean.turn_off
    target:
      entity_id: input_boolean.carga_solar_activa
  - service: notify.persistent_notification
    data:
      title: "☀️ Carga Solar Pausada"
      message: "Exceso solar insuficiente. Carga EV pausada."
```

#### 📈 **Dashboard Solar + EV**

```yaml
type: vertical-stack
cards:
  - type: horizontal-stack
    cards:
      - type: gauge
        entity: sensor.inversor_potencia_actual
        name: Producción Solar
        min: 0
        max: 5000
        severity:
          green: 2000
          yellow: 1000
          red: 0
      - type: gauge
        entity: sensor.octopus_monedero_solar_saldo  
        name: Monedero Solar
        min: 0
        max: 100
        severity:
          green: 50
          yellow: 20
          red: 0
  
  - type: entities
    title: ☀️ Control Carga Solar
    entities:
      - entity: sensor.inversor_potencia_exceso
        name: Exceso Solar
        icon: mdi:solar-power
      - entity: input_boolean.carga_solar_activa
        name: Modo Carga Solar
        icon: mdi:car-electric
      - entity: sensor.cargador_ev_state
        name: Estado Cargador
      - entity: switch.cargador_ev_carga_rapida
        name: Carga Activa
  
  - type: custom:apexcharts-card
    header:
      title: ☀️ Solar vs Carga EV
      show: true
    span:
      start: day
    graph_span: 24h
    series:
      - entity: sensor.inversor_potencia_actual
        name: Producción Solar
        type: area
        color: orange
      - entity: sensor.cargador_potencia_actual  # Tu sensor de potencia del cargador
        name: Consumo EV
        type: line
        color: blue
      - entity: sensor.inversor_potencia_exceso
        name: Exceso Solar
        type: line
        color: green
```

#### 🏠 **Gestión Inteligente Casa + Solar + EV**

```yaml
alias: "Casa: Gestión energética inteligente"
description: "Optimiza consumo según producción solar y necesidades"
trigger:
  - platform: state
    entity_id: sensor.inversor_potencia_exceso
variables:
  exceso: "{{ states('sensor.inversor_potencia_exceso') | int }}"
  bateria_casa: "{{ states('sensor.bateria_casa_soc') | int }}"
  bateria_ev: "{{ states('sensor.coche_battery_level') | int }}"
action:
  - choose:
      # Mucho exceso: Cargar EV + Batería casa
      - conditions:
          - "{{ exceso > 4000 }}"
          - "{{ bateria_ev < 90 }}"
        sequence:
          - service: octopus_ev_spain.start_boost_charge
            data:
              device_id: "{{ state_attr('sensor.cargador_ev_state', 'device_id') }}"
          - service: switch.turn_on
            target:
              entity_id: switch.bateria_casa_carga_forzada
      
      # Exceso medio: Solo EV si batería casa OK
      - conditions:
          - "{{ exceso > 2000 and exceso <= 4000 }}"
          - "{{ bateria_casa > 70 }}"
          - "{{ bateria_ev < 80 }}"
        sequence:
          - service: octopus_ev_spain.start_boost_charge
            data:
              device_id: "{{ state_attr('sensor.cargador_ev_state', 'device_id') }}"
      
      # Poco exceso: Solo cargas esenciales
      - conditions:
          - "{{ exceso < 1000 }}"
        sequence:
          - service: octopus_ev_spain.stop_boost_charge
            data:
              device_id: "{{ state_attr('sensor.cargador_ev_state', 'device_id') }}"
          - service: switch.turn_off
            target:
              entity_id: switch.bateria_casa_carga_forzada
```

#### 💰 **Sensor: Ahorro Solar EV**

```yaml
# configuration.yaml
sensor:
  - platform: template
    sensors:
      ahorro_solar_ev:
        friendly_name: "Ahorro Solar EV"
        unit_of_measurement: "€"
        device_class: monetary
        value_template: >
          {% set energia_solar = states('sensor.energia_solar_a_ev_hoy') | float %}
          {% set precio_red = states('sensor.precio_luz_actual') | float %}
          {% set precio_solar = 0.05 %}  # Coste estimado kWh solar
          {{ ((precio_red - precio_solar) * energia_solar) | round(2) }}
        attribute_templates:
          energia_solar_hoy: "{{ states('sensor.energia_solar_a_ev_hoy') }} kWh"
          precio_evitado: "{{ states('sensor.precio_luz_actual') }}€/kWh"
```

#### 📱 **Notificaciones Solar**

```yaml
alias: "Solar: Notificar oportunidades carga"
trigger:
  - platform: numeric_state
    entity_id: sensor.inversor_potencia_exceso
    above: 3000
    for:
      minutes: 15
condition:
  - condition: state
    entity_id: sensor.cargador_ev_state
    state: "connected"
  - condition: state
    entity_id: switch.cargador_ev_carga_rapida
    state: "off"
action:
  - service: notify.mobile_app_tu_telefono
    data:
      title: "☀️ Oportunidad Carga Solar"
      message: >
        Exceso solar: {{ states('sensor.inversor_potencia_exceso') }}W
        Coche conectado. ¿Iniciar carga gratuita?
      data:
        actions:
          - action: "start_solar_charge"
            title: "🚗 Cargar Ahora"
          - action: "dismiss"
            title: "❌ Descartar"

# Automatización para manejar la respuesta
- alias: "Solar: Manejar respuesta notificación"
  trigger:
    - platform: event
      event_type: mobile_app_notification_action
      event_data:
        action: "start_solar_charge"
  action:
    - service: octopus_ev_spain.start_boost_charge
      data:
        device_id: "{{ state_attr('sensor.cargador_ev_state', 'device_id') }}"
    - service: input_boolean.turn_on
      target:
        entity_id: input_boolean.carga_solar_activa
```

---

## 🔗 **Ejemplos con Custom Components Avanzados**

### 🔋 **Con Huawei Solar Custom Component**

Asumiendo que ya tienes [Huawei Solar](https://github.com/wlcrs/huawei_solar) instalado:

```yaml
alias: "Octopus + Huawei: Control EV inteligente"
description: "Usa sensores Huawei Solar para controlar cargador Octopus"
trigger:
  - platform: state
    entity_id: sensor.inverter_active_power
    for:
      minutes: 3
variables:
  produccion_solar: "{{ states('sensor.inverter_active_power') | int }}"
  consumo_casa: "{{ states('sensor.power_meter_active_power') | int }}"
  bateria_casa_soc: "{{ states('sensor.battery_state_of_capacity') | int }}"
  exceso_solar: "{{ produccion_solar - consumo_casa }}"
  ev_estado: "{{ states('sensor.cargador_ev_state') }}"
action:
  - choose:
      # Exceso > 3kW + Batería casa > 70%: Iniciar carga EV
      - conditions:
          - "{{ exceso_solar > 3000 }}"
          - "{{ bateria_casa_soc > 70 }}"
          - "{{ ev_estado == 'connected' }}"
        sequence:
          - service: octopus_ev_spain.start_boost_charge
            data:
              device_id: "{{ state_attr('sensor.cargador_ev_state', 'device_id') }}"
          - service: notify.persistent_notification
            data:
              title: "🔋⚡ Huawei + Octopus"
              message: >
                Iniciando carga EV: {{ exceso_solar }}W exceso
                Batería casa: {{ bateria_casa_soc }}%
      
      # Poco exceso: Parar carga
      - conditions:
          - "{{ exceso_solar < 1000 }}"
          - "{{ is_state('switch.cargador_ev_carga_rapida', 'on') }}"
        sequence:
          - service: octopus_ev_spain.stop_boost_charge
            data:
              device_id: "{{ state_attr('sensor.cargador_ev_state', 'device_id') }}"
```

### 🌤️ **Con Solcast Custom Component**

Asumiendo que ya tienes [Solcast](https://github.com/BJReplay/ha-solcast-solar) instalado:

```yaml
alias: "Octopus + Solcast: Planificación predictiva"
description: "Ajusta configuración Octopus según previsiones Solcast"
trigger:
  - platform: time
    at: "06:00:00"
  - platform: state
    entity_id: sensor.cargador_ev_state
    to: "connected"
variables:
  prevision_hoy: "{{ states('sensor.solcast_pv_forecast_forecast_today') | float }}"
  prevision_manana: "{{ states('sensor.solcast_pv_forecast_forecast_tomorrow') | float }}"
  mejor_hora_hoy: "{{ state_attr('sensor.solcast_pv_forecast_peak_w_today', 'period_start') }}"
  ev_bateria: "{{ states('sensor.coche_battery_level') | int }}"
action:
  - choose:
      # Excelente día solar (>25kWh): Configurar para máximo solar
      - conditions:
          - "{{ prevision_hoy > 25 }}"
        sequence:
          - service: select.select_option
            target:
              entity_id: select.cargador_ev_target_time
            data:
              option: "10:30"  # Hora pico solar
          - service: number.set_value
            target:
              entity_id: number.cargador_ev_max_percentage
            data:
              value: 95
          - service: notify.persistent_notification
            data:
              title: "🌞 Solcast + Octopus"
              message: >
                Excelente día solar: {{ prevision_hoy }}kWh
                EV configurado para carga solar máxima
      
      # Día solar regular (10-25kWh): Configuración mixta
      - conditions:
          - "{{ prevision_hoy >= 10 and prevision_hoy <= 25 }}"
        sequence:
          - service: select.select_option
            target:
              entity_id: select.cargador_ev_target_time
            data:
              option: "09:00"
          - service: number.set_value
            target:
              entity_id: number.cargador_ev_max_percentage
            data:
              value: 80
      
      # Mal día solar (<10kWh): Carga nocturna
      - conditions:
          - "{{ prevision_hoy < 10 }}"
        sequence:
          - service: select.select_option
            target:
              entity_id: select.cargador_ev_target_time
            data:
              option: "06:00"  # Tarifa valle
          - service: number.set_value
            target:
              entity_id: number.cargador_ev_max_percentage
            data:
              value: 70
```

### 🧠 **Con EMHASS Custom Component - OPTIMIZACIÓN AVANZADA**

Asumiendo que ya tienes [EMHASS](https://github.com/davidusb-geek/emhass) instalado:

```yaml
alias: "Octopus + EMHASS: Optimización con precios reales"
description: "Usa precios Octopus para alimentar optimización EMHASS"
trigger:
  - platform: time_pattern
    minutes: "/30"  # Cada 30 minutos (coincide con intervalos de precios)
  - platform: state
    entity_id: sensor.octopus_precio_actual_ev
    attribute: today
variables:
  # Obtener precios horarios de Octopus para EMHASS
  precios_hoy: "{{ state_attr('sensor.octopus_precio_actual_ev', 'today') }}"
  precios_manana: "{{ state_attr('sensor.octopus_precio_actual_ev', 'tomorrow') }}"
  coche_conectado: "{{ state_attr('sensor.octopus_precio_actual_ev', 'charger_connected') }}"
  precio_actual: "{{ states('sensor.octopus_precio_actual_ev') | float }}"
action:
  # Configurar EMHASS con precios reales de Octopus
  - service: rest_command.emhass_post_configuration
    data:
      load_cost_forecast: >
        [{% for precio in precios_hoy -%}
          {{ precio.value }}{{ ',' if not loop.last }}
        {%- endfor %}]
      prod_price_forecast: >
        [{% for precio in precios_hoy -%}
          {{ (precio.value * 0.8) | round(3) }}{{ ',' if not loop.last }}
        {%- endfor %}]
      
  # Ejecutar optimización si es necesario
  - choose:
      # Precio muy alto: Optimizar para reducir consumo
      - conditions:
          - "{{ precio_actual > 0.15 }}"
        sequence:
          - service: rest_command.emhass_optimization
            data:
              def_total_hours: [0, 0, 0, 0]  # No cargar durante precio alto
          - service: notify.persistent_notification
            data:
              title: "🧠 EMHASS + Octopus"
              message: >
                Precio alto ({{ precio_actual }}€/kWh): Optimización conservadora
      
      # Precio bajo + coche conectado: Optimizar para cargar
      - conditions:
          - "{{ precio_actual < 0.10 }}"
          - "{{ coche_conectado }}"
        sequence:
          - service: rest_command.emhass_optimization
            data:
              def_total_hours: [3, 0, 0, 0]  # Cargar 3kW durante precio bajo
          - service: octopus_ev_spain.start_boost_charge
            data:
              device_id: "{{ state_attr('sensor.cargador_ev_state', 'device_id') }}"
          - service: notify.persistent_notification
            data:
              title: "🧠 EMHASS + Octopus"
              message: >
                Precio bajo ({{ precio_actual }}€/kWh): Optimización agresiva + carga EV
```

### 📈 **Dashboard EMHASS + Octopus integrado**

```yaml
type: vertical-stack
cards:
  # Precios y optimización
  - type: horizontal-stack
    cards:
      - type: gauge
        entity: sensor.octopus_precio_actual_ev
        name: Precio EV Actual
        min: 0
        max: 0.25
        severity:
          green: 0.08
          yellow: 0.12
          red: 0.18
      - type: gauge
        entity: sensor.p_deferrable0  # EMHASS
        name: Recomendación EMHASS
        min: 0
        max: 5000
        unit: W
  
  # Estado de integración
  - type: entities
    title: 🧠 EMHASS + Octopus Integration
    entities:
      - entity: sensor.octopus_precio_actual
        name: Precio Normal
      - entity: sensor.octopus_precio_actual_ev
        name: Precio EV (con descuento)
      - entity: sensor.p_deferrable0
        name: EMHASS Recomendación EV
      - entity: sensor.unit_load_cost
        name: EMHASS Coste kWh
      - type: divider
      - type: custom:template-entity-row
        entity: sensor.octopus_precio_actual_ev
        name: Diferencia EMHASS vs Octopus
        state: >
          {% set octopus = states('sensor.octopus_precio_actual_ev') | float %}
          {% set emhass = states('sensor.unit_load_cost') | float %}
          {{ ((octopus - emhass) * 1000) | round(1) }} cts/kWh
        icon: mdi:compare-horizontal
  
  # Gráfico comparativo
  - type: custom:apexcharts-card
    header:
      title: 📊 Precios: Octopus vs EMHASS
    span:
      start: day
    series:
      - entity: sensor.octopus_precio_actual_ev
        name: Octopus Precio EV
        type: line
        color: blue
        data_generator: |
          return entity.attributes.today.map((entry) => {
            return [new Date(entry.start).getTime(), entry.value];
          });
      - entity: sensor.unit_load_cost
        name: EMHASS Coste
        type: line
        color: orange
      - entity: sensor.p_deferrable0
        name: EMHASS Recomendación (kW)
        type: column
        yaxis_id: power
        color: green
    yaxis:
      - id: price
        title:
          text: €/kWh
      - id: power
        opposite: true
        title:
          text: kW
```

### 🔄 **Automatización: Sincronizar EMHASS con precios Octopus**

```yaml
alias: "EMHASS: Sincronizar con precios Octopus automáticamente"
description: "Actualiza EMHASS cada vez que Octopus actualiza precios"
trigger:
  - platform: state
    entity_id: sensor.octopus_precio_actual_ev
    attribute: today
  - platform: time
    at: "00:05:00"  # Diariamente para obtener precios de mañana
action:
  - service: rest_command.emhass_dayahead_optim
    data:
      load_cost_forecast: >
        {% set today = state_attr('sensor.octopus_precio_actual_ev', 'today') %}
        {% set tomorrow = state_attr('sensor.octopus_precio_actual_ev', 'tomorrow') %}
        {% set all_prices = today + tomorrow %}
        [{% for precio in all_prices -%}
          {{ precio.value }}{{ ',' if not loop.last }}
        {%- endfor %}]
      prod_price_forecast: >
        {% set today = state_attr('sensor.octopus_precio_actual_ev', 'today') %}
        {% set tomorrow = state_attr('sensor.octopus_precio_actual_ev', 'tomorrow') %}
        {% set all_prices = today + tomorrow %}
        [{% for precio in all_prices -%}
          {{ (precio.value * 0.75) | round(3) }}{{ ',' if not loop.last }}
        {%- endfor %}]
  - service: logbook.log
    data:
      name: "EMHASS + Octopus"
      message: >
        Precios sincronizados: {{ state_attr('sensor.octopus_precio_actual_ev', 'today_prices_count') }} períodos hoy,
        {{ state_attr('sensor.octopus_precio_actual_ev', 'tomorrow_prices_count') }} períodos mañana.
        Descuentos EV: {{ state_attr('sensor.octopus_precio_actual_ev', 'today_ev_discount_periods') }} períodos.
```

### 🔄 **Combinación: Huawei + Solcast + EMHASS + Octopus + PRECIOS**

```yaml
alias: "SUPER: Sistema maestro con precios inteligentes"
description: "Combina todos los sistemas + precios Octopus para gestión perfecta"
trigger:
  - platform: time_pattern
    minutes: "/10"  # Cada 10 minutos
variables:
  # Huawei Solar (tiempo real)
  produccion_actual: "{{ states('sensor.inverter_active_power') | int }}"
  consumo_casa: "{{ states('sensor.power_meter_active_power') | int }}"
  bateria_casa: "{{ states('sensor.battery_state_of_capacity') | int }}"
  exceso_actual: "{{ produccion_actual - consumo_casa }}"
  
  # Solcast (previsiones)
  prevision_siguiente: "{{ states('sensor.solcast_pv_forecast_power_now') | int }}"
  prevision_dia: "{{ states('sensor.solcast_pv_forecast_forecast_today') | float }}"
  
  # EMHASS (optimización)
  recomendacion_emhass: "{{ states('sensor.p_deferrable0') | int }}"
  
  # Octopus Precios (NUEVO - clave para decisiones)
  precio_actual: "{{ states('sensor.octopus_precio_actual') | float }}"
  precio_ev: "{{ states('sensor.octopus_precio_actual_ev') | float }}"
  descuento_ev_activo: "{{ state_attr('sensor.octopus_precio_actual_ev', 'current_period_is_ev_discount') }}"
  precio_min_hoy: "{{ state_attr('sensor.octopus_precio_actual', 'today_min_price') | float }}"
  
  # Octopus EV España
  ev_estado: "{{ states('sensor.cargador_ev_state') }}"
  ev_cargando: "{{ is_state('switch.cargador_ev_carga_rapida', 'on') }}"
  ev_bateria: "{{ states('sensor.coche_battery_level') | int }}"
action:
  - choose:
      # PRIORIDAD 1: Exceso solar + precio valle = Carga máxima
      - conditions:
          - "{{ exceso_actual > 3500 }}"
          - "{{ bateria_casa > 80 }}"
          - "{{ precio_actual <= precio_min_hoy + 0.01 }}"  # Precio muy barato
          - "{{ ev_estado == 'connected' }}"
          - "{{ ev_bateria < 95 }}"
        sequence:
          - service: octopus_ev_spain.start_boost_charge
            data:
              device_id: "{{ state_attr('sensor.cargador_ev_state', 'device_id') }}"
          - service: number.set_value
            target:
              entity_id: number.cargador_ev_max_percentage
            data:
              value: 95
          - service: logbook.log
            data:
              name: "Sistema Maestro"
              message: >
                🔥 OPTIMAL: Exceso {{ exceso_actual }}W + Precio {{ precio_actual }}€/kWh
                Batería casa {{ bateria_casa }}% - Carga EV al máximo
      
      # PRIORIDAD 2: Descuento EV activo + EMHASS recomienda
      - conditions:
          - "{{ descuento_ev_activo }}"
          - "{{ recomendacion_emhass > 2000 }}"
          - "{{ ev_estado == 'connected' }}"
          - "{{ not ev_cargando }}"
        sequence:
          - service: octopus_ev_spain.start_boost_charge
            data:
              device_id: "{{ state_attr('sensor.cargador_ev_state', 'device_id') }}"
          - service: logbook.log
            data:
              name: "Sistema Maestro"
              message: >
                ⚡ DESCUENTO EV: {{ precio_ev }}€/kWh (vs {{ precio_actual }}€/kWh)
                EMHASS recomienda: {{ recomendacion_emhass }}W
      
      # PRIORIDAD 3: Exceso solar moderado + precio no alto
      - conditions:
          - "{{ exceso_actual > 2000 }}"
          - "{{ bateria_casa > 60 }}"
          - "{{ precio_actual < 0.15 }}"
          - "{{ ev_estado == 'connected' }}"
          - "{{ not ev_cargando }}"
        sequence:
          - service: octopus_ev_spain.start_boost_charge
            data:
              device_id: "{{ state_attr('sensor.cargador_ev_state', 'device_id') }}"
          - service: logbook.log
            data:
              name: "Sistema Maestro"
              message: >
                ☀️ SOLAR MODERADO: {{ exceso_actual }}W
                Precio aceptable: {{ precio_actual }}€/kWh
      
      # PRIORIDAD 4: Precio muy alto - Parar todo lo no esencial
      - conditions:
          - "{{ precio_actual > 0.18 }}"
          - "{{ exceso_actual < 1000 }}"
        sequence:
          - service: octopus_ev_spain.stop_boost_charge
            data:
              device_id: "{{ state_attr('sensor.cargador_ev_state', 'device_id') }}"
          - service: switch.turn_off
            target:
              entity_id: switch.bateria_casa_carga_forzada
          - service: logbook.log
            data:
              name: "Sistema Maestro"
              message: >
                ⚠️ PRECIO ALTO: {{ precio_actual }}€/kWh
                Exceso mínimo: {{ exceso_actual }}W - Conservando energía
      
      # PRIORIDAD 5: Prevision solar buena + precio valle próximo
      - conditions:
          - "{{ prevision_siguiente > 3000 }}"
          - "{{ precio_actual > precio_min_hoy + 0.05 }}"  # No es el precio más barato
          - "{{ ev_bateria < 70 }}"
        sequence:
          # Esperar a mejor momento - no hacer nada por ahora
          - service: logbook.log
            data:
              name: "Sistema Maestro"  
              message: >
                ⏳ ESPERANDO: Previsión solar {{ prevision_siguiente }}W
                Precio actual {{ precio_actual }}€/kWh vs mín {{ precio_min_hoy }}€/kWh
```

### 📊 **Dashboard Integrado Completo con Precios**

```yaml
type: vertical-stack
cards:
  # Estado de todos los sistemas + precios
  - type: horizontal-stack
    cards:
      - type: entity
        entity: sensor.inverter_device_status
        name: 🔋 Huawei
      - type: entity
        entity: sensor.solcast_pv_forecast_forecast_today
        name: 🌤️ Solcast
      - type: entity
        entity: sensor.p_deferrable0
        name: 🧠 EMHASS
      - type: entity
        entity: sensor.octopus_precio_actual_ev
        name: 💰 Octopus
      - type: entity
        entity: sensor.cargador_ev_state
        name: 🚗 EV

  # Métricas principales con precios
  - type: horizontal-stack
    cards:
      - type: gauge
        entity: sensor.inverter_active_power
        name: Solar Actual
        min: 0
        max: 10000
      - type: gauge
        entity: sensor.octopus_precio_actual
        name: Precio Normal
        min: 0
        max: 0.25
        severity:
          green: 0.08
          yellow: 0.15
          red: 0.20
      - type: gauge
        entity: sensor.octopus_precio_actual_ev
        name: Precio EV
        min: 0
        max: 0.25
        severity:
          green: 0.068
          yellow: 0.10
          red: 0.15

  # Información de decisiones inteligentes
  - type: entities
    title: 🧠 Decisiones del Sistema Maestro
    entities:
      - type: custom:template-entity-row
        entity: sensor.octopus_precio_actual_ev
        name: Situación Energética
        state: >
          {% set exceso = states('sensor.inverter_active_power')|int - states('sensor.power_meter_active_power')|int %}
          {% set precio = states('sensor.octopus_precio_actual')|float %}
          {% if exceso > 3000 and precio < 0.10 %}
            🔥 ÓPTIMA - Solar + Precio bajo
          {% elif exceso > 2000 %}
            ☀️ BUENA - Exceso solar moderado
          {% elif precio < 0.08 %}
            💰 BUENA - Precio muy barato
          {% elif precio > 0.18 %}
            ⚠️ CARA - Precio alto
          {% else %}
            ⚡ NORMAL - Condiciones estándar
          {% endif %}
        icon: >
          {% set exceso = states('sensor.inverter_active_power')|int - states('sensor.power_meter_active_power')|int %}
          {% set precio = states('sensor.octopus_precio_actual')|float %}
          {% if exceso > 3000 and precio < 0.10 %}
            mdi:fire
          {% elif precio > 0.18 %}
            mdi:alert
          {% else %}
            mdi:flash
          {% endif %}
      
      - type: custom:template-entity-row
        entity: sensor.octopus_precio_actual_ev
        name: Recomendación IA
        state: >
          {% set exceso = states('sensor.inverter_active_power')|int - states('sensor.power_meter_active_power')|int %}
          {% set precio = states('sensor.octopus_precio_actual')|float %}
          {% set ev_conectado = is_state('sensor.cargador_ev_state', 'connected') %}
          {% set descuento_ev = state_attr('sensor.octopus_precio_actual_ev', 'current_period_is_ev_discount') %}
          
          {% if exceso > 3000 and precio < 0.10 and ev_conectado %}
            Cargar EV al máximo
          {% elif descuento_ev and ev_conectado %}
            Aprovechar descuento EV
          {% elif precio > 0.18 %}
            Conservar energía
          {% elif precio < 0.08 %}
            Cargar todo lo posible
          {% else %}
            Modo estándar
          {% endif %}
        icon: mdi:brain
      
      - type: custom:template-entity-row
        entity: sensor.octopus_precio_actual_ev
        name: Ahorro Potencial Hoy
        state: >
          {% set normal_avg = state_attr('sensor.octopus_precio_actual', 'today_avg_price') %}
          {% set ev_avg = state_attr('sensor.octopus_precio_actual_ev', 'today_avg_price') %}
          {% if normal_avg and ev_avg %}
            {{ ((normal_avg - ev_avg) * 1000) | round(1) }} cts/kWh
          {% else %}
            Calculando...
          {% endif %}
        icon: mdi:piggy-bank

  # Gráfico integrado con precios
  - type: custom:apexcharts-card
    header:
      title: ⚡ SISTEMA COMPLETO + PRECIOS
    span:
      start: day
    series:
      - entity: sensor.inverter_active_power
        name: Solar (Huawei)
        type: area
        color: orange
        unit: W
      - entity: sensor.solcast_pv_forecast_power_now
        name: Previsión (Solcast)
        type: line
        color: yellow
        unit: W
      - entity: sensor.p_deferrable0
        name: Óptimo (EMHASS)
        type: column
        color: green
        unit: W
      - entity: sensor.octopus_precio_actual
        name: Precio Normal (Octopus)
        type: line
        color: blue
        yaxis_id: price
        unit: €/kWh
        data_generator: |
          return entity.attributes.today.map((entry) => {
            return [new Date(entry.start).getTime(), entry.value];
          });
      - entity: sensor.octopus_precio_actual_ev
        name: Precio EV (Octopus)
        type: line
        color: red
        yaxis_id: price
        unit: €/kWh
        data_generator: |
          return entity.attributes.today.map((entry) => {
            return [new Date(entry.start).getTime(), entry.value];
          });
    yaxis:
      - id: power
        title:
          text: W
      - id: price
        opposite: true
        title:
          text: €/kWh
        min: 0
        max: 0.25
```

### 🎯 **Ventajas de la Integración Completa:**

- ✅ **Datos reales** (Huawei) + **Previsiones** (Solcast) + **Optimización** (EMHASS) + **Precios reales** (Octopus)
- ✅ **Control directo** del cargador Octopus EV Spain
- ✅ **Lógica de prioridades** inteligente basada en precios y producción solar
- ✅ **Dashboard unificado** de todos los sistemas con precios en tiempo real
- ✅ **Automatización sin intervención** manual usando precios Octopus
- ✅ **Máximo ahorro** energético con descuentos EV automáticos

¡Tu custom component de Octopus EV Spain se convierte en el cerebro ejecutor de todo el sistema, ahora con **información de precios en tiempo real**! 🧠⚡💰

---

## 💰 **¿Por qué los Sensores de Precios son Revolucionarios?**

### 🎯 **Para EMHASS:**
- **Precios horarios reales** directos de Octopus → EMHASS optimiza con datos 100% precisos
- **Descuentos EV automáticos** → EMHASS recibe precios EV reales (0.068€/kWh vs normales)
- **Sincronización perfecta** → Cuando Octopus actualiza precios, EMHASS se reconfigura automáticamente

### 🏠 **Para Casa Inteligente:**
- **Decisiones energéticas automáticas** basadas en precios reales
- **Activación de cargas** cuando precio < 0.09€/kWh
- **Pausa de consumos** cuando precio > 0.18€/kWh
- **Aprovechamiento de descuentos EV** para cargas domésticas

### ⚡ **Para Optimización Solar:**
- **Combina exceso solar + precios** → Decisión perfecta de cuándo cargar
- **Evita venta a red en precio alto** → Mejor cargar EV con descuento
- **Maximiza autoconsumo** en períodos de precio valle

### 📊 **Para Monitorización:**
- **Ahorro real calculado** → Ves exactamente cuánto ahorras con EV
- **Predicciones** → Sabes cuándo habrá precios bajos mañana
- **Estadísticas** → Períodos más económicos, ahorro mensual, etc.

### 🤖 **Ejemplos de Valor Real:**

```yaml
# Automatización: Usar datos de precios para EMHASS
- Si precio_actual < precio_min_hoy + 0.02€ → EMHASS agresivo
- Si descuento_ev_activo → Forzar carga EV independiente de exceso solar  
- Si precio > 0.18€/kWh → EMHASS conservador, solo cargas esenciales
```

**Resultado**: Sistema energético que **toma decisiones inteligentes** usando precios reales de tu comercializadora, no estimaciones. ¡La integración perfecta entre hardware, software y mercado eléctrico! 🎯

---

## 🔧 Servicios Disponibles

### `octopus_ev_spain.start_boost_charge`
**Inicia carga rápida**
```yaml
service: octopus_ev_spain.start_boost_charge
data:
  device_id: "tu_device_id"
```

### `octopus_ev_spain.stop_boost_charge`
**Detiene carga rápida**
```yaml
service: octopus_ev_spain.stop_boost_charge
data:
  device_id: "tu_device_id"
```

### `octopus_ev_spain.refresh_charger`
**Actualiza datos del cargador**
```yaml
service: octopus_ev_spain.refresh_charger
```

### `octopus_ev_spain.check_charger`
**Verifica estado y notifica cambios**
```yaml
service: octopus_ev_spain.check_charger
data:
  notify: true
```

### `octopus_ev_spain.set_preferences`
**Configura preferencias de carga**
```yaml
service: octopus_ev_spain.set_preferences
data:
  device_id: "tu_device_id"
  max_percentage: 85
  target_time: "08:30"
```

---

## 🔗 Integración con Otras Plataformas

### 💡 **Node-RED**
```json
{
  "id": "ev_monitor",
  "type": "ha-entity",
  "name": "Monitor EV",
  "server": "home_assistant",
  "entity_id": "sensor.cargador_ev_state",
  "property": "state",
  "output_properties": [
    {
      "property": "payload",
      "propertyType": "msg",
      "value": "",
      "valueType": "entityState"
    }
  ]
}
```

### 📊 **Grafana Dashboard**
```json
{
  "dashboard": {
    "title": "Octopus Energy EV",
    "panels": [
      {
        "title": "Consumo EV",
        "type": "stat",
        "targets": [
          {
            "entity": "sensor.cargador_ev_last_energy_added",
            "format": "time_series"
          }
        ]
      }
    ]
  }
}
```

### 🎮 **Control por Voz (Alexa/Google)**
```yaml
# configuration.yaml
alexa:
  smart_home:
    filter:
      include_entities:
        - switch.cargador_ev_carga_rapida
        - sensor.cargador_ev_state
```

### 💰 **Integración con Tarifas**
```yaml
# Sensor personalizado para coste en tiempo real
sensor:
  - platform: template
    sensors:
      coste_carga_actual:
        friendly_name: "Coste Carga Actual"
        unit_of_measurement: "€/kWh"
        value_template: >
          {% if is_state('sensor.cargador_ev_state', 'boost_charging') %}
            {{ states('sensor.precio_luz_actual') }}
          {% else %}
            {{ states('sensor.precio_luz_valle') }}
          {% endif %}
```

---

## 🐛 Resolución de Problemas

### ❌ **Error de Autenticación**
```
ConfigEntryAuthFailed: Authentication failed
```
**Solución**: Verifica email y contraseña. Si persiste, prueba a cambiar la contraseña en Octopus Energy.

### 🔄 **Datos no se actualizan**
**Solución**: 
1. Usa el botón "Actualizar Estado" del cargador
2. Ejecuta el servicio `octopus_ev_spain.refresh_charger`
3. Verifica conectividad a internet

### 🚗 **Cargador no aparece**
**Solución**: 
- Asegúrate de tener la tarifa Octopus Intelligent GO
- El cargador debe estar registrado en tu cuenta Octopus

### 📊 **Sensores muestran "unknown"**
**Solución**:
- Espera unos minutos tras la configuración inicial
- Algunos sensores requieren datos históricos (hasta 24h)

---

## 🤝 Contribuir

¿Encontraste un bug? ¿Tienes una idea? ¡Contribuye al proyecto!

1. **Fork** el repositorio
2. **Crea** una rama para tu feature
3. **Commit** tus cambios
4. **Push** a la rama
5. **Abre** un Pull Request

### 📝 **Reportar Issues**
[Abrir issue en GitHub](https://github.com/lockevod/ha-octopus-ev-spain/issues)

---

## 📜 Licencia

Este proyecto está bajo la licencia **MIT**. Ver [LICENSE](LICENSE) para más detalles.

---

## ⚠️ Disclaimer

Esta integración **NO ES OFICIAL** de Octopus Energy España. Es un proyecto comunitario desarrollado de forma independiente.

**El uso de esta integración es bajo tu propia responsabilidad**. Los desarrolladores no se hacen responsables de:
- Errores en el código o funcionamiento
- Interacciones no deseadas con la API de Octopus
- Consumos mayores de lo previsto
- Cualquier problema derivado del uso de la integración

Si no estás de acuerdo con estos términos, **no uses la integración**.

---

## 🙏 Agradecimientos

- **Basado en la idea original** de [MiguelAngelLV/ha-octopus-spain](https://github.com/MiguelAngelLV/ha-octopus-spain)
- **Comunidad Home Assistant España** por el feedback y testing
- **Octopus Energy** por su API (no oficial)

---

## 🔗 Enlaces Útiles

- 🏠 [Home Assistant](https://www.home-assistant.io/)
- 🛠️ [HACS](https://hacs.xyz/)
- ⚡ [Octopus Energy España](https://octopusenergy.es/)
- 📘 [Documentación Home Assistant](https://www.home-assistant.io/integrations/)

---

**¿Te gusta la integración?** ⭐ ¡Dale una estrella al repo!