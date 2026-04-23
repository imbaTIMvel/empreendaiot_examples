import network
import urequests
import time
import math
from machine import Pin, ADC
import dht

# --- WiFi ---
SSID = "Wokwi-GUEST"
PASSWORD = ""

# --- API ---
API_URL = "SUA-URL-AQUI" # INSERIR URL !!!

# --- Sensores ---
dht_sensor = dht.DHT22(Pin(4))
ldr = ADC(Pin(34))
ldr.atten(ADC.ATTN_11DB)

# --- Atuadores ---
fan = Pin(16, Pin.OUT)          # GRN LED = VENTILADOR
light = Pin(17, Pin.OUT)        # RED LED = LUZ
humidifier = Pin(18, Pin.OUT)   # BLU LED = ÁGUA

# --- Thresholds (fallback local) ---
thresholds = {
    "temp_min": 20,
    "temp_max": 30,
    "humidity_min": 50,
    "humidity_max": 80,
    "light_min": 8000
}

# --- Conectar WiFi ---
def connect_wifi():
    wifi = network.WLAN(network.STA_IF)
    wifi.active(True)
    wifi.connect(SSID, PASSWORD)
    
    while not wifi.isconnected():
        print("Conectando...")
        time.sleep(1)
    
    print("Conectado!", wifi.ifconfig())

# --- Receber entrada ---
def get_plant_name():
    try:
        plant = input("Digite o nome da planta: ")
        return plant.strip()
    except:
        return "tomate"     # Fallback

# --- Buscar thresholds ---
def fetch_thresholds_from_ai(plant_name):
    global thresholds
    try:
        url = f"{API_URL}?name={plant_name}"
        print("Consultando IA:", url)

        response = urequests.get(url)
        data = response.json()

        if "temp_min" in data:
            thresholds = data
            print("Thresholds atualizados:", thresholds)
        else:
            print("Resposta inválida:", data)

    except Exception as e:
        print("Erro ao buscar thresholds via IA:", e)

# --- Controle inteligente ---
def control(temp, hum, light_val):
    fan.value(temp > thresholds["temp_max"])
    humidifier.value(hum < thresholds["humidity_min"])
    light.value(light_val < thresholds["light_min"])

# --- Conversão de leitura ADC do sensor LDR (fotorresistor) p/ lux ---
# Tabela (lux, leitura ADC convertida)
calibration_table = [
    (0.1, 512), (0.2, 720), (0.5, 1520), (1, 2848), 
    (2, 3632), (5, 7409), (10, 10914), (20, 16051),
    (50, 25030), (100, 32808), (200, 40569), (500, 49548),
    (1000, 54653), (2000, 58366), (5000, 61567), (10000, 63039),
    (20000, 63967), (50000, 64703), (100000, 65023)
]
# Algoritmo de conversão
def light_to_lux(light):
    table = calibration_table
    # Limites
    if light <= table[0][1]:
        return table[0][0]
    if light >= table[-1][1]:
        return table[-1][0]
    # Busca de intervalo
    for i in range(len(table) - 1):
        lux1, adc1 = table[i]
        lux2, adc2 = table[i + 1]
        if adc1 <= light <= adc2:
            lux = lux1 + (light - adc1) * (lux2 - lux1) / (adc2 - adc1)
            return lux
    return 0 # Fallback

# --- Loop principal ---
connect_wifi()

plant_name = get_plant_name()
fetch_thresholds_from_ai(plant_name)

while True:
    try:
        dht_sensor.measure()
        temp = dht_sensor.temperature()
        hum = dht_sensor.humidity()
        light_val = light_to_lux(65535 - ldr.read_u16())

        print("Temp:", temp, "Hum:", hum, "Luz:", light_val)

        control(temp, hum, light_val)

    except Exception as e:
        print("Erro:", e)

    time.sleep(5)
