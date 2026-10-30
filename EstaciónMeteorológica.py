import network
import time
from machine import Pin
import dht
from umqtt.simple import MQTTClient

# ------------------------------------------------------------------
# CONFIGURACIÓN WIFI + MQTT
# ------------------------------------------------------------------
SSID = "HERRERAR"
PASSWORD = "I63558232@1002@"

MQTT_SERVER = "mqtt.apps.willedtech.io"
MQTT_PORT = 1884

CLIENT_ID = b"ECSPC0"

TOPIC_TEMP = b"/ThinkIOT/temp"
TOPIC_HUM = b"/ThinkIOT/hum"
TOPIC_PUB = b"/ThinkIOT/Publish"
TOPIC_SUB = b"/ThinkIOT/Subscribe"

PUBLISH_INTERVAL = 2000  # ms (2 s)

# ------------------------------------------------------------------
# CONFIGURACIÓN DHT11 (Temperatura y Humedad)
# ------------------------------------------------------------------
DHT_PIN = 15
sensor_dht = dht.DHT11(Pin(DHT_PIN))  # <-- SOLO DHT11

# ------------------------------------------------------------------
# TODO lo demás (LDR, LEDs, OLED, Lux) QUEDA COMENTADO
# ------------------------------------------------------------------

# import math
# from machine import ADC, I2C
# import ssd1306

# # ---------------- LDR + BARRA DE LEDs ----------------
# R_FIXED = 10_000
# led_pins = [13, 12, 14, 27, 26, 25, 33, 32, 23, 19]
# leds = [Pin(pin, Pin.OUT) for pin in led_pins]
#
# def clear_leds():
#     for led in leds:
#         led.value(0)
#
# def light_up_to(n):
#     clear_leds()
#     n = min(max(n, 0), len(leds))
#     for i in range(n):
#         leds[i].value(1)
#
# adc = ADC(Pin(34))
# adc.atten(ADC.ATTN_11DB)
#
# rl10  = 50e3
# gamma = 0.7
#
# def calculate_resistance():
#     value = adc.read()
#     if value <= 0:
#         value = 1
#     if value >= 4095:
#         value = 4094
#     voltage_ratio = value / (4095 - value)
#     return R_FIXED * voltage_ratio
#
# def calculate_lux(resistance):
#     return 10 * math.pow(rl10 / resistance, 1 / gamma)
#
# points = [
#     (0.1,     1.25e6),
#     (1,       250e3),
#     (10,      50e3),
#     (50,      16.2e3),
#     (100,     9.98e3),
#     (400,     3.78e3),
#     (1000,    1.99e3),
#     (10000,   397),
#     (100000,  79),
# ]
#
# def linear_interpolation(resistance):
#     if resistance >= 1.25e6:
#         light_up_to(1)
#         return 0.1
#     if resistance <= 79:
#         light_up_to(10)
#         return 100000
#     for i in range(len(points) - 1):
#         lux1, r1 = points[i]
#         lux2, r2 = points[i + 1]
#         if r2 <= resistance <= r1:
#             light_up_to(i + 2)
#             return lux1 + ((resistance - r1) / (r2 - r1)) * (lux2 - lux1)
#     return calculate_lux(resistance)
#
# LDR_INTERVAL = 2000

# # ---------------- OLED SSD1306 ----------------
# i2c = I2C(0, scl=Pin(22), sda=Pin(21))
# oled = ssd1306.SSD1306_I2C(128, 64, i2c)
#
# def update_oled(temp, hum, lux):
#     oled.fill(0)
#     oled.text("  ECSPC0  ",  10, 0)
#     oled.text("T: {:>5.1f} C".format(temp),  0, 16)
#     oled.text("H: {:>5.1f} %".format(hum),   0, 28)
#     oled.text("Lux:{:>7.1f}".format(lux),    0, 40)
#     oled.show()
#
# OLED_INTERVAL = 1000


# ------------------------------------------------------------------
# WIFI
# ------------------------------------------------------------------
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    if not wlan.active():
        wlan.active(True)
    if not wlan.isconnected():
        print("[{} ms] Conectando a WiFi: {}".format(time.ticks_ms(), SSID))
        wlan.connect(SSID, PASSWORD)

        start = time.ticks_ms()
        while not wlan.isconnected():
            if time.ticks_diff(time.ticks_ms(), start) > 15000:
                raise OSError("Timeout conectando a WiFi (15s)")
            print("[{} ms] ... esperando WiFi".format(time.ticks_ms()))
            time.sleep(0.5)
    ip = wlan.ifconfig()[0]
    print("[{} ms] WiFi conectado. IP: {}".format(time.ticks_ms(), ip))
    return wlan


def ensure_wifi(wlan):
    if not wlan.isconnected():
        print("[{} ms] WiFi desconectado. Reintentando...".format(time.ticks_ms()))
        wlan.disconnect()
        wlan.connect(SSID, PASSWORD)

        start = time.ticks_ms()
        while not wlan.isconnected():
            if time.ticks_diff(time.ticks_ms(), start) > 15000:
                raise OSError("Timeout reconectando a WiFi (15s)")
            print("[{} ms] ... reconectando WiFi".format(time.ticks_ms()))
            time.sleep(0.5)
        print(
            "[{} ms] WiFi OK otra vez. IP: {}".format(
                time.ticks_ms(), wlan.ifconfig()[0]
            )
        )


# ------------------------------------------------------------------
# MQTT
# ------------------------------------------------------------------
def mqtt_callback(topic, msg):
    # Mostrar claramente por serial lo que llega
    try:
        t = topic.decode()
    except:
        t = str(topic)
    try:
        m = msg.decode()
    except:
        m = str(msg)
    print("[{} ms] MQTT RX -> {} : {}".format(time.ticks_ms(), t, m))


def connect_mqtt():
    print(
        "[{} ms] Conectando MQTT {}:{} ...".format(
            time.ticks_ms(), MQTT_SERVER, MQTT_PORT
        )
    )

    client = MQTTClient(
        client_id=CLIENT_ID, server=MQTT_SERVER, port=MQTT_PORT, keepalive=60
    )
    client.set_callback(mqtt_callback)
    client.connect()

    print("[{} ms] MQTT conectado.".format(time.ticks_ms()))
    client.publish(TOPIC_PUB, b"Welcome from MicroPython (DHT11 only)")
    client.subscribe(TOPIC_SUB)
    print("[{} ms] Suscrito a {}".format(time.ticks_ms(), TOPIC_SUB))

    return client


# ------------------------------------------------------------------
# BUCLE PRINCIPAL (SOLO DHT11 + MQTT)
# ------------------------------------------------------------------
def main():
    wlan = connect_wifi()
    client = None

    last_pub = time.ticks_ms()

    # Valores actuales
    current_temp = None
    current_hum = None

    print("[{} ms] Iniciando bucle principal (DHT11) ...".format(time.ticks_ms()))

    while True:
        try:
            ensure_wifi(wlan)

            # Asegurar cliente MQTT
            if client is None:
                client = connect_mqtt()
            # Revisar mensajes entrantes
            client.check_msg()

            now = time.ticks_ms()

            # ---- Lectura DHT11 + envío MQTT ----
            if time.ticks_diff(now, last_pub) > PUBLISH_INTERVAL:
                last_pub = now
                print("[{} ms] Leyendo DHT11 ...".format(now))

                try:
                    sensor_dht.measure()
                    current_temp = sensor_dht.temperature()
                    current_hum = sensor_dht.humidity()
                except OSError as e:
                    print("[{} ms] Error leyendo DHT11: {}".format(time.ticks_ms(), e))
                else:
                    # DHT11 suele ser entero; lo formateamos igualmente
                    temp_str = "{:.1f}".format(float(current_temp))
                    hum_str = "{:.1f}".format(float(current_hum))

                    client.publish(TOPIC_TEMP, temp_str.encode())
                    client.publish(TOPIC_HUM, hum_str.encode())

                    print(
                        "[{} ms] MQTT TX -> TEMP: {} C".format(
                            time.ticks_ms(), temp_str
                        )
                    )
                    print(
                        "[{} ms] MQTT TX -> HUM : {} %".format(time.ticks_ms(), hum_str)
                    )
            time.sleep_ms(50)
        except OSError as e:
            print("[{} ms] Error en bucle principal: {}".format(time.ticks_ms(), e))

            # Intentar desconectar MQTT si existe
            try:
                if client is not None:
                    client.disconnect()
            except:
                pass
            client = None
            # Reintento rápido (puedes subirlo si deseas)
            print("[{} ms] Reintentando en 5s...".format(time.ticks_ms()))
            time.sleep(5)


if __name__ == "__main__":
    main()
