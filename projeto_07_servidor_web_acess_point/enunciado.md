# Projeto 07 — Servidor web no ESP32 (modo Access Point)

**Placa:** ESP32 DevKit V1 · **Esforço estimado:** 6 h

## Contexto

Nos projetos anteriores a placa consumia: lia sensor, mostrava no serial, no
display. Aqui ela **vira o servidor**. Sobe a própria rede Wi-Fi, atende na
porta 80, e qualquer dispositivo que se conecte a essa rede abre uma página
servida pelo microcontrolador.

E você vai escrever o HTTP **na mão**. Sem framework, sem biblioteca de rota,
sem template. O protocolo que carrega metade da internet cabe em algumas
dezenas de linhas — e vê-lo por dentro uma vez muda a forma como você lê
qualquer stack web depois.

## Antes de começar: o HTTP é texto, e a formatação é o protocolo

### Como é um request

Quando um navegador pede uma página, ele manda texto puro pelo socket:

```
GET /dados HTTP/1.1
Host: 192.168.4.1
User-Agent: Mozilla/5.0
Accept: text/html

```

A **primeira linha** é a que interessa para rotear: método, alvo e versão,
separados por espaço. Depois vêm os headers, um por linha. E no fim, uma
**linha em branco**, que anuncia o fim dos headers.

### Como é uma resposta

Mesma estrutura, invertida:

```
HTTP/1.1 200 OK
Content-Type: text/html; charset=utf-8
Content-Length: 887
Connection: close

<!DOCTYPE html><html>...
```

Status line, headers, **linha em branco**, body.

### A linha em branco é o projeto inteiro

Repare que cada linha termina com `\r\n` — CR (*carriage return*) seguido de LF
(*line feed*). Não é `\n` sozinho: é o par, e isso é imposição do protocolo.

A linha em branco, então, é um `\r\n` a mais logo depois do `\r\n` que fecha o
último header. Na prática você digita **`\r\n\r\n`** — o famoso CRLF duplo.

Duas maneiras de errar, e as duas vão acontecer com você:

**Faltando a linha em branco.** O navegador não dá erro. Ele fica girando,
esperando mais headers, para sempre. É o sintoma mais confuso do projeto,
porque parece travamento do servidor quando na verdade o servidor já respondeu.

**Linha em branco sobrando.** Se a última linha de header já termina em `\r\n`
e você concatena `\r\n\r\n` depois dela, sobra uma linha em branco a mais. O
body começa dois bytes adiante do que o `Content-Length` anuncia, e o cliente
lê o corpo truncado. Esse erro é pior que o primeiro, porque *quase* funciona —
o navegador muitas vezes mostra a página assim mesmo, e o defeito só aparece
quando alguém consome o JSON.

Conte os `\r\n` com calma, e teste assim antes de ir para a placa:

```python
cabecalho, corpo = resposta.split(b"\r\n\r\n", 1)
# len(corpo) tem que bater EXATAMENTE com o Content-Length anunciado
```

### O `Content-Length` não é enfeite

Ele diz ao cliente quantos bytes de body esperar. Sem ele, o cliente precisa
adivinhar quando a resposta acabou. E é em **bytes**, não em caracteres — um
`°` ocupa dois. Meça depois de codificar para UTF-8.

## Antes de começar: o modelo de socket

### As cinco chamadas

Um servidor TCP é sempre a mesma sequência:

| Chamada | O que faz |
|---|---|
| `socket()` | cria o socket |
| `bind()` | reserva a porta (aqui, a 80) |
| `listen()` | passa a aceitar conexões, que entram numa fila |
| `accept()` | tira **uma** conexão da fila e devolve um socket novo, só dela |
| `close()` | encerra |

O detalhe que confunde: `accept()` devolve um **socket diferente** do seu. O
original continua escutando; o novo é o canal com aquele cliente específico, e
é ele que você lê, escreve e fecha.

### `accept()` bloqueia

Enquanto ninguém bate na porta, o programa **para** naquela linha. Isso é
diferente de tudo que você fez até agora, onde o loop girava livre. Aqui o
ritmo é ditado por quem chega.

### Todo cliente precisa ser fechado — inclusive os que deram errado

Cada `accept()` consome memória, e ela só volta no `close()`. Se você fechar
apenas no caminho feliz, cada request interrompido deixa um socket pendurado.
A memória livre cai a cada um, devagar, e depois de algumas centenas a placa
para. O programa funciona na demonstração e morre no dia seguinte.

Existe uma construção do Python feita exatamente para "isto tem que acontecer
mesmo se der erro". Use.

### Clientes desaparecem — isso é normal

O usuário fecha a aba no meio do carregamento. A conexão cai. O cliente manda
lixo. Nada disso é defeito do seu código: é o dia a dia de um servidor. O
requisito 6 pede que o servidor **sobreviva** a isso, não que impeça.

## Antes de começar: entrada não confiável

Tudo que chega pelo socket foi escrito por outra pessoa. Duas regras:

**Leia com teto.** `recv(n)` com um `n` que **você** escolheu. Sem isso, quem
decide quanta memória da sua placa será usada é quem manda o request — e um
request de 10 MB derruba o dispositivo.

**Não devolva o que recebeu.** A armadilha deste projeto está no 404. O impulso
é escrever `"rota /foo não encontrada"`, ecoando o caminho pedido. Se o cliente
pedir uma rota contendo código, você acabou de devolvê-lo para o navegador de
quem abrir. A mensagem de 404 deve ser útil **sem repetir** o que foi pedido —
liste as rotas que existem, por exemplo.

## O que montar

Obrigatórios:

- 1 ESP32 DevKit V1;
- 1 LED (`wokwi-led`) com resistor de 220 Ω a 330 Ω, como carga controlável;
- 1 sensor DHT22 (`wokwi-dht22`) como fonte de dados.

## Requisitos funcionais

1. **Access Point** com SSID próprio do projeto e senha definida como
   **placeholder documentado** — nunca uma senha real do Instituto.
2. **Página HTML na raiz** com a leitura do sensor e um controle para alternar
   o LED, **sem depender de recursos externos** (nada de CDN ou fonte remota).
3. **Auto-refresh** dos dados sem intervenção do usuário.
4. **Rotas distintas e documentadas:** raiz, ligar, desligar, e uma que devolve
   os dados em **JSON com o header de content type correto**.
5. **Rota inexistente devolve 404** com body explicativo — e não erro de
   execução.
6. **O servidor sobrevive a cliente que desconecta no meio do request.**
   Sockets fechados corretamente, e a memória livre estável depois de uma
   sequência longa de requests.
7. **O request é tratado como entrada não confiável:** leitura com limite de
   bytes, e nenhum conteúdo do cliente refletido na resposta sem validação.

## Parâmetros e limites

### Ajustáveis (arbitrários)

| Constante | Sugestão | Observação |
|---|---|---|
| `SSID_AP` | `EmpreendAIoT-P07` | identificador neutro, nunca pessoal |
| `REFRESH_S` | 2 | intervalo do auto-refresh |
| nomes das rotas | — | livres, desde que documentados |
| `MAX_BYTES_REQUEST` | 1024 | teto de leitura do socket |
| requests do teste de estabilidade | 50 | quantos disparar na medição |

### Determinados (não arbitrários)

- a **senha WPA2 tem de 8 a 63 caracteres ASCII**, sendo 8 o mínimo do padrão —
  não é escolha sua;
- **porta HTTP padrão = 80**;
- a resposta HTTP exige **status line, headers e uma linha em branco (CRLF
  duplo) antes do body** — omitir a linha em branco deixa o navegador esperando
  indefinidamente;
- a rota de dados exige **`Content-Type: application/json`**;
- a **semântica do status 404** para recurso inexistente é definida pelo HTTP;
- uma rota que **existe**, chamada com um método que ela não aceita, não é
  404: é **405 Method Not Allowed**, e o HTTP exige que essa resposta traga o
  header **`Allow`** com os métodos aceitos;
- **intervalo mínimo entre leituras do DHT22 ≈ 2 s** (datasheet).

## Sobre a senha: uma regra do repositório, não do professor

Nenhuma senha, chave ou token vai para código, comentário, log ou screenshot.
Use um placeholder explícito:

```python
SENHA_AP = "SUBSTITUA_AQUI"
```

E documente no README **como** o valor real deve ser obtido. A razão é
prática: o que entra no Git fica no histórico para sempre, mesmo depois de
apagado do arquivo.

### Configurar a senha não é o mesmo que proteger a rede

Esta pega muita gente. Passar só a senha para o Access Point:

```python
ap.config(essid=SSID_AP, password=SENHA_AP)
```

**não garante** que a rede fique protegida. Conforme a versão do firmware, o AP
sobe **aberto** e a senha é simplesmente ignorada — sem erro, sem aviso. Você
acha que tem uma rede com senha e qualquer um entra.

Duas atitudes resolvem. Informe o modo de autenticação **explicitamente**, com o
parâmetro `authmode`. E depois **leia o modo de volta** com
`ap.config("authmode")` e imprima no log. Se vier aberto, recuse abrir o
servidor. É a diferença entre *achar* que a rede está protegida e ter a prova
no log.

## O que entregar

- `main.py` com os `# TODO:` resolvidos e os dois blocos de constantes separados;
- o `diagram.json` do seu circuito;
- no README: a **tabela de rotas** (caminho, método, o que devolve, content
  type) e as **chaves do JSON**;
- o roteiro de teste preenchido, com evidências em `evidencias/`.

## Como provar que funciona

O Access Point da simulação **não é alcançável do seu navegador** — ele existe
dentro do Wokwi. Então a evidência vem de outro lugar: **a própria placa vira
cliente dela mesma**. O programa sobe o servidor e, em seguida, abre sockets
para o próprio IP, dispara os requests de teste e imprime a resposta crua no
log serial.

O log com o HTTP literal é uma evidência melhor que uma captura de navegador —
nela você vê o status, os headers e o body exatamente como saíram.

A ordem importa: conecte o cliente **primeiro** e chame `accept()` depois. A
conexão fica esperando na fila de escuta, e um programa só consegue fazer os
dois papéis.

## Roteiro de teste

| # | Ação | Resultado esperado |
|---|---|---|
| 1 | Rodar a simulação | O log mostra o SSID, o IP, a porta de escuta e o modo de segurança lido de volta (não pode ser "aberta") |
| 2 | Requisitar a raiz | `200 OK`, `Content-Type: text/html`, body completo |
| 3 | Conferir o `Content-Length` da raiz | Bate exatamente com os bytes do body |
| 4 | Requisitar a rota de dados | `200 OK` com `application/json`, e o body faz parse |
| 5 | Requisitar ligar e desligar | `200 OK` e o LED acompanha |
| 6 | Requisitar uma rota inexistente | `404`, com body explicativo, sem repetir o caminho pedido |
| 7 | Mandar um request malformado e um gigante | Resposta de erro, servidor de pé |
| 8 | Fechar o cliente no meio do request | Aviso no log, servidor continua atendendo |
| 9 | Disparar 50 requests seguidos | Memória livre estável do início ao fim |
| 10 | Colocar uma senha de 7 caracteres | O programa recusa e explica, em vez de subir aberto |
| 11 | Mandar `POST /ligar` e `POST /nao-existe` | `405` com header `Allow` no primeiro, `404` no segundo, e a carga não acende |

## Perguntas para o relatório

1. Tire a linha em branco da sua resposta e requisite a raiz. O que o cliente
   faz? E por que esse sintoma é mais difícil de diagnosticar que um erro?
2. Compare a memória livre antes e depois dos 50 requests. Agora comente o
   fechamento do socket do cliente e repita. Quantos requests até a queda ficar
   evidente?
3. Seu 404 repete o caminho que o cliente pediu? Se repetisse, o que alguém
   conseguiria fazer com isso?
4. Por que a página não pode usar uma biblioteca de CDN, mesmo que ficasse
   mais bonita?
