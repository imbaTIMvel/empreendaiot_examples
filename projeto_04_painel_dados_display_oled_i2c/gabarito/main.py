"""
Projeto 04 - Painel de dados em display OLED (I2C)
EmpreendAIoT / Instituto Hardware BR - Monitoria, Trilha IoT

Le temperatura e umidade de um DHT22 e mostra os valores num painel OLED
SSD1306 128x64 ligado ao barramento I2C. O display e descoberto por scan, o
painel tem indicador de atividade, tela de erro dedicada e uma segunda tela
de diagnostico alternada por botao.
"""

import time
from machine import Pin, I2C
import dht
import ssd1306

# --- parametros ajustaveis (valores de referencia, podem ser calibrados) ---
PIN_SDA = 21                 # I2C0 padrao do ESP32
PIN_SCL = 22
PIN_DHT = 4                  # GPIO comum; evita os strapping pins do ESP32
PIN_BOTAO = 14
PERIODO_LEITURA_MS = 2500    # margem sobre o minimo de 2 s do DHT22 (ver limites).
                             # Pedir exatamente 2000 fica na fronteira: qualquer
                             # adiantamento do agendamento cai abaixo do minimo e
                             # o sensor responde com erro.
PERIODO_REFRESH_MS = 500     # independente da leitura: a tela redesenha 4x por leitura
DEBOUNCE_MS = 50             # tempo que o botao precisa ficar SOLTO para valer um
                             # novo toque; nao e espera antes de agir (ver o loop)
FALHAS_PARA_TELA_ERRO = 2    # falhas seguidas antes de trocar para a tela de erro
SPINNER = "|/-\\"            # indicador de atividade (requisito 3)
NOME_PAINEL = "PAINEL 04"    # identificador neutro do header (max 15 caracteres)

# --- limites determinados: NAO alterar sem consultar a fonte citada ---
# Area util do modulo SSD1306 = 128 x 64 pixels (datasheet do controlador).
LARGURA_PX = 128
ALTURA_PX = 64
# A fonte embutida no framebuf ocupa 8 x 8 pixels por caractere, o que da
# 16 colunas por 8 linhas de texto. Confirmar no driver efetivamente usado.
LARGURA_FONTE_PX = 8
ALTURA_FONTE_PX = 8
COLUNAS = LARGURA_PX // LARGURA_FONTE_PX      # 16 caracteres por linha
LINHAS = ALTURA_PX // ALTURA_FONTE_PX         # 8 linhas de texto
# O endereco I2C do modulo e 0x3C ou 0x3D conforme a configuracao da placa.
# Descobrir por scan, nunca presumir.
ENDERECOS_SSD1306 = (0x3C, 0x3D)
# Clock do barramento I2C: 100 kHz no modo standard, 400 kHz no fast
# (definido pela especificacao I2C). Usamos o fast porque cada show() envia o
# framebuffer inteiro (1024 bytes) e o loop fica parado durante o envio:
# ~92 ms a 100 kHz contra ~23 ms a 400 kHz.
I2C_FREQ_HZ = 400000
# Intervalo minimo entre leituras do DHT22 = 2 s (datasheet). Ler antes disso
# devolve erro, e esse erro nao e defeito do codigo.
DHT22_INTERVALO_MIN_MS = 2000
# Faixa de medicao do DHT22 (datasheet).
DHT22_TEMP_MIN_C = -40.0
DHT22_TEMP_MAX_C = 80.0
DHT22_UMID_MIN_PCT = 0.0
DHT22_UMID_MAX_PCT = 100.0

# Grade de posicionamento (y em pixels). As linhas 1 e 6 ficam reservadas
# para os tracos separadores, por isso nao recebem texto.
Y_HEADER = 0                 # linha 0
Y_TRACO_TOPO = 10            # dentro da faixa da linha 1
Y_CAMPO_1 = 16               # linha 2
Y_CAMPO_2 = 24               # linha 3
Y_CAMPO_3 = 32               # linha 4
Y_TRACO_BASE = 52            # dentro da faixa da linha 6
Y_RODAPE = 56                # linha 7

# Identificadores das telas.
TELA_DADOS = 0
TELA_DIAGNOSTICO = 1


# --------------------------------------------------------------------------
# Montagem de texto: funcoes puras, nao acessam hardware nem display.
# --------------------------------------------------------------------------
def montar_linha(esquerda, direita):
    """Monta uma linha de no maximo COLUNAS caracteres, com os dois textos
    encostados nas bordas e ao menos um espaco entre eles. Garante o
    requisito 5: nada passa da tela, em nenhum estado."""
    if len(direita) > COLUNAS:
        direita = direita[:COLUNAS]
    # O -1 reserva o espaco minimo: rotulo e valor nunca se encostam.
    limite_esquerda = COLUNAS - len(direita) - 1
    if limite_esquerda < 0:
        limite_esquerda = 0
    if len(esquerda) > limite_esquerda:
        esquerda = esquerda[:limite_esquerda]
    sobra = COLUNAS - len(esquerda) - len(direita)
    return esquerda + " " * sobra + direita


def formatar_medida(valor, unidade):
    """Formata uma grandeza com uma casa decimal. None vira tracos."""
    if valor is None:
        return "--.- " + unidade
    return "{:.1f} {}".format(valor, unidade)


def formatar_uptime(segundos):
    """Uptime compacto, em no maximo 6 caracteres. Troca de unidade em vez de
    deixar o numero crescer, para a linha nunca estourar.

    O valor negativo vira zero: quem chama calcula o uptime com ticks_diff(),
    que so devolve resultado correto enquanto a diferenca couber em metade do
    periodo do contador de milissegundos (ver Limitacoes no README)."""
    if segundos < 0:
        segundos = 0
    if segundos < 1000:
        return "{}s".format(segundos)
    minutos = segundos // 60
    if minutos < 1000:
        return "{}m".format(minutos)
    return "{}h".format(minutos // 60)


def medida_na_faixa(valor, minimo, maximo):
    """True se a leitura cai na faixa que o datasheet promete."""
    return valor is not None and minimo <= valor <= maximo


# --------------------------------------------------------------------------
# Desenho: recebem TODOS os dados por parametro (requisito 6).
# Nao leem sensor, nao usam variavel global, nao decidem nada.
# --------------------------------------------------------------------------
def desenhar_dados(oled, dados):
    oled.fill(0)
    oled.text(montar_linha(NOME_PAINEL, dados["spinner"]), 0, Y_HEADER)
    oled.hline(0, Y_TRACO_TOPO, LARGURA_PX, 1)
    oled.text(montar_linha("Temp", formatar_medida(dados["temp_c"], "C")), 0, Y_CAMPO_1)
    oled.text(montar_linha("Umid", formatar_medida(dados["umid_pct"], "%")), 0, Y_CAMPO_2)
    oled.text(montar_linha("Leituras", str(dados["leituras_ok"])), 0, Y_CAMPO_3)
    oled.hline(0, Y_TRACO_BASE, LARGURA_PX, 1)
    oled.text(montar_linha("I2C 0x{:02X}".format(dados["endereco"]),
                           formatar_uptime(dados["uptime_s"])), 0, Y_RODAPE)
    oled.show()


def desenhar_diagnostico(oled, dados):
    oled.fill(0)
    oled.text(montar_linha("DIAGNOSTICO", dados["spinner"]), 0, Y_HEADER)
    oled.hline(0, Y_TRACO_TOPO, LARGURA_PX, 1)
    oled.text(montar_linha("Falhas", str(dados["falhas"])), 0, Y_CAMPO_1)
    oled.text(montar_linha("Seguidas", str(dados["falhas_seguidas"])), 0, Y_CAMPO_2)
    oled.text(montar_linha("Refresh", "{}ms".format(PERIODO_REFRESH_MS)), 0, Y_CAMPO_3)
    oled.hline(0, Y_TRACO_BASE, LARGURA_PX, 1)
    oled.text(montar_linha("botao: dados", ""), 0, Y_RODAPE)
    oled.show()


def desenhar_erro(oled, dados):
    """Tela de erro (requisito 4): fundo aceso e texto apagado, para ser
    inconfundivel a distancia - nao depende de ler o texto."""
    oled.fill(1)
    oled.text(montar_linha("** FALHA **", dados["spinner"]), 0, Y_HEADER, 0)
    oled.hline(0, Y_TRACO_TOPO, LARGURA_PX, 0)
    oled.text(montar_linha("DHT22 sem", ""), 0, Y_CAMPO_1, 0)
    oled.text(montar_linha("resposta", ""), 0, Y_CAMPO_2, 0)
    oled.text(montar_linha("Seguidas", str(dados["falhas_seguidas"])), 0, Y_CAMPO_3, 0)
    oled.hline(0, Y_TRACO_BASE, LARGURA_PX, 0)
    oled.text(montar_linha("ok ha", formatar_uptime(dados["desde_ok_s"])), 0, Y_RODAPE, 0)
    oled.show()


# --------------------------------------------------------------------------
# Montagem do hardware
# --------------------------------------------------------------------------
def procurar_display(i2c):
    """Requisito 1: faz o scan, imprime o que achou e devolve o endereco do
    display - ou None, para o programa encerrar de forma controlada."""
    encontrados = i2c.scan()
    print("# scan do barramento I2C (SDA=D{}, SCL=D{}, {} Hz)".format(
        PIN_SDA, PIN_SCL, I2C_FREQ_HZ))
    print("# dispositivos que responderam: {}".format(len(encontrados)))
    for endereco in encontrados:
        print("#   0x{:02X}".format(endereco))

    if not encontrados:
        print("# FALHA: ninguem respondeu no barramento.")
        print("#   confira VCC em 3V3, GND, SDA em D{} e SCL em D{}.".format(
            PIN_SDA, PIN_SCL))
        return None

    for endereco in encontrados:
        if endereco in ENDERECOS_SSD1306:
            print("# display SSD1306 encontrado em 0x{:02X}".format(endereco))
            return endereco

    print("# FALHA: ha dispositivos no barramento, mas nenhum em 0x3C ou 0x3D.")
    print("#   o endereco do modulo pode estar configurado de outro jeito.")
    return None


def main():
    i2c = I2C(0, scl=Pin(PIN_SCL), sda=Pin(PIN_SDA), freq=I2C_FREQ_HZ)
    endereco = procurar_display(i2c)
    if endereco is None:
        print("# encerrando sem abrir o painel.")
        return

    oled = ssd1306.SSD1306_I2C(i2c, endereco)
    sensor = dht.DHT22(Pin(PIN_DHT))
    # Botao com pull-up interno: solto le 1, pressionado le 0.
    botao = Pin(PIN_BOTAO, Pin.IN, Pin.PULL_UP)

    temp_c = None
    umid_pct = None
    leituras_ok = 0
    falhas = 0
    falhas_seguidas = 0
    giro = 0
    tela = TELA_DADOS

    t_boot = time.ticks_ms()
    t_ultimo_ok = t_boot
    # A primeira leitura fica para daqui a um periodo: o DHT22 precisa de um
    # tempo depois de energizado antes de responder. Ler no instante zero
    # devolve erro sempre, e isso poluiria o log logo no boot.
    prox_leitura = time.ticks_add(t_boot, PERIODO_LEITURA_MS)
    prox_refresh = t_boot
    # Estado do debounce do botao. 'armado' diz se o programa esta pronto para
    # aceitar um toque; 't_solto' marca desde quando o botao esta solto.
    armado = True
    t_solto = t_boot

    print("# painel no ar. botao em D{} alterna dados/diagnostico.".format(PIN_BOTAO))

    try:
        while True:
            agora = time.ticks_ms()

            # --- botao: age no toque, depois trava contra o repique ---
            # O contato repica ao apertar E ao soltar. Em vez de esperar o
            # sinal se acalmar antes de agir - o que obrigaria a segurar o
            # botao -, o programa age no INSTANTE do aperto e so volta a
            # aceitar toque depois de ver o botao solto por DEBOUNCE_MS.
            # Assim o repique das duas pontas cai dentro do periodo travado.
            leitura = botao.value()
            if armado and leitura == 0:
                armado = False
                t_solto = agora
                if tela == TELA_DADOS:
                    tela = TELA_DIAGNOSTICO
                    print("# tela trocada para diagnostico")
                else:
                    tela = TELA_DADOS
                    print("# tela trocada para dados")
                # Redesenha JA, sem esperar o proximo tique de refresh.
                prox_refresh = agora
            elif not armado:
                if leitura == 0:
                    # Ainda pressionado, ou repicando: adia o rearme.
                    t_solto = agora
                elif time.ticks_diff(agora, t_solto) >= DEBOUNCE_MS:
                    # Solto e quieto ha tempo suficiente: pronto para o proximo.
                    armado = True

            # --- leitura do sensor, no ritmo dele ---
            if time.ticks_diff(agora, prox_leitura) >= 0:
                prox_leitura = time.ticks_add(prox_leitura, PERIODO_LEITURA_MS)
                try:
                    sensor.measure()
                    lido_temp = sensor.temperature()
                    lido_umid = sensor.humidity()
                    if (medida_na_faixa(lido_temp, DHT22_TEMP_MIN_C, DHT22_TEMP_MAX_C) and
                            medida_na_faixa(lido_umid, DHT22_UMID_MIN_PCT, DHT22_UMID_MAX_PCT)):
                        temp_c = lido_temp
                        umid_pct = lido_umid
                        leituras_ok += 1
                        if falhas_seguidas > 0:
                            print("# recuperado apos {} falha(s) seguida(s)".format(
                                falhas_seguidas))
                        falhas_seguidas = 0
                        t_ultimo_ok = agora
                    else:
                        falhas += 1
                        falhas_seguidas += 1
                        print("# AVISO: leitura fora da faixa do datasheet, descartada")
                except OSError as erro:
                    falhas += 1
                    falhas_seguidas += 1
                    print("# AVISO: falha na leitura do DHT22 ({})".format(erro))

            # --- refresh da tela, no ritmo dele (independente da leitura) ---
            if time.ticks_diff(agora, prox_refresh) >= 0:
                prox_refresh = time.ticks_add(prox_refresh, PERIODO_REFRESH_MS)
                giro = giro + 1
                if giro >= len(SPINNER):
                    giro = 0

                dados = {
                    "temp_c": temp_c,
                    "umid_pct": umid_pct,
                    "leituras_ok": leituras_ok,
                    "falhas": falhas,
                    "falhas_seguidas": falhas_seguidas,
                    "endereco": endereco,
                    "spinner": SPINNER[giro],
                    "uptime_s": time.ticks_diff(agora, t_boot) // 1000,
                    "desde_ok_s": time.ticks_diff(agora, t_ultimo_ok) // 1000,
                }

                if falhas_seguidas >= FALHAS_PARA_TELA_ERRO:
                    desenhar_erro(oled, dados)
                elif tela == TELA_DIAGNOSTICO:
                    desenhar_diagnostico(oled, dados)
                else:
                    desenhar_dados(oled, dados)
    except KeyboardInterrupt:
        print("# encerrado pelo usuario")
    finally:
        oled.fill(0)
        oled.show()


main()
