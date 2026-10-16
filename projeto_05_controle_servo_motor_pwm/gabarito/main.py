"""Projeto 05 - Controle de servo por PWM. Pico RP2040 / MicroPython.

Monitoria - Trilha IoT. Comando de uma persiana didatica.
O angulo informado e o COMANDADO, nao uma medicao do eixo.
Botao vermelho: retorna a posicao segura e encerra antes de clicar Stop.
"""
import time
from machine import ADC, PWM, Pin

# --- parametros ajustaveis (valores de referencia, podem ser calibrados) ---
PIN_POT = 26
PIN_SERVO = 15
PIN_ENCERRAR = 14
PERIODO_COMANDO_MS = 20
PASSO_MAX_GRAUS = 2.0
DEADBAND_PCT = 1.5
ANGULO_SEGURO = 0.0       # persiana fechada no modelo didatico
TEMPO_ACOMODACAO_MS = 500 # manter pulsos depois do ultimo passo de retorno
MODO_CALIBRACAO = False  # True: percorre 0, 90, 180 graus; depois encerra
TEMPO_CALIBRACAO_MS = 3000
# Valores NOMINAIS da especificacao, ainda sujeitos ao teste no Wokwi.
# Registrar a calibracao observada no README; nao sao universais para servos.
PULSO_MIN_US = 500
PULSO_MAX_US = 2500

# --- limites determinados: NAO alterar sem consultar a fonte citada ---
# Wokwi: https://docs.wokwi.com/parts/wokwi-servo
ANGULO_MIN = 0.0
ANGULO_MAX = 180.0
# Especificacao do projeto 05, p. 4: usar 50 Hz / 20 ms.
PWM_FREQ_HZ = 50
# API: https://docs.micropython.org/en/v1.27.0/library/machine.ADC.html
ADC_MAX_U16 = 65535
# API: https://docs.micropython.org/en/v1.27.0/library/machine.PWM.html
PWM_MAX_U16 = 65535
# Conversao de unidades e escala percentual (definicoes matematicas).
US_POR_SEGUNDO = 1000000
PCT_TOTAL = 100.0
PERIODO_PWM_US = US_POR_SEGUNDO // PWM_FREQ_HZ


def validar_configuracao():
    if not ANGULO_MIN <= ANGULO_SEGURO <= ANGULO_MAX:
        raise ValueError("ANGULO_SEGURO fora do curso")
    if not 0 < PASSO_MAX_GRAUS <= ANGULO_MAX - ANGULO_MIN:
        raise ValueError("PASSO_MAX_GRAUS invalido")
    if not 0 <= DEADBAND_PCT < PCT_TOTAL:
        raise ValueError("DEADBAND_PCT invalido")
    if not isinstance(PERIODO_COMANDO_MS, int) or PERIODO_COMANDO_MS < 20:
        raise ValueError("PERIODO_COMANDO_MS deve ser inteiro >= 20")
    if not 0 < PULSO_MIN_US < PULSO_MAX_US < PERIODO_PWM_US:
        raise ValueError("Faixa de pulsos invalida")
    if not isinstance(PULSO_MIN_US, int) or not isinstance(PULSO_MAX_US, int):
        raise ValueError("Pulsos em microssegundos inteiros")
    if TEMPO_ACOMODACAO_MS < PERIODO_COMANDO_MS:
        raise ValueError("Tempo de acomodacao insuficiente")
    if TEMPO_CALIBRACAO_MS < PERIODO_COMANDO_MS:
        raise ValueError("Tempo de calibracao insuficiente")
    if PIN_POT not in (26, 27, 28):
        raise ValueError("Use GP26, GP27 ou GP28 para o potenciometro")
    if len({PIN_POT, PIN_SERVO, PIN_ENCERRAR}) != 3:
        raise ValueError("Pinos devem ser distintos")
    if not (0 <= PIN_SERVO <= 22 and 0 <= PIN_ENCERRAR <= 22):
        raise ValueError("Pinos digitais invalidos para esta montagem")
    inferior, superior = limites_duty()
    if inferior > superior:
        raise ValueError("Faixa menor que a resolucao do PWM")


def raw_para_pct(raw):
    """Satura entradas numericas finitas; a API ADC fornece um inteiro u16."""
    return max(0, min(ADC_MAX_U16, raw)) * PCT_TOTAL / ADC_MAX_U16


def pct_para_angulo(pct):
    pct = max(0.0, min(PCT_TOTAL, pct))
    return ANGULO_MIN + pct * (ANGULO_MAX - ANGULO_MIN) / PCT_TOTAL


def aceitar_referencia(pct, referencia):
    """Compara com a ultima referencia ACEITA, nao com a amostra anterior.

    Assim pequenas variacoes acumuladas eventualmente alteram a referencia.
    Os extremos exatos sempre sao aceitos para permitir fechar/abrir totalmente.
    A zona morta filtra o alvo; a rampa continua ate o ultimo alvo aceito.
    """
    if referencia is None or pct in (0.0, PCT_TOTAL):
        return pct
    if abs(pct - referencia) >= DEADBAND_PCT:
        return pct
    return referencia


def proximo_angulo(atual, alvo):
    alvo = max(ANGULO_MIN, min(ANGULO_MAX, alvo))
    delta = max(-PASSO_MAX_GRAUS, min(PASSO_MAX_GRAUS, alvo - atual))
    return max(ANGULO_MIN, min(ANGULO_MAX, atual + delta))


def limites_duty():
    # Arredondamento para DENTRO da faixa nominal; evita pulso de 499,9 us.
    inferior = (PULSO_MIN_US * PWM_MAX_U16 + PERIODO_PWM_US - 1) // PERIODO_PWM_US
    superior = PULSO_MAX_US * PWM_MAX_U16 // PERIODO_PWM_US
    return inferior, superior


def angulo_para_duty(angulo):
    if not ANGULO_MIN <= angulo <= ANGULO_MAX:
        raise ValueError("Angulo fora da faixa; PWM nao atualizado")
    fracao = (angulo - ANGULO_MIN) / (ANGULO_MAX - ANGULO_MIN)
    pulso = PULSO_MIN_US + fracao * (PULSO_MAX_US - PULSO_MIN_US)
    duty = int(pulso * PWM_MAX_U16 / PERIODO_PWM_US + 0.5)
    inferior, superior = limites_duty()
    return max(inferior, min(superior, duty))


def aplicar(pwm, estado, angulo, referencia, motivo):
    duty = angulo_para_duty(angulo)
    # Atualiza estado imediatamente apos escrever: inclusive se print falhar.
    if duty == estado['duty']:
        estado['angulo'] = angulo
        return
    pwm.duty_u16(duty)
    estado['angulo'], estado['duty'] = angulo, duty
    pulso = duty * PERIODO_PWM_US / PWM_MAX_U16
    print("[INFO] t_ms={} | ref={:.2f}% | ang_cmd={:.2f} graus | pulso_us={:.2f} | duty={} | {}".format(
        time.ticks_ms(), referencia, angulo, pulso, duty, motivo))


def mover_ate(pwm, estado, alvo, referencia, motivo, botao=None):
    while estado['angulo'] != alvo:
        if botao is not None and botao.value() == 0:
            return False
        time.sleep_ms(PERIODO_COMANDO_MS)
        aplicar(pwm, estado, proximo_angulo(estado['angulo'], alvo), referencia, motivo)
    return True


def encerrar(pwm, estado):
    try:
        print("[INFO] Retorno a posicao segura: {:.1f} graus".format(ANGULO_SEGURO))
        pct_seguro = (ANGULO_SEGURO - ANGULO_MIN) * PCT_TOTAL / (ANGULO_MAX - ANGULO_MIN)
        mover_ate(pwm, estado, ANGULO_SEGURO, pct_seguro, 'retorno_seguro')
        time.sleep_ms(TEMPO_ACOMODACAO_MS)
    finally:
        # Duty zero aqui significa desligamento, nao um novo angulo.
        pwm.deinit()
        Pin(PIN_SERVO, Pin.OUT, value=0)
    print("[INFO] PWM desligado. Agora pode parar a simulacao.")


def calibrar(pwm, estado, botao):
    print("[INFO] CALIBRACAO: observe e registre eixo e pulsos no README")
    for alvo in (ANGULO_MIN, (ANGULO_MIN + ANGULO_MAX) / 2, ANGULO_MAX):
        pct = (alvo - ANGULO_MIN) * PCT_TOTAL / (ANGULO_MAX - ANGULO_MIN)
        if not mover_ate(pwm, estado, alvo, pct, 'calibracao', botao):
            return
        print("[CAL] Alvo {:.1f} graus; duty {}; anote o angulo OBSERVADO".format(alvo, estado['duty']))
        inicio = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), inicio) < TEMPO_CALIBRACAO_MS:
            if botao.value() == 0:
                return
            time.sleep_ms(PERIODO_COMANDO_MS)


def main():
    validar_configuracao()  # Antes de ativar qualquer saida.
    adc = ADC(Pin(PIN_POT))
    botao = Pin(PIN_ENCERRAR, Pin.IN, Pin.PULL_UP)
    pwm = PWM(Pin(PIN_SERVO), freq=PWM_FREQ_HZ, duty_u16=0)
    estado = {'angulo': ANGULO_SEGURO, 'duty': None}
    try:
        print("# Projeto 05 - servo PWM | 50 Hz | botao vermelho encerra")
        pct_seguro = (ANGULO_SEGURO - ANGULO_MIN) * PCT_TOTAL / (ANGULO_MAX - ANGULO_MIN)
        aplicar(pwm, estado, ANGULO_SEGURO, pct_seguro, 'inicial')
        time.sleep_ms(TEMPO_ACOMODACAO_MS)
        if MODO_CALIBRACAO:
            calibrar(pwm, estado, botao)
            return
        referencia = None
        while botao.value() != 0:
            # Espera minima entre comandos: nao recupera atrasos em rajadas.
            time.sleep_ms(PERIODO_COMANDO_MS)
            referencia = aceitar_referencia(raw_para_pct(adc.read_u16()), referencia)
            alvo = pct_para_angulo(referencia)
            aplicar(pwm, estado, proximo_angulo(estado['angulo'], alvo), referencia, 'movimento')
    except KeyboardInterrupt:
        print("[INFO] Interrupcao recebida pelo MicroPython")
    finally:
        encerrar(pwm, estado)


if __name__ == '__main__':
    main()
