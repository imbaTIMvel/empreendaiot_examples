"""
Projeto 04 - Painel de dados em display OLED (I2C)
EmpreendAIoT / Instituto Hardware BR - versao do aluno

Preencha os trechos marcados com "# TODO:". A estrutura do programa ja esta
pronta - o que falta sao as decisoes de projeto, o layout e as conversoes.

ANTES DE RODAR: o modulo do display pode nao vir embarcado no firmware. Leia
a secao "Antes de comecar: o modulo do display" no enunciado.md.
"""

import time
from machine import Pin, I2C
import dht
import ssd1306

# --- parametros ajustaveis (valores de referencia, podem ser calibrados) ---
# TODO: escolha os pinos conforme o circuito que voce montou no Wokwi.
#       No ESP32, o I2C0 costuma usar D21 (SDA) e D22 (SCL).
PIN_SDA = None
PIN_SCL = None
PIN_DHT = None
PIN_BOTAO = None

# TODO: defina os dois periodos. Eles sao INDEPENDENTES (requisito 6): a tela
#       redesenha mais rapido que o sensor e lido. Sugestoes do enunciado:
#       PERIODO_LEITURA_MS = 2500 | PERIODO_REFRESH_MS = 500
#       Atencao: o periodo de leitura nao pode ficar abaixo do minimo do DHT22 -
#       e pedir exatamente o minimo fica na fronteira, o que produz erro de
#       leitura intermitente. Deixe margem.
PERIODO_LEITURA_MS = None
PERIODO_REFRESH_MS = None

DEBOUNCE_MS = 50
FALHAS_PARA_TELA_ERRO = 2
# TODO: o indicador de atividade (requisito 3). Pode ser um caractere que gira,
#       um contador ou um pixel piscando - escolha e justifique no README.
SPINNER = None
NOME_PAINEL = "PAINEL 04"    # identificador neutro: nunca use seu nome aqui

# --- limites determinados: NAO alterar sem consultar a fonte citada ---
# TODO: preencha cada valor E o comentario com a fonte. Nenhum destes e escolha
#       sua: vem do datasheet do modulo, do driver ou da especificacao do I2C.
LARGURA_PX = None            # TODO: area util do SSD1306. Fonte: ?
ALTURA_PX = None             # TODO: area util do SSD1306. Fonte: ?
LARGURA_FONTE_PX = None      # TODO: largura de um caractere da fonte embutida. Fonte: ?
ALTURA_FONTE_PX = None       # TODO: altura de um caractere da fonte embutida. Fonte: ?
COLUNAS = None               # TODO: quantos caracteres cabem numa linha? (conta, nao chute)
LINHAS = None                # TODO: quantas linhas de texto cabem na tela?
ENDERECOS_SSD1306 = None     # TODO: os dois enderecos possiveis do modulo. Fonte: ?
I2C_FREQ_HZ = None           # TODO: 100 kHz (standard) ou 400 kHz (fast). Fonte: ?
DHT22_INTERVALO_MIN_MS = None  # TODO: intervalo minimo entre leituras. Fonte: ?
DHT22_TEMP_MIN_C = None      # TODO: faixa de medicao do DHT22. Fonte: ?
DHT22_TEMP_MAX_C = None
DHT22_UMID_MIN_PCT = None
DHT22_UMID_MAX_PCT = None

# TODO: monte a grade de posicionamento. Cada linha de texto ocupa
#       ALTURA_FONTE_PX pixels, entao a linha N comeca em y = N * ALTURA_FONTE_PX.
#       Reserve alguma linha para os tracos separadores, se for usa-los.
#       A grade que voce escolher vai para o README (requisito 5).
Y_HEADER = None
Y_TRACO_TOPO = None
Y_CAMPO_1 = None
Y_CAMPO_2 = None
Y_CAMPO_3 = None
Y_TRACO_BASE = None
Y_RODAPE = None

TELA_DADOS = 0
TELA_DIAGNOSTICO = 1


# --------------------------------------------------------------------------
# Montagem de texto: funcoes puras, nao acessam hardware nem display.
# --------------------------------------------------------------------------
def montar_linha(esquerda, direita):
    """Monta uma linha com o rotulo na borda esquerda e o valor na direita.

    TODO: implemente.
      Esta funcao e a sua garantia do requisito 5 - "layout inteiramente
      contido na area util, sem texto cortado em NENHUM dos estados".
      Em vez de contar caracteres na mao a cada campo, faca a funcao cortar
      o que nao couber. Assim, quando o numero crescer (uptime de 4 digitos,
      contador de leituras de 6), nada vaza para fora da tela.

      Roteiro:
        1. o texto da direita nunca pode passar de COLUNAS caracteres;
        2. calcule quanto sobra para o texto da esquerda, reservando ao menos
           um espaco entre os dois, e corte a esquerda se ela nao couber;
        3. devolva esquerda + espacos + direita, com COLUNAS caracteres.

      Teste com valores absurdos ANTES de ir para o display:
        montar_linha("Leituras", "99999999")  -> nao pode passar de COLUNAS
    """
    return ""


def formatar_medida(valor, unidade):
    """Formata uma grandeza com uma casa decimal.

    TODO: o valor pode ser None antes da primeira leitura bem-sucedida.
          Decida o que mostrar nesse caso - e lembre que essa escolha tambem
          precisa caber na linha.
    """
    return ""


def formatar_uptime(segundos):
    """Tempo desde o boot, em formato compacto.

    TODO: um contador em segundos cresce para sempre e uma hora estoura a
          linha. Troque de unidade conforme o numero cresce (s -> m -> h) para
          o texto nunca passar de poucos caracteres.
    """
    return ""


def medida_na_faixa(valor, minimo, maximo):
    """TODO: True se a leitura cai na faixa que o datasheet promete.
    Leitura fora da faixa nao e dado: e defeito, e precisa ser descartada."""
    return True


# --------------------------------------------------------------------------
# Desenho das telas
# --------------------------------------------------------------------------
def desenhar_dados(oled, dados):
    """Tela principal (requisito 2).

    TODO: monte o painel com:
      - um header fixo de identificacao, com o indicador de atividade;
      - de dois a tres campos de dados;
      - um rodape com o endereco I2C descoberto no scan e o uptime.

    REGRA DO REQUISITO 6: esta funcao recebe TUDO pelo parametro 'dados'.
    Ela nao pode ler o sensor, nao pode usar variavel global e nao decide
    nada - so desenha. E o que permite trocar o layout sem tocar na logica.

    Lembre-se: nada aparece na tela ate voce chamar oled.show().
    """
    pass


def desenhar_diagnostico(oled, dados):
    """Segunda tela, alternada pelo botao.

    TODO: mostre o que ajuda a depurar - contadores de falha, o periodo de
          refresh, o endereco I2C. Mesma regra: so desenha.
    """
    pass


def desenhar_erro(oled, dados):
    """Tela de erro (requisito 4).

    TODO: ela precisa ser VISUALMENTE DISTINTA da tela normal - alguem
          olhando de longe, sem ler o texto, tem que perceber que deu errado.
          Uma opcao e inverter o fundo (oled.fill(1) e texto na cor 0).
          Diga no README qual recurso voce usou e por que.
    """
    pass


# --------------------------------------------------------------------------
# Montagem do hardware
# --------------------------------------------------------------------------
def procurar_display(i2c):
    """Requisito 1: scan do barramento no boot.

    TODO: implemente.
      1. i2c.scan() devolve a lista de enderecos que responderam;
      2. imprima todos eles no log serial, em hexadecimal (formato 0x3C);
      3. se a lista vier VAZIA, imprima um diagnostico util - o que conferir
         no circuito - e devolva None, para o programa encerrar de forma
         controlada. Travar ou estourar excecao aqui nao vale;
      4. se houver enderecos, devolva o primeiro que for de um SSD1306.
         Descobrir por scan, nunca presumir o endereco.
    """
    return None


def main():
    # TODO: crie o barramento com I2C(0, scl=..., sda=..., freq=...)
    i2c = None

    endereco = procurar_display(i2c)
    if endereco is None:
        print("# encerrando sem abrir o painel.")
        return

    oled = ssd1306.SSD1306_I2C(i2c, endereco)
    sensor = dht.DHT22(Pin(PIN_DHT))
    # TODO: botao com pull-up interno. Solto le 1, pressionado le 0.
    botao = None

    temp_c = None
    umid_pct = None
    leituras_ok = 0
    falhas = 0
    falhas_seguidas = 0
    giro = 0
    tela = TELA_DADOS

    t_boot = time.ticks_ms()
    t_ultimo_ok = t_boot
    prox_leitura = t_boot
    prox_refresh = t_boot
    nivel_anterior = 1
    t_ultimo_toque = t_boot

    try:
        while True:
            agora = time.ticks_ms()

            # --- botao: alterna a tela ---
            # TODO: implemente a troca de tela pelo botao.
            #
            #       O contato de um botao REPICA: ao apertar e ao soltar, o
            #       nivel oscila entre 0 e 1 varias vezes antes de assentar.
            #       Se voce so procurar o instante em que o nivel vai de 1 para
            #       0, cada repique vira um toque - e a tela troca em rajada,
            #       ou volta sozinha quando voce solta o botao.
            #
            #       Tambem nao adianta esperar o sinal se acalmar antes de agir:
            #       isso obriga o usuario a SEGURAR o botao, e o clique rapido
            #       e ignorado.
            #
            #       A saida e inverter a ordem: aja no instante do aperto e
            #       trave a entrada depois.
            #         1. guarde se o programa esta 'armado' para aceitar toque;
            #         2. armado + nivel 0 -> troca a tela AGORA e desarma;
            #         3. enquanto desarmado, so rearme depois de ver o botao
            #            SOLTO por DEBOUNCE_MS seguidos - qualquer leitura em
            #            nivel 0 reinicia essa contagem.
            #       Assim o repique das duas pontas cai dentro do periodo
            #       travado, e o toque tem resposta imediata.
            #
            #       Troque a tela e peca o redesenho imediato: sem isso a tela
            #       so muda no proximo tique de refresh, o usuario acha que
            #       falhou e clica de novo - desfazendo a troca.

            # --- leitura do sensor, no ritmo dele ---
            # TODO: so leia quando PERIODO_LEITURA_MS tiver vencido.
            #       A leitura do DHT22 pode falhar de verdade, e isso nao e
            #       defeito seu: envolva em try/except, capture a excecao
            #       ESPECIFICA que o modulo dht levanta (nao um except pelado),
            #       registre no log com nivel de aviso e conte a falha.
            #       Em caso de sucesso: valide a faixa, guarde os valores,
            #       zere o contador de falhas seguidas e marque o instante.

            # --- refresh da tela, no ritmo dele ---
            # TODO: so redesenhe quando PERIODO_REFRESH_MS tiver vencido.
            #       Aqui e onde o indicador de atividade avanca: se ele parar,
            #       o loop travou (requisito 3).
            #       Monte o dicionario 'dados' com tudo que as funcoes de
            #       desenho precisam e escolha a tela:
            #         - falhas seguidas demais  -> desenhar_erro
            #         - botao na tela de diag   -> desenhar_diagnostico
            #         - caso contrario          -> desenhar_dados
            pass
    except KeyboardInterrupt:
        print("# encerrado pelo usuario")
    finally:
        # TODO: deixe a tela apagada ao encerrar.
        pass


main()
