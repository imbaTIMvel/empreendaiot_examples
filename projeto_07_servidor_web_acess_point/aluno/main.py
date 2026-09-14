"""
Projeto 07 - Servidor web no ESP32 (modo Access Point)
EmpreendAIoT / Instituto Hardware BR - versao do aluno

Preencha os trechos marcados com "# TODO:".

Aqui nao ha framework: voce monta o HTTP byte a byte. Leia as duas secoes
"Antes de comecar" do enunciado.md antes de escrever qualquer linha - em
especial a que fala da LINHA EM BRANCO. Ela derruba quase todo mundo.
"""

import gc
import time
import socket
import network
from machine import Pin
import dht

# --- parametros ajustaveis (valores de referencia, podem ser calibrados) ---
# TODO: escolha o nome da sua rede. Identificador NEUTRO do projeto - nunca o
#       seu nome, nem nada que identifique uma pessoa.
SSID_AP = None

# TODO: a senha do Access Point.
#       REGRA DO REPOSITORIO: nenhuma senha real vai para o codigo, comentario,
#       log ou screenshot. Use um PLACEHOLDER explicito e documente no README
#       como o valor real deve ser combinado. Repare que existe um tamanho
#       minimo imposto pelo WPA2 - veja nos limites determinados.
SENHA_AP = None

REFRESH_S = None             # TODO: de quantos em quantos segundos a pagina se atualiza
# TODO: os nomes das rotas. Sao escolha sua, mas precisam estar documentados
#       no README exatamente como aparecem aqui.
ROTA_RAIZ = None
ROTA_LIGAR = None
ROTA_DESLIGAR = None
ROTA_DADOS = None

MAX_BYTES_REQUEST = None     # TODO: teto de leitura do socket (requisito 7)
REQUESTS_TESTE_ESTABILIDADE = 50
TIMEOUT_CLIENTE_S = 5
PIN_LED = None               # TODO: pino da carga
PIN_DHT = None               # TODO: pino de dados do sensor
PERIODO_LEITURA_MS = None    # TODO: nao pode ficar abaixo do minimo do DHT22
AUTOTESTE = True

# --- limites determinados: NAO alterar sem consultar a fonte citada ---
# TODO: preencha cada valor E a fonte. Nenhum destes e escolha sua: sao
#       impostos pelo protocolo HTTP, pela especificacao WPA2 ou pelo datasheet.
PORTA_HTTP = None            # TODO: porta padrao do HTTP. Fonte: ?
SENHA_MIN_CARACTERES = None  # TODO: minimo do WPA2. Fonte: ?
SENHA_MAX_CARACTERES = None  # TODO: maximo do WPA2. Fonte: ?
FIM_DOS_HEADERS = None       # TODO: o que separa os headers do body? Fonte: ?
TIPO_JSON = None             # TODO: content type exigido pela rota de dados. Fonte: ?
TIPO_HTML = None
TIPO_TEXTO = None
STATUS_OK = None             # TODO: os tres status usados. A semantica de cada
STATUS_NAO_ENCONTRADO = None #       um e definida pelo HTTP, nao por voce.
STATUS_REQUEST_INVALIDO = None

# TODO: monte a tupla com as rotas validas. Ela serve para duas coisas:
#       o roteamento e a mensagem do 404 (ver montar_404).
ROTAS_VALIDAS = None


# --------------------------------------------------------------------------
# Funcoes puras: nao tocam em socket, sensor nem LED.
# Todas testaveis isoladamente, fora da placa - e vale testar.
# --------------------------------------------------------------------------
def senha_valida(senha):
    """TODO: True se a senha respeita o tamanho exigido pelo WPA2."""
    return True


def extrair_rota(bruto):
    """Le a request line e devolve (metodo, rota).

    TODO: implemente.
      ENTRADA NAO CONFIAVEL (requisito 7). Do outro lado do socket pode vir
      qualquer coisa: bytes que nao sao texto, request sem metodo, caminho de
      4000 caracteres, conexao cortada no meio. Nada disso pode derrubar o
      servidor - devolva (None, None) e deixe o chamador responder 400.

      Roteiro:
        1. a request line e a PRIMEIRA linha, ate o primeiro \\r\\n;
        2. decodificar pode falhar: trate isso;
        3. a linha valida tem exatamente tres partes: "METODO alvo HTTP/x.y";
        4. o alvo precisa comecar com "/";
        5. descarte a query string (o que vem depois de "?").

      Teste com lixo antes de ir para a placa:
        extrair_rota(b"")                     -> (None, None)
        extrair_rota(b"isto nao e http\\r\\n")  -> (None, None)
        extrair_rota(b"GET / HTTP/1.1\\r\\n")   -> ("GET", "/")
    """
    return None, None


def montar_resposta(status, tipo_conteudo, corpo):
    """Monta a resposta HTTP completa, em bytes.

    TODO: implemente. Esta e a funcao mais traicoeira do projeto.

      A ordem e imposta pelo protocolo:
        status line, headers, LINHA EM BRANCO, body.

      A linha em branco e o CRLF duplo. Sem ela, o navegador fica esperando
      para sempre - nao da erro, so nao carrega. E o sintoma mais confuso que
      existe aqui.

      Mas cuidado com o oposto: cada linha de header ja termina em \\r\\n.
      Se voce terminar a ULTIMA linha e ainda colar o CRLF duplo, sobra uma
      linha em branco a mais, e o body comeca deslocado do que o
      Content-Length anuncia. O cliente le o corpo truncado.
      Conte os \\r\\n com calma.

      Inclua Content-Length com o tamanho do body EM BYTES (nao em
      caracteres - acentos ocupam mais de um byte).

      Teste antes de ir para a placa:
        cab, corpo = resposta.split(b"\\r\\n\\r\\n", 1)
        len(corpo) tem que bater com o Content-Length anunciado.
    """
    return b""


def montar_json(dados):
    """TODO: o JSON da rota de dados.

    Inclua pelo menos: identificador NEUTRO do dispositivo, as leituras, o
    estado da carga e o uptime. Documente as chaves no README.
    Atencao: quando o sensor falha, o valor nao pode virar a string "None" -
    JSON tem um jeito proprio de dizer "sem valor".
    """
    return ""


def montar_pagina(dados):
    """TODO: a pagina HTML da raiz (requisitos 2 e 3).

    Precisa mostrar a leitura do sensor e ter controles para a carga.

    SEM RECURSO EXTERNO: nada de biblioteca em CDN, nada de fonte remota.
    Pense em por que: o cliente esta conectado na rede do SEU dispositivo, que
    nao tem internet. Qualquer coisa que venha de fora simplesmente nao carrega.
    Todo o CSS vai embutido.

    O auto-refresh (requisito 3) sai sem JavaScript - o HTML tem um recurso
    proprio para isso.
    """
    return ""


def montar_404():
    """TODO: o body da resposta 404.

    Cuidado com a armadilha do requisito 7. O impulso natural e escrever algo
    como "rota /foo nao encontrada" - mas isso REFLETE na resposta um texto
    que veio do cliente, sem validacao. Se o cliente pedir uma rota com
    conteudo malicioso, voce acabou de devolve-lo para o navegador.
    Escreva uma mensagem util que NAO repita o que foi pedido.
    """
    return ""


def responder(metodo, rota, dados):
    """Roteamento. TODO: devolva (resposta_em_bytes, acao).

    'acao' diz ao chamador o que fazer com o hardware ("ligar", "desligar" ou
    None). Mantenha esta funcao pura: ela DECIDE, mas nao aciona o LED. E o
    que permite testar o roteamento inteiro sem placa nenhuma.

    Casos a cobrir:
      - metodo None (request que nao deu para interpretar) -> 400
      - rota que nao existe -> 404 (requisito 5), com QUALQUER metodo
      - rota que existe, com metodo nao suportado (ex.: POST /ligar) -> 405
      - cada uma das rotas validas com GET -> 200, com o content type certo
      Nenhum caso pode virar erro de execucao.

    A ORDEM dos testes importa. Olhe a rota antes do metodo: se voce testar o
    metodo primeiro, um POST numa rota inexistente vira 405 - e o certo e 404,
    porque o recurso nem existe.

    O 405 tem uma exigencia do HTTP que o 404 nao tem: o header Allow, dizendo
    quais metodos a rota aceita. E um POST /ligar nunca pode acender a carga.
    """
    return b"", None


# --------------------------------------------------------------------------
# Hardware e rede
# --------------------------------------------------------------------------
def subir_ap():
    """TODO: suba o Access Point e devolva o IP (ou None se algo impedir).

    Roteiro:
      1. valide a senha ANTES de tentar - senha curta demais nao sobe protegida;
      2. network.WLAN(network.AP_IF), active(True) e config(...) com essid,
         password E authmode.
         ARMADILHA: informar so a senha nao garante rede protegida. Conforme a
         versao do firmware, o AP sobe ABERTO e a senha e ignorada, sem erro
         nenhum. Diga o modo de autenticacao explicitamente;
      3. active() nao fica True na hora: espere, com um teto de tentativas;
      4. leia o authmode DE VOLTA com ap.config("authmode") e imprima no log.
         Se vier aberto, recuse abrir o servidor. E isso que transforma
         "configurei a senha" em "provei que a rede esta protegida";
      5. imprima o SSID, o IP e a URL completa no log - e o unico jeito de
         alguem descobrir onde o servidor esta.
    """
    return None


def abrir_servidor():
    """TODO: crie o socket, faca bind na porta do HTTP e comece a escutar.

    Dica: SO_REUSEADDR evita o erro "address in use" quando voce reinicia a
    simulacao sem o socket anterior ter sido liberado.
    """
    return None


def ler_sensor(sensor):
    """TODO: leia o DHT22, devolvendo (temp, umid) ou (None, None) na falha.
    Mesma disciplina do projeto 4: excecao especifica, registrada, sem parar
    o programa."""
    return None, None


def atender(srv, led, dados):
    """Aceita UM cliente, responde e fecha.

    TODO: implemente.
      1. srv.accept() devolve o socket do cliente;
      2. ponha um timeout nele - cliente que emudece nao pode travar o servidor;
      3. leia com TETO DE BYTES (requisito 7): quem manda no tamanho da leitura
         e voce, nao o cliente;
      4. extraia a rota, responda, e acione o LED conforme a acao devolvida;
      5. cliente que desaparece no meio levanta excecao (requisito 6). Isso e
         ocorrencia NORMAL, nao defeito: capture, registre e siga.

      O PONTO QUE MAIS CUSTA CARO: o fechamento do socket do cliente tem que
      acontecer SEMPRE, inclusive quando deu erro. Se voce fechar so no
      caminho feliz, cada request interrompido deixa um socket aberto, a
      memoria livre cai a cada um, e depois de algumas centenas a placa para.
      Existe uma construcao do Python que garante isso.
    """
    return None


def montar_dados(led, temp_c, umid_pct, t_boot, requests):
    """TODO: junte num dicionario tudo que as funcoes de resposta precisam.
    Inclua a memoria livre (gc.mem_free()) - ela e a evidencia do requisito 6."""
    return {}


# --------------------------------------------------------------------------
# Autoteste: a propria placa vira cliente do proprio servidor.
# Existe porque o Access Point simulado nao e alcancavel de fora do Wokwi.
# --------------------------------------------------------------------------
def enviar_request(ip, bruto):
    """TODO: conecte no proprio servidor, mande os bytes e devolva o socket
    AINDA ABERTO - sem ler a resposta.

    Por que nao ler aqui? O programa tem uma thread so. O servidor so responde
    quando atender() rodar. Se o cliente tentar ler antes disso, ele espera
    uma resposta que so pode existir depois que ele desistir de esperar - e o
    resultado e um timeout em TODO request, com o servidor atendendo tarde
    demais. E um impasse, e ele nao da erro de sintaxe nem de logica: so trava.
    """
    return None


def ler_resposta(cli):
    """TODO: leia a resposta e feche o cliente.
    So pode ser chamada DEPOIS de atender(). Feche o socket mesmo se a leitura
    falhar - o mesmo cuidado do servidor vale para o cliente."""
    return b""


def autoteste(srv, led, ip, dados):
    """TODO: monte a bateria de testes e imprima o resultado no log.

    Um caso por requisito - e o log resultante e a sua evidencia:
      - a pagina na raiz                    (requisitos 2 e 3)
      - a rota de dados, conferindo o tipo  (requisito 4)
      - ligar e desligar a carga            (requisito 4)
        Cuidado: as duas rotas rodam com milissegundos de diferenca, e o LED
        acende e apaga rapido demais para o olho. De uma pausa depois de cada
        rota, e leia o nivel do pino de volta com led.value() para o log
        provar que a carga acompanhou - nao dependa so de enxergar o LED.
      - uma rota que nao existe             (requisito 5)
      - um request malformado               (requisito 7)
      - um request gigante                  (requisito 7)
      - um cliente que some no meio         (requisito 6)

    Depois, o teste de estabilidade: meca a memoria livre, dispare
    REQUESTS_TESTE_ESTABILIDADE requests, meca de novo e imprima a variacao.
    Se a memoria cair proporcionalmente ao numero de requests, algum socket
    nao esta sendo fechado.

    A ORDEM E TUDO, porque o programa e um so. Para cada caso:
      1. enviar_request()  - o cliente conecta e manda; a conexao fica
                             esperando na fila de escuta do servidor;
      2. atender()         - o servidor aceita, le e responde;
      3. ler_resposta()    - SO AGORA o cliente le.
    Trocar 2 e 3 de lugar trava cada request ate o timeout.

    Para o caso do cliente que some no meio (requisito 6): feche o cliente
    entre os passos 1 e 2, sem ler nada, e confirme que atender() sobrevive.

    Um aviso sobre o request gigante: o servidor le so MAX_BYTES_REQUEST e
    fecha com o resto ainda no buffer. Pelo TCP, isso gera um RESET, e o
    cliente pode receber "conexao resetada" em vez da resposta. Nao e falha:
    e o teto de leitura funcionando. Diga isso no log, para quem ler a
    evidencia nao confundir com erro.
    """
    pass


def main():
    gc.collect()
    # TODO: monte LED e sensor.
    led = None
    sensor = None

    ip = subir_ap()
    if ip is None:
        print("# encerrando sem abrir o servidor.")
        return

    srv = abrir_servidor()
    t_boot = time.ticks_ms()
    temp_c = None
    umid_pct = None
    requests = 0
    prox_leitura = time.ticks_add(t_boot, PERIODO_LEITURA_MS)

    try:
        if AUTOTESTE:
            autoteste(srv, led, ip,
                      montar_dados(led, temp_c, umid_pct, t_boot, requests))

        print("# pronto. aguardando requests em http://{}/".format(ip))
        while True:
            # TODO: leia o sensor no ritmo dele, sem bloquear o atendimento.

            # TODO: monte os dados, atenda um cliente e conte o request.

            # TODO: periodicamente, rode gc.collect() e imprima a memoria
            #       livre. E o que transforma o requisito 6 em numero.
            pass
    except KeyboardInterrupt:
        print("# encerrado pelo usuario")
    finally:
        # TODO: feche o socket do servidor e desligue a carga ao encerrar.
        pass


main()
