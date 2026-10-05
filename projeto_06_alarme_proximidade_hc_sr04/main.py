"""
===============================================================================
Projeto 6 - Alarme de Proximidade com HC-SR04
Papel: Monitoria - Trilha IoT (EmpreendAIoT)
Placa: ESP32 DevKit V1

OBJETIVO:
Medição de distância por time-of-flight com o sensor HC-SR04, validação de
leituras, filtragem por mediana, classificação em faixas com hysteresis e
sinalização (LEDs + buzzer + OLED) sem uso de delay bloqueante. Push-button
para silenciar o buzzer (modo mute).

REQUISITOS ATENDIDOS:
1. Medição de distância em cm a intervalo fixo (PERIODO_MEDICAO_MS).
2. Leituras fora da faixa válida do sensor, ou timeout, são descartadas e
   contabilizadas, sem entrar no cálculo.
3. A distância usada na decisão é a mediana das últimas N medições válidas.
4. Três faixas (segura / atenção / crítica) com thresholds em constantes e
   hysteresis na transição, para oscilação perto do threshold não trocar
   a classificação repetidamente.
5. Buzzer com cadência crescente conforme a aproximação, som contínuo na
   faixa crítica, sem qualquer delay bloqueante.
6. Indicação visual da faixa atual (LEDs + OLED) e log serial apenas nas
   transições, com a distância que causou a mudança; implementado como
   state machine com estados nomeados (SEGURA / ATENCAO / CRITICA).

OPCIONAIS INCLUÍDOS:
- Três LEDs (verde/amarelo/vermelho) sinalizando a faixa atual.
- Push-button para alternar o modo MUTE (silencia o buzzer; LEDs e log
  continuam normais).
- Display OLED (SSD1306, I2C) mostrando distância, estado e modo mute.

PRÉ-CONDIÇÕES:
- ESP32 DevKit V1.
- HC-SR04: VCC -> VIN (5V), GND -> GND, TRIG -> GPIO5, ECHO -> GPIO18.
- LED verde -> GPIO2, LED amarelo -> GPIO4, LED vermelho -> GPIO15
  (cada um com resistor de 220 Ω a 330 Ω).
- Buzzer ativo -> GPIO19.
- Push-button de mute -> GPIO23 e GND, com pull-up interno.
- OLED SSD1306 (I2C): SDA -> GPIO21, SCL -> GPIO22, VCC -> 3V3, GND -> GND.

AVISO DE HARDWARE REAL (não se aplica ao simulador Wokwi):
O HC-SR04 opera a 5 V e o pino ECHO reflete esse nível. O ESP32 NÃO tolera
5 V nos GPIOs (datasheet ESP32: tensão máxima de entrada dos pinos). Em uma
montagem física, use um divisor resistivo (ex.: 1 kΩ e 2 kΩ) entre o ECHO
do sensor e o GPIO do ESP32. No Wokwi isso não é necessário, porque o
simulador não modela dano por sobretensão.

Sem segredos e sem dados pessoais neste arquivo (ver README).
===============================================================================
"""

from machine import Pin, SoftI2C, time_pulse_us
import time

try:
    import ssd1306
except ImportError as erro_import:
    ssd1306 = None
    print("[ AVISO ] modulo ssd1306 nao encontrado: {} - alarme continua sem display".format(
        erro_import))


# =============================================================================
# PARÂMETROS AJUSTÁVEIS (valores de referência, podem ser calibrados)
# =============================================================================

PERIODO_MEDICAO_MS = 100      # intervalo entre medições
N_MEDIANA = 5                  # tamanho da janela para a mediana (sugerido 3 a 5)

THRESHOLD_ATENCAO_CM = 50      # abaixo disso -> faixa ATENCAO
THRESHOLD_CRITICO_CM = 20      # abaixo disso -> faixa CRITICA

HYSTERESE_ATENCAO_CM = 5       # margem para voltar de ATENCAO para SEGURA
HYSTERESE_CRITICO_CM = 5       # margem para voltar de CRITICA para ATENCAO

CADENCIA_MIN_MS = 500          # cadência do buzzer no início da faixa ATENCAO (mais lenta)
CADENCIA_MAX_MS = 100          # cadência do buzzer perto da faixa CRITICA (mais rápida)

DEBOUNCE_MS = 50                # janela de estabilização do botão de mute (faixa usual 20-80 ms)


# =============================================================================
# LIMITES DETERMINADOS: NÃO alterar sem consultar a fonte citada
# =============================================================================

# Faixa de medição do sensor: 2 cm a 400 cm. Fora desse intervalo a leitura
# é inválida por princípio de funcionamento do sensor, não por escolha de
# projeto.
#   Fonte: datasheet HC-SR04 (conferir também no editor Wokwi, aba do
#   componente, que permite ajustar a distância simulada entre 2 e 400 cm).
ALCANCE_MIN_CM = 2
ALCANCE_MAX_CM = 400

# Duração mínima do pulso de trigger para o sensor iniciar uma medição: 10 µs.
#   Fonte: datasheet HC-SR04.
PULSO_TRIGGER_US = 10

# Velocidade do som ≈ 343 m/s a 20 °C, o que equivale a ≈58 µs por
# centímetro de percurso de ida e volta (o pulso do ECHO mede o trajeto de
# ida + volta; a distância até o objeto é a metade do percurso medido).
#   Fonte: física do fenômeno (velocidade do som no ar), valor de referência
#   usado no datasheet do HC-SR04.
US_POR_CM_IDA_E_VOLTA = 58

# A ausência de eco (nada refletiu o pulso, ou objeto fora de alcance) faz o
# pino ECHO nunca completar o pulso; sem um timeout na medição, o programa
# trava esperando indefinidamente.
#   Calculado a partir do alcance máximo do sensor (ALCANCE_MAX_CM) e da
#   constante US_POR_CM_IDA_E_VOLTA, com 30% de margem de segurança.
TIMEOUT_ECHO_US = int(ALCANCE_MAX_CM * US_POR_CM_IDA_E_VOLTA * 1.3)

# Com pull-up interno habilitado (Pin.PULL_UP) no botão de mute:
# - botão solto     -> nível lógico 1
# - botão apertado   -> nível lógico 0
#   Fonte: documentação MicroPython, módulo machine.Pin (Pin.PULL_UP).
#   Comportamento imposto pela topologia do circuito, não é um parâmetro livre.
NIVEL_BOTAO_PRESSIONADO = 0


# =============================================================================
# CONFIGURAÇÃO DOS PINOS
# =============================================================================

PIN_TRIG = 5
PIN_ECHO = 18
PIN_LED_VERDE = 2
PIN_LED_AMARELO = 4
PIN_LED_VERMELHO = 15
PIN_BUZZER = 19
PIN_BOTAO_MUTE = 23
PIN_I2C_SDA = 21
PIN_I2C_SCL = 22

trig = Pin(PIN_TRIG, Pin.OUT)
echo = Pin(PIN_ECHO, Pin.IN)

led_verde = Pin(PIN_LED_VERDE, Pin.OUT)
led_amarelo = Pin(PIN_LED_AMARELO, Pin.OUT)
led_vermelho = Pin(PIN_LED_VERMELHO, Pin.OUT)
buzzer = Pin(PIN_BUZZER, Pin.OUT)
btn_mute = Pin(PIN_BOTAO_MUTE, Pin.IN, Pin.PULL_UP)

i2c = SoftI2C(scl=Pin(PIN_I2C_SCL), sda=Pin(PIN_I2C_SDA), freq=400000)

oled = None      # None = display indisponível; o alarme funciona sem ele
oled_ok = True   # controla para logar a falha apenas 1 vez

try:
    if ssd1306 is not None:
        oled = ssd1306.SSD1306_I2C(128, 64, i2c)
    else:
        oled_ok = False
except Exception as erro_oled_init:
    oled_ok = False
    print("[ AVISO ] OLED nao inicializou: {} - alarme continua sem display".format(
        erro_oled_init))

trig.value(0)
buzzer.value(0)


# =============================================================================
# VARIÁVEIS DE ESTADO
# =============================================================================

inicio = time.ticks_ms()              # referência para "tempo desde o boot"
evento_num = 0                        # número sequencial dos eventos logados

estado = "SEGURA"                     # estado inicial da state machine
mutado = False                        # modo mute inicia desligado

leituras_validas = []                 # janela das últimas N leituras válidas (cm)
leituras_descartadas = 0              # contador de leituras fora de faixa / timeout
ultima_distancia = None               # última leitura válida, só para mostrar no OLED

ultima_medicao = time.ticks_ms()      # controla o intervalo não bloqueante de medição
ultimo_beep_toggle = time.ticks_ms()  # controla a cadência não bloqueante do buzzer
buzzer_ligado = False

# Debounce do botão de mute
raw_last_botao = btn_mute.value()
stable_botao = raw_last_botao
last_change_botao = time.ticks_ms()


# =============================================================================
# FUNÇÕES
# =============================================================================

def log_evento(msg):
    """Registra um evento no terminal serial: tempo desde o boot + número
    sequencial + descrição."""
    global evento_num

    evento_num += 1
    tempo_desde_boot = time.ticks_diff(time.ticks_ms(), inicio)

    print("[{:>8} ms] evento #{:03d} - {}".format(
        tempo_desde_boot, evento_num, msg
    ))


def medir_distancia_cm():
    """
    Dispara o pulso de trigger e mede a duração do eco.
    Retorna a distância em cm, ou None se a leitura for inválida
    (timeout ou fora da faixa do sensor) — nesse caso a leitura é
    descartada e contabilizada, sem entrar no cálculo da mediana.
    """
    global leituras_descartadas

    trig.value(0)
    time.sleep_us(2)
    trig.value(1)
    time.sleep_us(PULSO_TRIGGER_US)
    trig.value(0)

    # time_pulse_us mede a duração de um pulso e retorna um valor
    # negativo em caso de timeout (-1: eco nunca começou; -2: eco
    # começou mas não terminou dentro do prazo).
    duracao_us = time_pulse_us(echo, 1, TIMEOUT_ECHO_US)

    if duracao_us < 0:
        leituras_descartadas += 1
        return None

    distancia_cm = duracao_us / US_POR_CM_IDA_E_VOLTA

    if distancia_cm < ALCANCE_MIN_CM or distancia_cm > ALCANCE_MAX_CM:
        leituras_descartadas += 1
        return None

    return distancia_cm


def mediana(valores):
    """Mediana de uma lista de números."""
    ordenados = sorted(valores)
    n = len(ordenados)
    meio = n // 2
    if n % 2 == 1:
        return ordenados[meio]
    return (ordenados[meio - 1] + ordenados[meio]) / 2


def proximo_estado(estado_atual, distancia):
    """
    State machine de 3 estados com hysteresis: aproximar (descer de faixa)
    reage imediatamente pelo threshold puro, por segurança; afastar (subir
    de faixa) exige passar do threshold + margem, para a oscilação perto
    da fronteira não trocar a classificação repetidamente.
    """
    if estado_atual == "SEGURA":
        if distancia <= THRESHOLD_ATENCAO_CM:
            return "ATENCAO"
        return "SEGURA"

    if estado_atual == "ATENCAO":
        if distancia <= THRESHOLD_CRITICO_CM:
            return "CRITICA"
        if distancia > THRESHOLD_ATENCAO_CM + HYSTERESE_ATENCAO_CM:
            return "SEGURA"
        return "ATENCAO"

    # estado_atual == "CRITICA"
    if distancia > THRESHOLD_CRITICO_CM + HYSTERESE_CRITICO_CM:
        return "ATENCAO"
    return "CRITICA"


def aplicar_leds(estado_atual):
    led_verde.value(1 if estado_atual == "SEGURA" else 0)
    led_amarelo.value(1 if estado_atual == "ATENCAO" else 0)
    led_vermelho.value(1 if estado_atual == "CRITICA" else 0)


def cadencia_buzzer(distancia):
    """
    Interpola a cadência do buzzer entre CADENCIA_MIN_MS (início da faixa
    ATENCAO, mais longe) e CADENCIA_MAX_MS (perto da faixa CRITICA).
    """
    faixa = THRESHOLD_ATENCAO_CM - THRESHOLD_CRITICO_CM
    if faixa <= 0:
        return CADENCIA_MIN_MS

    proporcao = (THRESHOLD_ATENCAO_CM - distancia) / faixa
    proporcao = max(0, min(1, proporcao))

    return int(CADENCIA_MIN_MS - proporcao * (CADENCIA_MIN_MS - CADENCIA_MAX_MS))


def atualizar_display(distancia_cm, estado_atual, mutado_atual, descartadas):
    """
    Mostra distância, estado atual, modo mute e leituras descartadas no OLED.
    Se o OLED não estiver disponível (não inicializou), a função não faz
    nada — o alarme (LEDs/buzzer) continua funcionando normalmente.
    Uma falha na escrita I2C também NÃO derruba o alarme; o erro é logado
    uma única vez no serial para diagnóstico.
    """
    global oled_ok

    if oled is None:
        return

    try:
        oled.fill(0)
        oled.text("Alarme HC-SR04", 0, 0)

        if distancia_cm is not None:
            oled.text("Dist: {:.1f} cm".format(distancia_cm), 0, 16)
        else:
            oled.text("Dist: --", 0, 16)

        oled.text("Estado: {}".format(estado_atual), 0, 30)
        oled.text("Mute: {}".format("ON" if mutado_atual else "OFF"), 0, 44)
        oled.text("Descartadas: {}".format(descartadas), 0, 56)

        oled.show()

    except Exception as erro:
        if oled_ok:
            oled_ok = False
            log_evento("falha ao atualizar OLED: {}".format(erro))


# =============================================================================
# INICIALIZAÇÃO
# =============================================================================

aplicar_leds(estado)
atualizar_display(ultima_distancia, estado, mutado, leituras_descartadas)
log_evento("boot: estado inicial {}".format(estado))


# =============================================================================
# LOOP PRINCIPAL
# =============================================================================

try:

    while True:

        agora = time.ticks_ms()

        # ---------------------------------------------------------------
        # BOTÃO DE MUTE (debounce, mesmo padrão do Projeto 1)
        # ---------------------------------------------------------------

        raw_botao = btn_mute.value()

        if raw_botao != raw_last_botao:
            raw_last_botao = raw_botao
            last_change_botao = agora
        elif (
            raw_botao != stable_botao
            and time.ticks_diff(agora, last_change_botao) >= DEBOUNCE_MS
        ):
            stable_botao = raw_botao

            if stable_botao == NIVEL_BOTAO_PRESSIONADO:
                mutado = not mutado
                log_evento("botao mute pressionado -> mute {}".format(
                    "ON" if mutado else "OFF"
                ))

        # ---------------------------------------------------------------
        # MEDIÇÃO A INTERVALO FIXO (não bloqueante)
        # ---------------------------------------------------------------

        if time.ticks_diff(agora, ultima_medicao) >= PERIODO_MEDICAO_MS:

            ultima_medicao = agora

            distancia = medir_distancia_cm()

            if distancia is not None:

                ultima_distancia = distancia
                leituras_validas.append(distancia)
                if len(leituras_validas) > N_MEDIANA:
                    leituras_validas.pop(0)

                if len(leituras_validas) == N_MEDIANA:

                    distancia_mediana = mediana(leituras_validas)
                    novo_estado = proximo_estado(estado, distancia_mediana)

                    if novo_estado != estado:

                        estado = novo_estado
                        aplicar_leds(estado)

                        log_evento(
                            "transicao -> {} (distancia mediana: {:.1f} cm)".format(
                                estado, distancia_mediana
                            )
                        )

            atualizar_display(ultima_distancia, estado, mutado, leituras_descartadas)

        # ---------------------------------------------------------------
        # BUZZER (não bloqueante; cadência/comportamento depende do estado)
        # ---------------------------------------------------------------

        if mutado:

            buzzer.value(0)
            buzzer_ligado = False

        elif estado == "SEGURA":

            buzzer.value(0)
            buzzer_ligado = False

        elif estado == "CRITICA":

            # Som contínuo na faixa crítica.
            buzzer.value(1)
            buzzer_ligado = True

        elif estado == "ATENCAO" and len(leituras_validas) == N_MEDIANA:

            cadencia_ms = cadencia_buzzer(mediana(leituras_validas))

            if time.ticks_diff(agora, ultimo_beep_toggle) >= cadencia_ms:
                ultimo_beep_toggle = agora
                buzzer_ligado = not buzzer_ligado
                buzzer.value(1 if buzzer_ligado else 0)


# =============================================================================
# ENCERRAMENTO
# =============================================================================

except KeyboardInterrupt:

    pass

finally:

    buzzer.value(0)
    led_verde.value(0)
    led_amarelo.value(0)
    led_vermelho.value(0)

    if oled is not None:
        try:
            oled.fill(0)
            oled.text("Encerrado", 0, 0)
            oled.show()
        except Exception:
            pass

    log_evento("encerrando: buzzer, LEDs e display desligados")
