"""
===============================================================================
Projeto 1 - Blink com Botão
Papel: Monitoria - Trilha IoT (EmpreendAIoT)
Placa: ESP32 DevKit V1

OBJETIVO:
Controlar um LED por meio de um botão, utilizando entrada e saída digital,
pull-up interno, debounce, lógica invertida e modo blink não bloqueante.

REQUISITOS ATENDIDOS:
1. LED inicia apagado e alterna a cada pressionamento.
2. Debounce por janela de tempo de 50 ms.
3. Um botão mantido pressionado não gera vários toggles.
4. Cada mudança de estado é registrada no terminal serial, com o tempo
   desde o boot e o número sequencial do evento.
5. Pressionamento longo ativa o modo BLINK sem uso de delay bloqueante.
   Um toque curto retorna ao modo NORMAL.
6. O LED é apagado ao encerrar a execução.

PRÉ-CONDIÇÕES:
- ESP32 DevKit V1.
- LED conectado ao GPIO 2 através de resistor de 220 Ω a 330 Ω.
- Botão conectado ao GPIO 4 e ao GND.
- Pull-up interno habilitado no GPIO 4.

Sem segredos e sem dados pessoais neste arquivo (ver README).
===============================================================================
"""

from machine import Pin
import time


# =============================================================================
# PARÂMETROS AJUSTÁVEIS 
# =============================================================================

DEBOUNCE_MS = 50        # Tempo mínimo para considerar o sinal estável (faixa usual 20-80 ms)
PRESS_LONGO_MS = 1500   # Tempo mínimo para caracterizar pressão longa
BLINK_HZ = 2             # Frequência do modo BLINK


# =============================================================================
# LIMITES DETERMINADOS: 
# =============================================================================

# Nível lógico da placa = 3,3 V.
#   Fonte: ESP32 Series Datasheet (Espressif Systems), seção de características
#   elétricas dos pinos GPIO. 
NIVEL_LOGICO_V = 3.3

# Com pull-up interno habilitado (Pin.PULL_UP):
# - botão solto     -> nível lógico 1
# - botão apertado   -> nível lógico 0
#   Fonte: documentação MicroPython, módulo machine.Pin (Pin.PULL_UP).
#   Comportamento imposto pela topologia do circuito, não é um parâmetro livre.
NIVEL_BOTAO_PRESSIONADO = 0

# O contador de milissegundos (time.ticks_ms()) sofre overflow periódico e
# reinicia; por isso a diferença entre duas marcas de tempo DEVE usar
# time.ticks_diff(), nunca subtração direta (b - a).
#   Fonte: documentação MicroPython, módulo time (ticks_ms / ticks_diff).
PERIODO_OVERFLOW_TICKS_MS = 2 ** 30  # limite documentado de time.ticks_ms()


# =============================================================================
# CONFIGURAÇÃO DOS PINOS
# =============================================================================

PIN_LED = 2
PIN_BOTAO = 4

led = Pin(PIN_LED, Pin.OUT)
btn = Pin(PIN_BOTAO, Pin.IN, Pin.PULL_UP)


# =============================================================================
# VARIÁVEIS DE ESTADO
# =============================================================================

led_state = False       # LED inicia apagado
blink_mode = False      # Sistema inicia no modo normal
evento_num = 0          # Número sequencial dos eventos

# Instante em que o programa foi iniciado
inicio = time.ticks_ms()

# Estado inicial do botão
raw_last = btn.value()
stable_state = raw_last

# Momento da última alteração detectada no sinal
last_change_time = inicio

# Momento em que o botão foi pressionado
pressed_at = None

# Período de alternância do LED no modo BLINK.
# A frequência é dividida por 2 porque cada troca corresponde
# a meio período da onda.
blink_period_ms = int(1000 / (2 * BLINK_HZ))

# Momento da última troca do LED no modo BLINK
last_blink_toggle = inicio


# =============================================================================
# FUNÇÕES
# =============================================================================

def aplicar_led(valor):
    """
    Atualiza o estado do LED.

    Parâmetro:
        valor (bool): True para acender e False para apagar.
    """
    global led_state

    led_state = valor
    led.value(1 if led_state else 0)


def log_evento(msg):
    """
    Registra um evento no terminal serial.

    O registro apresenta:
    - tempo decorrido desde o boot (calculado com ticks_diff, seguro contra overflow);
    - número sequencial do evento;
    - descrição do evento.
    """
    global evento_num

    evento_num += 1

    agora = time.ticks_ms()

    # ticks_diff() é utilizado para calcular corretamente a diferença
    # entre dois valores de ticks_ms(), mesmo em caso de overflow.
    tempo_desde_boot = time.ticks_diff(agora, inicio)

    print("[{:>8} ms] evento #{:03d} - {}".format(
        tempo_desde_boot,
        evento_num,
        msg
    ))


# =============================================================================
# INICIALIZAÇÃO
# =============================================================================

# Garante que o LED comece apagado.
aplicar_led(False)

log_evento("boot: LED apagado, modo normal")


# =============================================================================
# LOOP PRINCIPAL
# =============================================================================

try:

    while True:

        agora = time.ticks_ms()
        raw = btn.value()

        # ---------------------------------------------------------------------
        # DEBOUNCE
        # ---------------------------------------------------------------------
        # Detecta uma alteração no sinal bruto e aguarda DEBOUNCE_MS
        # antes de aceitar a alteração como um novo estado estável.

        if raw != raw_last:

            raw_last = raw
            last_change_time = agora

        elif (
            raw != stable_state
            and time.ticks_diff(agora, last_change_time) >= DEBOUNCE_MS
        ):

            # O sinal permaneceu estável pelo tempo necessário.
            stable_state = raw

            # -----------------------------------------------------------------
            # BOTÃO PRESSIONADO
            # -----------------------------------------------------------------

            if stable_state == NIVEL_BOTAO_PRESSIONADO:

                # Guarda o instante em que o botão foi pressionado.
                pressed_at = agora

            # -----------------------------------------------------------------
            # BOTÃO LIBERADO
            # -----------------------------------------------------------------

            else:

                if pressed_at is not None:

                    # Calcula por quanto tempo o botão permaneceu pressionado.
                    duracao = time.ticks_diff(agora, pressed_at)

                    pressed_at = None

                    # ---------------------------------------------------------
                    # PRESSÃO LONGA
                    # ---------------------------------------------------------

                    if duracao >= PRESS_LONGO_MS:

                        blink_mode = True
                        last_blink_toggle = agora

                        log_evento(
                            "pressionamento longo ({} ms) -> "
                            "modo BLINK ativado".format(duracao)
                        )

                    # ---------------------------------------------------------
                    # TOQUE CURTO
                    # ---------------------------------------------------------

                    else:

                        # Se estava no modo BLINK, retorna ao modo normal.
                        if blink_mode:

                            blink_mode = False
                            aplicar_led(False)

                            log_evento(
                                "toque curto ({} ms) -> "
                                "modo NORMAL (LED apagado)".format(duracao)
                            )

                        # Caso contrário, alterna o estado do LED.
                        else:

                            aplicar_led(not led_state)

                            log_evento(
                                "toque curto ({} ms) -> LED {}".format(
                                    duracao,
                                    "aceso" if led_state else "apagado"
                                )
                            )

        # ---------------------------------------------------------------------
        # MODO BLINK
        # ---------------------------------------------------------------------
        # O LED é alternado usando ticks_ms(), sem time.sleep().
        # Dessa forma, o programa continua verificando o botão normalmente.

        if blink_mode:

            if time.ticks_diff(agora, last_blink_toggle) >= blink_period_ms:

                last_blink_toggle = agora

                aplicar_led(not led_state)

# =============================================================================
# ENCERRAMENTO
# =============================================================================

except KeyboardInterrupt:

    # Permite encerrar o programa pelo terminal sem gerar erro.
    pass

finally:

    # Independentemente da forma de encerramento,
    # o LED deve terminar apagado.
    aplicar_led(False)

    log_evento("encerrando: LED apagado")
