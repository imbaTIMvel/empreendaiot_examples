# Projeto 02 — Leitura de potenciômetro (ADC)

**Placa:** ESP32 DevKit V1 (ou Raspberry Pi Pico) · **Esforço estimado:** 2 h

## Contexto

Você vai instrumentar o **sensor de nível de um reservatório**. Na simulação, o
potenciômetro faz o papel da boia: girar o eixo é o mesmo que a água subir ou
descer. O microcontrolador precisa transformar aquilo que o conversor A/D
entrega — um número inteiro sem unidade — em duas grandezas que uma pessoa
consegue ler: **tensão em volts** e **nível em porcentagem**.

O ponto do projeto é justamente implementar essa conversão: o valor *raw* não é o nível.
É uma contagem de degraus do conversor ADC, e só vira uma grandeza física que faça sentido de leitura depois que você aplica a escala correta.

## Antes de começar: como marcar o tempo sem travar o programa

Este é o trecho do código que mais confunde na primeira leitura. Leia esta
seção inteira antes de mexer no `main.py`.

### O problema

Você precisa ler o ADC a cada 50 ms. A solução óbvia é mandar o programa dormir:

```python
while True:
    raw = adc.read_u16()
    time.sleep_ms(50)      # dorme 50 ms
```

Funciona — e é exatamente o que **não** vamos fazer. Durante esses 50 ms o
programa fica **congelado**, ou seja, ele não vai ler botões, não atualiza telas, e, basicamente, não vai responder a nada. Nesse projeto 2, em que há uma tarefa simples, o problema passaria invisível. Mas a partir do projeto 6, em que a placa
precisa medir distância, tocar o buzzer e ler um botão ao mesmo tempo, o `sleep`
deixa de ser aceitável. Por isso, é bom que se aprenda já no começo uma implementação mais elegante, num programa simples.

### A ideia

Em vez de **dormir até** a hora, você **anota** a hora do próximo compromisso e
fica olhando o relógio. É a diferença entre tirar um cochilo e pôr um alarme: com
o alarme, você continua fazendo outras coisas enquanto espera.

O código vira mais ou menos assim:

```python
prox_amostra = time.ticks_ms()          # o primeiro compromisso é agora

while True:
    agora = time.ticks_ms()             # que horas são?
    if ainda_nao_deu_a_hora:
        continue                        # volta pro topo sem fazer nada
    prox_amostra = prox_amostra + 50    # marca o próximo compromisso
    raw = adc.read_u16()                # ... e faz o trabalho
```

O `while` roda milhares de vezes por segundo e quase sempre cai no `continue`.
Só a cada 50 ms ele passa adiante e lê o sensor. É nesse espaço entre as leituras
que, nos projetos seguintes, entram as outras tarefas.

### As três funções

**`time.ticks_ms()`** — o relógio. Devolve há quantos milissegundos a placa
ligou. Não é hora do dia, não é data: é um cronômetro que começa em zero no boot
e só cresce. Sozinho ele não serve para nada; o que interessa é **comparar duas
leituras dele**.

**`time.ticks_diff(a, b)`** — a subtração `a − b`. Responde "quanto tempo passou
entre a marca `b` e a marca `a`". O sinal é o que importa:

| resultado | significa |
|---|---|
| negativo | `a` ainda não chegou em `b` — **ainda não deu a hora** |
| zero ou positivo | a hora chegou (ou já passou) |

**`time.ticks_add(marca, ms)`** — a soma `marca + ms`. Devolve uma marca de tempo
nova, deslocada para o futuro. É com ela que você agenda o próximo compromisso.

### Por que não usar `-` e `+` normais

Porque o cronômetro **não cresce para sempre**. Ele tem um valor máximo; ao
chegar lá, ele volta para zero e recomeça. Isso acontece depois de alguns dias de execução contínua.

Na hora da virada, uma conta comum dá resultado absurdo. Imagine que o máximo
fosse 1000: você marca um compromisso para `20`, e agora são `990`.

- `990 - 20 = 970` → "já passaram 970 ms, a hora chegou!" — **errado**, faltam 30.

As funções `ticks_diff` e `ticks_add` sabem que o contador dá a volta e devolvem
o resultado certo. Por isso a regra é: **marcas de tempo do `ticks_ms()` só se
comparam com `ticks_diff()` e só se somam com `ticks_add()`.** Nunca com `-` e `+`.

### Um detalhe importante do agendamento

Ao marcar o próximo compromisso, conte a partir do **compromisso anterior**, não
do instante em que o código acordou:

```python
prox_amostra = time.ticks_add(prox_amostra, PERIODO_AMOSTRA_MS)   # certo
prox_amostra = time.ticks_add(agora, PERIODO_AMOSTRA_MS)          # acumula atraso
```

Se um ciclo demorar 3 ms a mais, a primeira forma se ajusta sozinha e o ritmo
médio continua sendo 50 ms. A segunda empurra esses 3 ms para frente a cada
volta, e depois de um tempo você não está mais amostrando a 50 ms.

### Acompanhe passo a passo

Com `PERIODO_AMOSTRA_MS = 50` e a placa tendo ligado no instante 1000:

| `agora` | `ticks_diff(agora, prox_amostra)` | o que acontece | `prox_amostra` depois |
|---|---|---|---|
| 1000 | `1000 − 1000 = 0` | não é negativo → **lê o sensor** | 1050 |
| 1003 | `1003 − 1050 = −47` | negativo → `continue` | 1050 |
| 1020 | `1020 − 1050 = −30` | negativo → `continue` | 1050 |
| 1049 | `1049 − 1050 = −1` | negativo → `continue` | 1050 |
| 1051 | `1051 − 1050 = +1` | não é negativo → **lê o sensor** | 1100 |

Entre a primeira e a última linha o `while` deu milhares de voltas. Só duas
delas leram o sensor.

## Antes de começar: o que é filtrar por média móvel

### Por que filtrar

Se você pedir ao ADC duas leituras seguidas, com o potenciômetro parado, e os dois números
não serão iguais. A entrada analógica capta interferência da própria placa, da
fonte, do ambiente — e à isso damos o nome de ruído.

Se você imprimir essa leitura crua, vai imprimir valores diferentes mesmo com o potenciômetro parado. Se acender um LED com ela, o brilho oscila de leve indevidamente. O valor do potenciômetro não mudou; o que mudou foi o ruído.

A saída simples que usaremos aaqui é não confiar em nenhuma leitura isolada e trabalhar com a **média de várias**. 
As flutuações são aleatórias — uma leitura vem um pouco acima, a
seguinte um pouco abaixo — e na média elas se cancelam. O que sobra é o valor de
verdade.

### O que "móvel" quer dizer

Média móvel é a média das **N leituras mais recentes**, recalculada **a cada nova
leitura**. Com `N = 5`:

| leitura nº | janela usada na média |
|---|---|
| 5 | 1, 2, 3, 4, 5 |
| 6 | 2, 3, 4, 5, 6 |
| 7 | 3, 4, 5, 6, 7 |

A janela **desliza**: a cada ciclo entra uma leitura nova e sai a mais antiga. Por
isso "móvel".

Cuidado com a confusão mais comum: **não** são lotes de 5. Não é "junta 5
leituras, tira a média, joga fora, junta outras 5". Sai uma média nova a cada
leitura — a cada 50 ms, não a cada 250 ms.

### O preço do filtro

Filtrar custa **atraso**. A média das 5 últimas leituras carrega 5 × 50 ms =
250 ms de passado. Quando o valor real dá um salto, a média sobe em rampa, não
de uma vez:

| leitura crua | janela | média |
|---|---|---|
| 1000 | 1000, 1000, 1000, 1000, 1000 | 1000 |
| **2000** | 2000, 1000, 1000, 1000, 1000 | 1200 |
| 2000 | 2000, 2000, 1000, 1000, 1000 | 1400 |
| 2000 | 2000, 2000, 2000, 1000, 1000 | 1600 |
| 2000 | 2000, 2000, 2000, 2000, 1000 | 1800 |
| 2000 | 2000, 2000, 2000, 2000, 2000 | 2000 |

São 5 ciclos até a média alcançar o valor real. É essa rampa que você enxerga no
brilho do LED ao girar o potenciômetro de uma vez.

Daí o compromisso, que é a decisão de projeto deste requisito: **janela grande
estabiliza mais e responde mais devagar; janela pequena responde na hora e treme
mais.** Não existe valor certo — por isso `N_MEDIA_MOVEL` está no bloco dos
parâmetros ajustáveis.

> No Wokwi o filtro parece quase inútil: o simulador entrega uma leitura limpa,
> sem o ruído que existe no circuito real. Não conclua daí que ele é dispensável
> — em bancada, sem filtro, o log capta ruído sem poder.

### "Sem estrutura de dados que cresça indefinidamente"

Essa frase está no requisito 3, e é o ponto em que o projeto deixa de ser um
exercício de Python e vira embarcado.

A forma imediata de guardar as leituras é ir empilhando numa lista:

```python
buf.append(raw)          # e nunca tirar nada
```

No computador, isso passa despercebido. Na placa, faça a conta: 20 leituras por
segundo são 1.200 por minuto, 72.000 por hora, 1,7 milhão por dia. Cada uma
ocupa um espaço na memória, e a memória de um microcontrolador é **finita e pequena.** — nada parecido com a do seu notebook.

O programa não quebra na hora. Ele roda lindamente na demonstração, roda no
primeiro teste, e morre de madrugada com `MemoryError`. Esse é o tipo de defeito
mais caro que existe: o que só aparece depois que ninguém está olhando.

**A regra, então:** o tamanho da estrutura tem que ter um teto que **não depende
de há quanto tempo o programa está rodando**. Se a lista tem 5 posições depois de
um minuto, tem que ter 5 depois de uma semana.

O que resolve não é evitar o `append` — é garantir o **descarte**:

```python
buf.append(raw)              # entra a mais nova, no fim
if len(buf) > N_MEDIA_MOVEL:
    buf.pop(0)               # sai a mais antiga, do começo
```

Com as duas linhas juntas, a lista sobe até `N_MEDIA_MOVEL` e trava ali para
sempre. É o `pop` que segura o teto. Sempre que atingirmos o teto, excluímos o primeiro valor da lista (o mais antigo) e mantemos o tamanho dela intacto.

A ideia vale para qualquer coisa que acumule: histórico, fila de envio, log de
eventos, buffer de rede. Antes de guardar algo numa estrutura, pergunte **quem
tira**. Se a resposta for "ninguém", você tem um vazamento de memória, ainda que
ele demore horas para aparecer.

## O que montar

Obrigatório:

- 1 potenciômetro (`wokwi-potentiometer`) ligado a um pino **com ADC**.

Opcionais (recomendados):

- 1 LED (`wokwi-led`) com resistor de 220 Ω a 330 Ω, com brilho proporcional à
  leitura;
- `wokwi-slide-potentiometer` no lugar do rotativo, se você achar o movimento
  linear mais intuitivo para representar "nível".

> Atenção ao escolher o pino no ESP32: use um pino do **ADC1** (GPIO 32 a 39).
> Os pinos do ADC2 deixam de funcionar quando o Wi-Fi está ativo — não é o caso
> deste projeto, mas é um hábito que evita uma dor de cabeça no projeto 8.

## Requisitos funcionais

1. **Amostragem periódica** em intervalo fixo, declarado em constante.
2. **Conversão** do valor raw em tensão (volts, duas casas decimais) e em
   percentual de 0 a 100 %.
3. **Filtragem por média móvel** de N amostras, **sem estrutura de dados que
   cresça indefinidamente** — o buffer é alocado uma vez e reaproveitado.
4. **Saída no log serial em colunas de largura fixa:** raw, tensão, percentual.
5. **Reporte condicional:** só imprime o resultado quando o percentual variar acima do        threshold de reporte, ou seja, é a taxa de "sensibilidade" que evita imprimir o mesmo valor várias vezes se o potenciômetro estiver parado. 
6. **A fórmula de conversão fica isolada em uma função que não acessa
   hardware** — ela recebe números e devolve números.

## Parâmetros e limites

Separe os dois grupos em blocos distintos no topo do arquivo. Eles não são a
mesma coisa e não se alteram com a mesma liberdade.

### Ajustáveis (arbitrários)

São escolhas suas. Os valores abaixo são sugestão inicial, não requisito.

| Constante | Sugestão | Faixa usual |
|---|---|---|
| `PERIODO_AMOSTRA_MS` | 50 | 20 a 1000 |
| `N_MEDIA_MOVEL` | 5 | 4 a 32 |
| `THRESHOLD_REPORTE_PCT` | 1 | 0,5 a 5 |
| pinos escolhidos | — | conforme seu circuito |

### Determinados (não arbitrários)

Estes você **descobre e cita a fonte**, não escolhe:

- a resolução nativa do ADC do ESP32 e do Pico é de **12 bits** (0 a 4095);
- a leitura via `read_u16()` é reescalada para **0 a 65535** independentemente
  da resolução física — é imposição da API do MicroPython. **As duas escalas
  não podem ser misturadas** no mesmo cálculo;
- a **tensão de referência é 3,3 V**, imposta pela placa;
- o ADC do ESP32 **não é linear nas extremidades da faixa**. É característica
  do silício. O efeito que você observar deve ser **documentado**, não
  corrigido com um número mágico no meio do código.

## O que entregar

- `main.py` com os `# TODO:` resolvidos e os dois blocos de constantes separados;
- o `diagram.json` do seu circuito;
- o preenchimento do **roteiro de teste** do README, com a coluna "resultado
  obtido" e as evidências (screenshot + log serial) em `evidencias/`.

## Roteiro de teste

Execute e registre o resultado de cada item:

| # | Ação | Resultado esperado |
|---|---|---|
| 1 | Rodar a simulação sem tocar no potenciômetro | Uma linha inicial e depois silêncio (ou apenas as linhas periódicas) |
| 2 | Girar o potenciômetro até o mínimo | raw ≈ 0, tensão ≈ 0,00 V, 0 % |
| 3 | Girar até o máximo | raw ≈ 65535, tensão ≈ 3,3 V, 100 % |
| 4 | Parar no meio do curso | ≈ 50 %, tensão ≈ 1,65 V |
| 5 | Girar devagar, de ponta a ponta | Uma linha por variação acima do threshold, sem enxurrada |
| 6 | Deixar parado por 1 minuto | Nenhuma linha de variação; colunas continuam alinhadas |

## Perguntas para o relatório

Responda no README, em uma ou duas frases cada:

1. Com `read_u16()`, o valor raw anda de 1 em 1 ou em degraus maiores? Por quê?
2. O que acontece com a leitura nos dois extremos do curso do potenciômetro?
   Você consegue chegar exatamente a 0 % e a 100 %?
3. Se `N_MEDIA_MOVEL` dobrar, o que muda no comportamento do sistema — e o que
   se perde? Teste: quanto tempo passa entre você girar o eixo e o LED chegar ao
   brilho final?
