# Projeto 03 — Sensor de temperatura e umidade DHT22

**Placa:** Raspberry Pi Pico (RP2040) · **Linguagem:** MicroPython · **Esforço estimado:** 3 h

## Contexto

Você vai construir um monitor de temperatura e umidade do ambiente. O DHT22
entrega as duas grandezas por uma linha digital de dados. O programa deve ler
o sensor periodicamente, mostrar os valores e guardar os extremos desde o boot.

Uma leitura pode falhar. A falha faz parte do exercício: o programa precisa
registrá-la, tentar novamente depois e avisar quando o problema persistir.
Quando o sensor voltar a responder, o sistema deve reconhecer a recuperação.

## Antes de começar: um sensor digital também pode falhar

O DHT22 já faz a conversão interna das grandezas físicas. O Pico recebe uma
mensagem digital com temperatura, umidade e um checksum. Não há ADC do Pico
envolvido nessa leitura: usamos `dht.DHT22(Pin(...))`.

O checksum ajuda a detectar uma mensagem corrompida. O timeout acontece quando
uma resposta esperada não chega no prazo. Em ambos os casos, aquele ciclo não
produziu uma nova amostra válida.

### Medir e consultar são operações diferentes

```python
sensor.measure()           # Faz uma nova transação; pode levantar uma exceção.
temperatura = sensor.temperature()
umidade = sensor.humidity()
```

Os dois últimos métodos consultam o resultado guardado pelo driver. Só devem
alimentar a saída e as estatísticas depois de `measure()` terminar com sucesso.
Consultar após uma falha pode acabar reutilizando uma leitura anterior.

### Tratar a exceção no lugar certo

O `try` deve envolver a operação que pode falhar por causa do sensor. A rotina
nativa pode levantar `OSError`, incluindo timeout. Nesse caso, registre a
falha e termine o ciclo. O laço principal continuará e esperará o próximo período.

```python
try:
    sensor.measure()
except OSError as erro:
    registrar_falha(estado, led, str(erro))
    return False
```

Há um detalhe do driver oficial: checksum inválido usa
`Exception("checksum error")`, em vez de uma classe exclusiva. Um segundo
`except Exception as erro` só deve considerar recuperável esse caso exato:
`type(erro) is Exception` e `erro.args == ("checksum error",)`.
Para qualquer outro caso, use `raise` para deixar o erro aparecer.

Essa distinção evita transformar um erro de programação em um falso aviso de
sensor. As exceções são definidas pelo driver, não escolhidas pelo monitor.
Confira o código-fonte indicado no README ao mudar a versão do firmware.

## Antes de começar: respeitar o tempo do sensor

O DHT22 é lento em comparação com o microcontrolador. Sua leitura exige um
intervalo da ordem de dois segundos. Adotaremos **2500 ms** para dar margem à
recomendação do datasheet. Ler mais rápido não produz mais informação útil.

Como há apenas uma tarefa periódica neste projeto, a espera pode ser explícita:

```python
while True:
    time.sleep_ms(PERIODO_LEITURA_MS)
    executar_ciclo(sensor, led, estado)
```

A espera acontece também antes da primeira leitura, permitindo a estabilização
após ligar. Como uma falha retorna ao laço, a próxima tentativa também espera.
Não coloque um laço de tentativas imediatas dentro do tratamento de exceção.

O intervalo entre inícios de leitura inclui o tempo do ciclo anterior, além da
espera. Isso é adequado aqui: garantir o mínimo é mais importante que manter
uma frequência exata. `sleep_ms()` bloqueia o programa; se outras tarefas forem
adicionadas, o agendamento deverá ser revisto. Em uma versão com `ticks_ms()`,
use `ticks_diff()`/`ticks_add()` e evite recuperar atrasos com leituras em rajada.

Uma leitura antecipada pode falhar ou trazer informação inadequada; o comportamento
depende do sensor, driver e simulador. Não use a ausência de exceção como prova
de que o intervalo escolhido é correto.

## Antes de começar: falhas consecutivas e recuperação

Contar falhas consecutivas é diferente de somar todas as falhas desde o boot.
Com limite 3, o comportamento esperado é:

| Evento | Contador depois do evento | Registro | LED |
|---|---|---|---|
| Leitura válida | 0 | INFO com valores | Apagado |
| Primeira falha | 1 | AVISO | Apagado |
| Segunda falha | 2 | AVISO | Apagado |
| Terceira falha | 3 | ERRO | Aceso |
| Quarta falha | 4 | ERRO | Aceso |
| Primeira leitura válida após as falhas | 0 | INFO de recuperação e valores | Apagado |

Também registre recuperação depois de uma ou duas falhas, mesmo que o LED ainda
não tenha acendido. Os mínimos e máximos permanecem guardados durante a falha.

## Antes de começar: inicializar mínimos e máximos

Zero é uma temperatura possível. Por isso, inicializar todos os extremos com
zero cria informação falsa. Se a primeira leitura for 24 °C, o mínimo correto
é 24 °C; se for −10 °C, o máximo correto é −10 °C.

Use `None` para representar ausência de amostra. Na primeira leitura válida,
mínimo e máximo recebem os valores dessa amostra. Nas próximas, compare cada
grandeza com seus próprios extremos. Guarde somente os extremos: não é
necessário criar uma lista de todas as medições.

## O que montar

Obrigatório:

- 1 Raspberry Pi Pico original (`wokwi-pi-pico`).
- 1 DHT22 (`wokwi-dht22`), com alimentação e terra comuns à placa.
- Pull-up na linha de dados; na montagem de referência, resistor de 5,1 kΩ
  entre GP27 e 3V3.

Opcionais (incluídos no gabarito):

- 1 LED vermelho (`wokwi-led`) com resistor de 330 Ω, como indicador de erro.
- 1 chave (`wokwi-slide-switch`) em série com os dados para provocar falha.

Extensão opcional, não implementada no gabarito: sensor NTC
(`wokwi-ntc-temperature-sensor`) para comparar leitura analógica e digital.

A pinagem completa está no README. O pino NC do DHT22 fica desconectado.
Alimente o circuito a 3,3 V. O nome `SDA` no componente Wokwi não transforma
esse protocolo em I²C; ele também é diferente do protocolo Dallas 1-Wire.

## Requisitos funcionais

1. **Leitura periódica**, respeitando o intervalo mínimo do sensor inclusive
   após falhas.
2. **Temperatura em °C e umidade relativa em %**, com uma casa decimal.
3. **Falha não encerra o programa:** capture a exceção do driver, registre
   AVISO e tente novamente no ciclo seguinte.
4. **Após N falhas consecutivas**, eleve o registro a ERRO e acione o LED.
   Na primeira leitura válida, zere o contador, apague o LED e registre a
   recuperação.
5. **Grandeza derivada:** calcule °F com fórmula documentada e referenciada.
6. **Mínimo e máximo de cada grandeza desde o boot**, exibidos em cada leitura
   válida. Falhas não atualizam estatísticas.

## Parâmetros e limites

Separe os dois grupos no topo do arquivo e documente suas fontes no README.

### Ajustáveis (arbitrários)

| Constante | Sugestão | Restrição |
|---|---|---|
| `PERIODO_LEITURA_MS` | 2500 | Inteiro, não inferior ao mínimo do sensor |
| `FALHAS_PARA_ERRO` | 3 | Inteiro maior ou igual a 1 |
| `PINO_DHT` | 27 | Número GP compatível com a montagem |
| `PINO_LED_ERRO` | 26 | GPIO de saída compatível com a montagem |

### Determinados (não arbitrários)

- Intervalo mínimo de referência: cerca de **2 s**; o datasheet recomenda
  período maior que 2 s, justificando o padrão de 2,5 s.
- Faixa de temperatura: **−40 a +80 °C**.
- Faixa de umidade relativa: **0 a 100 %**.
- Resolução: **0,1 °C e 0,1 ponto percentual de UR**. Resolução não é exatidão.
- Comunicação por linha única, com pull-up e protocolo próprio.
- Tipo da exceção: definido pela implementação de `dht` usada no firmware.

## O que entregar

- `aluno/main.py` com os `# TODO:` resolvidos e os dois blocos de constantes.
- `diagram.json` do circuito usado, correspondente à pinagem do programa.
- README com fontes, parâmetros e coluna **Resultado obtido** preenchida.
- Screenshots e log serial reais em `evidencias/`, cobrindo leitura, falha e
  recuperação. Não use a saída esperada como se fosse uma captura de execução.

## Roteiro de teste

| # | Ação | Resultado esperado |
|---|---|---|
| 1 | Iniciar com chave à esquerda e DHT22 em 24 °C / 40 % | Primeira leitura após a espera; 75,2 °F; extremos iguais à amostra |
| 2 | Observar pelo menos cinco ciclos | Sem tentativas mais próximas que o intervalo configurado |
| 3 | Alterar para −10 °C / 20 % e depois 30 °C / 80 % | 14,0 °F e 86,0 °F; extremos de cada grandeza corretos |
| 4 | Chave à direita por uma ou duas tentativas | AVISO; LED apagado; programa continua |
| 5 | Manter desconectado por pelo menos três tentativas | ERRO a partir da terceira; LED aceso |
| 6 | Voltar a chave à esquerda | Recuperação, contador zerado, LED apagado, extremos mantidos |
| 7 | Desconectar novamente depois da recuperação | Contagem reinicia em 1, com AVISO |
| 8 | Reiniciar o programa com sensor desconectado e reconectar | Nenhum extremo artificial; primeira leitura válida inicializa os extremos |

## Perguntas para o relatório

Responda no README, em uma ou duas frases cada:

1. Por que aumentar a frequência de leitura não melhora a resolução do DHT22?
2. Qual é a diferença entre timeout e checksum inválido? Como o driver os sinaliza?
3. Por que um `except Exception` que ignora tudo prejudica o diagnóstico?
4. Por que os mínimos e máximos não devem começar em zero?
5. O que muda ao passar `FALHAS_PARA_ERRO` de 3 para 1? Quais são os ganhos e perdas?
6. O que a chave permite testar? O que continua sem ser comprovado por esse teste?
