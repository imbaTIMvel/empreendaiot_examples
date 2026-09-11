"""
Projeto 02 - Leitura de potenciometro (ADC)
EmpreendAIoT / Instituto Hardware BR - versao do aluno

Contexto: sensor de nivel de reservatorio.
Preencha os trechos marcados com "# TODO:". A estrutura do programa ja esta
pronta - o que falta sao as decisoes de projeto e as conversoes.

Leia o enunciado.md antes de comecar.
"""

import time
from machine import Pin, ADC, PWM

# --- parametros ajustaveis (valores de referencia, podem ser calibrados) ---
# TODO: escolha os pinos de acordo com o circuito que voce montou no Wokwi.
#       Atencao: no ESP32, use um pino do ADC1 (32 a 39). O ADC2 nao funciona
#       quando o Wi-Fi esta ligado.
PIN_POT = None               # TODO: pino do potenciometro
PIN_LED = None               # TODO: pino do LED indicador (componente opcional)

# TODO: defina os parametros de amostragem e reporte. Sugestoes do enunciado:
#       PERIODO_AMOSTRA_MS = 200 | N_MEDIA_MOVEL = 10 | THRESHOLD_REPORTE_PCT = 1
PERIODO_AMOSTRA_MS = None
N_MEDIA_MOVEL = None
THRESHOLD_REPORTE_PCT = None
PERIODO_HEARTBEAT_MS = 5000
PWM_FREQ_HZ = 1000
USAR_LED = True

# --- limites determinados: NAO alterar sem consultar a fonte citada ---
# TODO: preencha cada valor abaixo E o comentario com a fonte de onde ele veio.
#       Nenhum destes e escolha sua: sao impostos pela API, pela placa ou pelo
#       componente. Registre a fonte e a data da conferencia no README.
ADC_MAX_U16 = None           # TODO: valor maximo devolvido por read_u16(). Fonte: ?
ADC_BITS_NATIVOS = None      # TODO: resolucao fisica do ADC da placa. Fonte: ?
                             #       (so para registro no README; nenhum calculo a usa)
V_REF_V = None               # TODO: tensao de referencia da placa. Fonte: ?
PWM_MAX_U16 = 65535          # escala de duty_u16() (imposto pela API do MicroPython)


# --------------------------------------------------------------------------
# Conversao
# --------------------------------------------------------------------------
def converter(raw_u16):
    """Recebe o valor raw na escala u16 e devolve (tensao_v, percentual).

    TODO: implemente a conversao.
      - Esta funcao NAO pode acessar hardware: sem ADC, sem Pin, sem leitura.
        Ela recebe um numero e devolve numeros - so assim da para testa-la
        isoladamente, sem simulador.
      - Proteja contra valores fora da faixa (menores que 0, maiores que o maximo).
      - Confira o resultado nos extremos antes de seguir:
            converter(0)     deve dar (0.0, 0.0)
            converter(65535) deve dar (3.3, 100.0)
    """
    # TODO: limitar raw_u16 a faixa valida
    # TODO: tensao_v = ?
    # TODO: percentual = ?
    return 0.0, 0.0


def montar_adc():
    adc = ADC(Pin(PIN_POT))
    # TODO: no ESP32, configure a atenuacao do ADC para cobrir a faixa ate ~3,3 V.
    #       Sem isso a leitura satura bem antes do fim do curso do potenciometro -
    #       gire o potenciometro ate o fim e veja o que acontece antes de corrigir.
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
    # TODO: imprima um cabecalho com os nomes das colunas do log. A saida deve
    #       sair em colunas de largura fixa - use format() com largura declarada
    #       (ex.: "{:>8}"), nao concatenacao de strings.


def imprimir_linha(t_ms, raw, tensao_v, pct, motivo):
    # TODO: uma linha por reporte, nas mesmas larguras do cabecalho.
    #       tensao com 2 casas decimais, percentual com 1.
    pass


def main():
    adc = montar_adc()
    led = montar_led()

    # --- media movel: fila das ultimas N_MEDIA_MOVEL leituras ---
    buf = []

    imprimir_cabecalho()

    t_boot = time.ticks_ms()
    prox_amostra = t_boot
    ult_reporte = None
    t_ult_reporte = t_boot

    try:
        while True:
            agora = time.ticks_ms()
            # TODO: so amostre quando o periodo tiver vencido; nas outras
            #       voltas, um 'continue' devolve o loop ao topo.
            #       Compare as marcas de tempo com time.ticks_diff() e agende a
            #       proxima com time.ticks_add() - nunca com - e +. O contador de
            #       ms da a volta e a conta comum erra na virada.
            #       Leia a secao "Antes de comecar: como marcar o tempo sem
            #       travar o programa", no enunciado.md, antes de escrever isto.

            raw = adc.read_u16()

            # TODO: guarde a leitura na fila 'buf', mantendo nela apenas as
            #       N_MEDIA_MOVEL leituras mais recentes:
            #         1. a leitura nova entra no FIM da lista (append)
            #         2. se a lista passou de N_MEDIA_MOVEL, a mais antiga sai
            #            do COMECO (pop na posicao 0)
            #       A regra do projeto e que a estrutura nao cresca
            #       indefinidamente: o append sozinho faz a lista crescer ate a
            #       placa ficar sem memoria. E o descarte que segura o tamanho.

            # TODO: raw_filtrado = media da fila. Divida pela quantidade de
            #       leituras que existem AGORA na lista, nao por N_MEDIA_MOVEL -
            #       nos primeiros ciclos a fila ainda esta enchendo.
            raw_filtrado = 0
            tensao_v, pct = converter(raw_filtrado)

            if led is not None:
                # TODO: brilho proporcional a leitura filtrada.
                #       Antes de escrever a conta, compare as duas escalas: a do
                #       ADC (ADC_MAX_U16) e a do PWM (PWM_MAX_U16). Se forem
                #       iguais, nao ha conversao a fazer.
                pass

            # TODO: enquanto a fila nao tiver N_MEDIA_MOVEL leituras, nao
            #       reporte - a media de 2 ou 3 amostras ainda nao representa nada.

            t_rel = time.ticks_diff(agora, t_boot)
            # TODO: sao tres os motivos para imprimir uma linha, nessa ordem:
            #         1. e a primeira leitura valida (ainda nao houve reporte);
            #         2. o percentual mudou mais que THRESHOLD_REPORTE_PCT desde
            #            a ULTIMA LINHA IMPRESSA - sem isso o log vira uma
            #            enxurrada de linhas iguais;
            #         3. passaram PERIODO_HEARTBEAT_MS sem nenhuma linha - um log
            #            mudo e indistinguivel de um programa travado.
            #       Os tres sao excludentes (if/elif/elif): no maximo uma linha
            #       por ciclo. Guarde o percentual e o instante de cada reporte
            #       para as comparacoes do proximo ciclo.
    except KeyboardInterrupt:
        print("# encerrado pelo usuario")
    finally:
        if led is not None:
            led.duty_u16(0)
            led.deinit()


main()
