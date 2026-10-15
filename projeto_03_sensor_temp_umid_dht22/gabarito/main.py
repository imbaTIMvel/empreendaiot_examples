"""Projeto 03 - Sensor de temperatura e umidade DHT22.
EmpreendAIoT / Instituto Hardware BR - Monitoria, Trilha IoT

Raspberry Pi Pico (RP2040), MicroPython; versao de referencia (gabarito).
Fahrenheit = Celsius * 9 / 5 + 32 (NIST; referencias no ../README.md).
O driver dht implementa o protocolo; este programa trata suas falhas.
"""

from machine import Pin
import dht
import time

# --- parametros ajustaveis: escolhas de projeto ---
PINO_DHT = 27                 # GP27, pino fisico 32 do Pico
PINO_LED_ERRO = 26            # GP26, pino fisico 31 do Pico
PERIODO_LEITURA_MS = 2500      # Conservador: acima dos 2 s do DHT22
FALHAS_PARA_ERRO = 3

# --- limites determinados: conferir fontes no ../README.md ---
# Datasheet Aosong DHT22, secoes 3 e 7; API MicroPython dht.
INTERVALO_MINIMO_MS = 2000
TEMPERATURA_MIN_C = -40.0
TEMPERATURA_MAX_C = 80.0
UMIDADE_MIN_PCT = 0.0
UMIDADE_MAX_PCT = 100.0
RESOLUCAO_C = 0.1             # Referencia; nao e um fator de conversao
RESOLUCAO_UR_PCT = 0.1        # Resolucao nao significa exatidao


def validar_configuracao():
    if (type(PERIODO_LEITURA_MS) is not int or
            PERIODO_LEITURA_MS < INTERVALO_MINIMO_MS):
        raise ValueError("PERIODO_LEITURA_MS deve ser inteiro >= 2000")
    if type(FALHAS_PARA_ERRO) is not int or FALHAS_PARA_ERRO < 1:
        raise ValueError("FALHAS_PARA_ERRO deve ser inteiro >= 1")


def novo_estado():
    # Sem zeros artificiais: extremos nascem na primeira leitura valida.
    return {"falhas": 0, "minimos": None, "maximos": None}


def celsius_para_fahrenheit(temperatura_c):
    """Funcao pura: F = C * 9/5 + 32. Fonte: NIST, SI Units - Temperature."""
    return temperatura_c * 9.0 / 5.0 + 32.0


def atualizar_extremos(estado, valores):
    """Ordem das grandezas: temperatura C, umidade % UR, temperatura F."""
    if estado["minimos"] is None:
        estado["minimos"] = list(valores)
        estado["maximos"] = list(valores)
    else:
        for indice, valor in enumerate(valores):
            estado["minimos"][indice] = min(estado["minimos"][indice], valor)
            estado["maximos"][indice] = max(estado["maximos"][indice], valor)


def registrar(nivel, mensagem):
    print("[{}] {}".format(nivel, mensagem))


def registrar_falha(estado, led, motivo):
    estado["falhas"] += 1
    alarme = estado["falhas"] >= FALHAS_PARA_ERRO
    led.value(1 if alarme else 0)
    registrar("ERRO" if alarme else "AVISO",
              "Falha consecutiva {}: {}. Nova tentativa no proximo ciclo."
              .format(estado["falhas"], motivo))
    # Nenhum valor invalido entra nos extremos.


def executar_ciclo(sensor, led, estado):
    # Deliberadamente, somente a operacao do driver fica neste try.
    try:
        sensor.measure()
    except OSError as erro:
        # Inclui timeout gerado pela rotina nativa de leitura do DHT.
        registrar_falha(estado, led, "leitura DHT: {}".format(erro))
        return False
    except Exception as erro:
        # O driver oficial usa Exception("checksum error") para checksum.
        # Nao e uma classe criada pelo projeto. Outros bugs devem aparecer.
        if type(erro) is not Exception or erro.args != ("checksum error",):
            raise
        registrar_falha(estado, led, "checksum invalido")
        return False

    temperatura_c = sensor.temperature()
    umidade = sensor.humidity()
    if not (TEMPERATURA_MIN_C <= temperatura_c <= TEMPERATURA_MAX_C and
            UMIDADE_MIN_PCT <= umidade <= UMIDADE_MAX_PCT):
        registrar_falha(estado, led, "valor fora da faixa do DHT22")
        return False

    temperatura_f = celsius_para_fahrenheit(temperatura_c)
    valores = (temperatura_c, umidade, temperatura_f)
    atualizar_extremos(estado, valores)

    falhas_anteriores = estado["falhas"]
    estado["falhas"] = 0
    led.value(0)
    if falhas_anteriores:
        registrar("INFO", "Recuperacao apos {} falha(s); contador zerado."
                  .format(falhas_anteriores))

    registrar("INFO", "Leitura valida; extremos desde o inicio do programa:")
    for indice, unidade in enumerate(("°C", "% UR", "°F")):
        print("  {}: {:.1f} | minimo: {:.1f} | maximo: {:.1f}"
              .format(unidade, valores[indice], estado["minimos"][indice],
                      estado["maximos"][indice]))
    return True


def main():
    validar_configuracao()
    led = Pin(PINO_LED_ERRO, Pin.OUT, value=0)
    sensor = dht.DHT22(Pin(PINO_DHT))
    estado = novo_estado()
    registrar("INFO", "Pico + DHT22 | intervalo: {} ms | alarme: {} falhas"
              .format(PERIODO_LEITURA_MS, FALHAS_PARA_ERRO))
    while True:
        # Tambem espera antes da primeira leitura, para estabilizar o sensor.
        # Espera apos cada ciclo: tentativas nunca ficam mais proximas que
        # PERIODO_LEITURA_MS, inclusive quando houve timeout.
        time.sleep_ms(PERIODO_LEITURA_MS)
        executar_ciclo(sensor, led, estado)


if __name__ == "__main__":
    main()
