"""
Projeto 03 - Sensor de temperatura e umidade DHT22
EmpreendAIoT / Instituto Hardware BR - versao do aluno

Contexto: monitorar o ambiente e continuar operando quando o sensor falhar.
Raspberry Pi Pico (RP2040), MicroPython.
Leia ../enunciado.md e resolva os # TODO:. Os NotImplementedError sinalizam
exercicios pendentes; remova-os ao implementar cada funcao. Nao sao falhas DHT.
"""

from machine import Pin
import dht
import time

# --- parametros ajustaveis: escolhas de projeto ---
PINO_DHT = None               # TODO: numero GP da linha de dados; nao pino fisico
PINO_LED_ERRO = None          # TODO: numero GP do LED, com resistor em serie
PERIODO_LEITURA_MS = None     # TODO: sugestao 2500 ms; respeite o limite abaixo
FALHAS_PARA_ERRO = None       # TODO: sugestao 3; inteiro positivo

# --- limites determinados: valores impostos pelo sensor/API ---
# TODO: consulte o datasheet, preencha valores e cite fonte/data no README.
INTERVALO_MINIMO_MS = None    # TODO: intervalo minimo entre tentativas
TEMPERATURA_MIN_C = None      # TODO: extremo inferior em Celsius
TEMPERATURA_MAX_C = None      # TODO: extremo superior em Celsius
UMIDADE_MIN_PCT = None        # TODO: extremo inferior de umidade relativa
UMIDADE_MAX_PCT = None        # TODO: extremo superior de umidade relativa
RESOLUCAO_C = None            # TODO: resolucao (nao confundir com exatidao)
RESOLUCAO_UR_PCT = None       # TODO: resolucao de umidade


def validar_configuracao():
    # TODO: rejeitar periodo nao inteiro ou inferior ao minimo e limite de
    # falhas nao inteiro ou menor que 1. Erro de configuracao deve aparecer;
    # nao o trate como uma falha recuperavel do sensor.
    raise NotImplementedError("TODO: validar configuracao")


def novo_estado():
    # None representa ausencia de amostra valida; zero seria um valor inventado.
    return {"falhas": 0, "minimos": None, "maximos": None}


def celsius_para_fahrenheit(temperatura_c):
    # TODO: implementar a formula, documentar a fonte e conferir:
    # 0 C -> 32 F; 100 C -> 212 F; -40 C -> -40 F.
    # A funcao recebe/devolve numeros; nao deve acessar sensor ou GPIO.
    raise NotImplementedError("TODO: converter Celsius para Fahrenheit")


def atualizar_extremos(estado, valores):
    # TODO: valores tem a ordem (Celsius, umidade, Fahrenheit).
    # Na primeira amostra, inicialize duas listas independentes com os valores.
    # Nas seguintes, atualize min/max de cada posicao. Nao acumule historico.
    raise NotImplementedError("TODO: atualizar extremos")


def registrar(nivel, mensagem):
    print("[{}] {}".format(nivel, mensagem))


def registrar_falha(estado, led, motivo):
    # TODO: incrementar falhas consecutivas; escolher AVISO ou ERRO conforme
    # FALHAS_PARA_ERRO; atualizar LED; imprimir contador e motivo.
    # Nao atualizar extremos nem tentar ler o sensor aqui.
    raise NotImplementedError("TODO: registrar falha e controlar alarme")


def executar_ciclo(sensor, led, estado):
    # TODO: chamar sensor.measure() em um try restrito a essa operacao.
    # Capturar OSError (inclui timeout). Para checksum, o driver oficial usa
    # Exception("checksum error"): reconhecer apenas esse caso exato e
    # relancar outros erros. Consulte a explicacao no enunciado.
    # Em falha: chamar registrar_falha(...) e retornar False para o proximo
    # ciclo aguardar o intervalo. Nao continuar com valores antigos do sensor.
    raise NotImplementedError("TODO: medir e tratar as excecoes do driver")

    # TODO: depois de measure() bem-sucedido, obter temperature() e humidity().
    # Validar as faixas; se invalidas, registrar falha e retornar False.
    # Converter para Fahrenheit e atualizar extremos apenas com dados validos.
    # Registrar recuperacao se existiam falhas; zerar contador e apagar LED.
    # Imprimir C, % UR e F, com uma casa decimal, minimo e maximo de cada uma.
    # Retornar True em sucesso.


def main():
    validar_configuracao()
    led = Pin(PINO_LED_ERRO, Pin.OUT, value=0)
    sensor = dht.DHT22(Pin(PINO_DHT))
    estado = novo_estado()
    registrar("INFO", "Projeto 03 - Pico + DHT22")
    while True:
        # TODO: esperar PERIODO_LEITURA_MS ANTES de cada tentativa, inclusive
        # a primeira. Esta espera tambem deve ocorrer apos qualquer falha.
        # Use time.sleep_ms(). O projeto tem uma unica tarefa periodica.
        # Remova a excecao abaixo ao implementar a espera.
        raise NotImplementedError("TODO: respeitar intervalo entre tentativas")
        executar_ciclo(sensor, led, estado)


if __name__ == "__main__":
    main()
