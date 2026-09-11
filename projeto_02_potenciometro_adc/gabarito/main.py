"""
Projeto 02 - Leitura de potenciometro (ADC)
EmpreendAIoT / Instituto Hardware BR - Monitoria, Trilha IoT

Contexto: sensor de nivel de reservatorio.
Le um potenciometro no ADC, filtra por media movel, converte o valor raw em
tensao e em percentual de nivel, e reporta no log serial apenas quando o
percentual varia acima do threshold de reporte.
"""

import time
from machine import Pin, ADC, PWM

# --- parametros ajustaveis (valores de referencia, podem ser calibrados) ---
PIN_POT = 34                 # ADC1_CH6; no ESP32 o ADC2 nao funciona junto com Wi-Fi
PIN_LED = 23                 # indicador opcional de brilho proporcional
# A latencia do filtro e o PRODUTO dos dois valores abaixo: 50 ms x 5 = 250 ms
# de historia na media. Aumentar qualquer um dos dois deixa a leitura mais
# estavel e a resposta mais lenta.
PERIODO_AMOSTRA_MS = 50      # faixa usual 20 a 1000
N_MEDIA_MOVEL = 5            # faixa usual 4 a 32
THRESHOLD_REPORTE_PCT = 1.0  # faixa usual 0.5 a 5.0
PERIODO_HEARTBEAT_MS = 5000  # reimprime uma linha mesmo sem variacao, p/ provar que o loop
                             # vive; 0 desliga a linha periodica por completo
PWM_FREQ_HZ = 1000           # frequencia do PWM do LED indicador
USAR_LED = True              # componente opcional; False roda so com o potenciometro

# --- limites determinados: NAO alterar sem consultar a fonte citada ---
# Escala de read_u16(): a API do MicroPython reescala qualquer ADC para 0..65535,
# independentemente da resolucao fisica (docs machine.ADC). Todo o pipeline deste
# arquivo trabalha NESTA escala - misturar com a escala nativa 0..4095 e erro.
ADC_MAX_U16 = 65535
# Resolucao nativa do ADC do ESP32/Pico = 12 bits (0..4095). Consequencia: em
# read_u16() os valores nao andam de 1 em 1 - e quantizacao, nao ruido.
# Registrada aqui como referencia; nenhum calculo deste arquivo a utiliza.
ADC_BITS_NATIVOS = 12
# Tensao de referencia = 3,3 V, imposta pela placa (ESP32 DevKit V1).
V_REF_V = 3.3
# Escala de duty_u16() do PWM: 0..65535 (imposto pela API do MicroPython).
PWM_MAX_U16 = 65535


# --------------------------------------------------------------------------
# Conversao: funcao pura, nao acessa hardware (requisito funcional 6).
# Testavel isoladamente: converter(0) -> (0.0, 0.0); converter(65535) -> (3.3, 100.0)
# --------------------------------------------------------------------------
def converter(raw_u16):
    """Recebe o valor raw na escala u16 e devolve (tensao_v, percentual)."""
    if raw_u16 < 0:
        raw_u16 = 0
    elif raw_u16 > ADC_MAX_U16:
        raw_u16 = ADC_MAX_U16
    tensao_v = raw_u16 * V_REF_V / ADC_MAX_U16
    percentual = raw_u16 * 100.0 / ADC_MAX_U16
    return tensao_v, percentual


def montar_adc():
    adc = ADC(Pin(PIN_POT))
    # ATTN_11DB: unica atenuacao que cobre a faixa de entrada ate ~3,3 V no ESP32.
    # Com a atenuacao padrao (0 dB) a leitura satura por volta de 1,0 V.
    adc.atten(ADC.ATTN_11DB)
    return adc


def montar_led():
    if not USAR_LED:
        return None
    led = PWM(Pin(PIN_LED))
    led.freq(PWM_FREQ_HZ)
    led.duty_u16(0)
    return led


def imprimir_cabecalho():
    print("# projeto 02 - leitura de potenciometro (ADC)")
    print("# escala raw = read_u16() (0..{})".format(ADC_MAX_U16))
    print("# amostragem {} ms | media movel {} amostras | reporte > {:.1f} %".format(
        PERIODO_AMOSTRA_MS, N_MEDIA_MOVEL, THRESHOLD_REPORTE_PCT))
    print("{:>10} {:>8} {:>9} {:>8} {:>8}".format("t_ms", "raw", "tensao_V", "pct", "motivo"))


def imprimir_linha(t_ms, raw, tensao_v, pct, motivo):
    # Colunas de largura fixa (requisito 4): alinhamento a direita, casas decimais fixas.
    print("{:>10d} {:>8d} {:>9.2f} {:>7.1f}% {:>8}".format(t_ms, raw, tensao_v, pct, motivo))


def main():
    adc = montar_adc()
    led = montar_led()

    # --- media movel: fila das ultimas N_MEDIA_MOVEL leituras ---
    # A leitura nova entra no fim da lista e a mais antiga sai do comeco, de modo
    # que a lista nunca passa de N_MEDIA_MOVEL posicoes (requisito funcional 3).
    # Usar append() sem o pop() correspondente faria a memoria acabar depois de
    # algumas horas de execucao: o que limita o tamanho E O DESCARTE, nao o append.
    buf = []

    imprimir_cabecalho()

    t_boot = time.ticks_ms()
    # ticks_diff() e obrigatorio: o contador de ms do MicroPython sofre overflow
    # e a subtracao direta de marcas de tempo da resultado errado na virada.
    prox_amostra = t_boot
    ult_reporte = None          # percentual do ultimo reporte; None = nada reportado ainda
    t_ult_reporte = t_boot

    try:
        while True:
            agora = time.ticks_ms()
            if time.ticks_diff(agora, prox_amostra) < 0:
                continue        # ainda nao e hora de amostrar; loop nao bloqueante
            # Agenda a proxima amostra a partir da anterior: o periodo nao acumula atraso.
            prox_amostra = time.ticks_add(prox_amostra, PERIODO_AMOSTRA_MS)

            raw = adc.read_u16()

            buf.append(raw)                   # a leitura nova entra no fim
            if len(buf) > N_MEDIA_MOVEL:
                buf.pop(0)                    # a mais antiga sai do comeco

            raw_filtrado = sum(buf) // len(buf)
            tensao_v, pct = converter(raw_filtrado)

            if led is not None:
                # PWM_MAX_U16 e ADC_MAX_U16 sao ambos 65535, entao o valor
                # filtrado ja serve como duty sem conversao. Se as escalas
                # fossem diferentes, aqui entraria a regra de tres.
                led.duty_u16(raw_filtrado)

            if len(buf) < N_MEDIA_MOVEL:
                continue        # janela ainda enchendo: media nao representativa

            t_rel = time.ticks_diff(agora, t_boot)
            if ult_reporte is None:
                imprimir_linha(t_rel, raw_filtrado, tensao_v, pct, "inicial")
                ult_reporte, t_ult_reporte = pct, agora
            elif abs(pct - ult_reporte) >= THRESHOLD_REPORTE_PCT:
                imprimir_linha(t_rel, raw_filtrado, tensao_v, pct, "delta")
                ult_reporte, t_ult_reporte = pct, agora
            elif (PERIODO_HEARTBEAT_MS > 0 and
                  time.ticks_diff(agora, t_ult_reporte) >= PERIODO_HEARTBEAT_MS):
                imprimir_linha(t_rel, raw_filtrado, tensao_v, pct, "periodico")
                t_ult_reporte = agora
    except KeyboardInterrupt:
        print("# encerrado pelo usuario")
    finally:
        if led is not None:
            led.duty_u16(0)
            led.deinit()


main()
