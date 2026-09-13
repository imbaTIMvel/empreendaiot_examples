# Projeto 04 — Painel de dados em display OLED (I2C)

**Placa:** ESP32 DevKit V1 (ou Raspberry Pi Pico) · **Esforço estimado:** 4 h

## Contexto

Até aqui os seus dados saíam pelo log serial — ou seja, só existiam enquanto
havia um computador ligado na placa. Neste projeto o dispositivo ganha uma
**interface própria**: um display OLED de 128 × 64 pixels mostrando a leitura
de um sensor DHT22.

São dois aprendizados que andam juntos. O primeiro é o **barramento I2C**: O I2C permite que você use somente dois fios e conecte vários dispositivos ao mesmo tempo, contanto que eles tenham endereços próprios. O segundo é **projetar para
uma área minúscula** — cabem 16 caracteres por linha, 8 linhas no total, e o
texto que não couber não some com elegância: ele é cortado no meio.

## Antes de começar: como funciona o barramento I2C

### Dois fios para todo mundo

Cada componente que você usou até agora tinha o seu próprio pino. Isso não escala: uma placa com dez sensores acabaria sem pinos.

O I2C resolve isso com **dois fios compartilhados por todos os dispositivos**:

- **SDA** (*serial data*) — por onde os dados passam, nos dois sentidos;
- **SCL** (*serial clock*) — o pulso que marca o compasso da conversa.

Todos os dispositivos ficam pendurados nos mesmos dois fios. A placa é o
**mestre**: só ela inicia conversa. Os dispositivos são **escravos** e só falam
quando chamados.

### Se todos dividem o mesmo fio, como o certo responde?

Pelo **endereço**. Cada dispositivo no barramento tem um número que o
identifica, e toda conversa começa com o mestre anunciando com quem quer falar.
Os outros ignoram.

O endereço **não é escolha sua**: vem de fábrica no componente. O SSD1306 usa
`0x3C` ou `0x3D`, conforme como o módulo foi configurado. Dois dispositivos com
o mesmo endereço no mesmo barramento brigam — e é por isso que o endereço é um
limite determinado, não um parâmetro ajustável.

### O scan: perguntar em vez de presumir

O mestre consegue descobrir quem está no barramento. Ele chama cada endereço
possível, um por um, e anota quais responderam. É isso que o `i2c.scan()` faz —
devolve a lista de endereços que deram sinal de vida.

**Comece o programa por aí, sempre.** É a primeira ferramenta de diagnóstico do
I2C: se o scan volta vazio, o problema é de fiação ou de alimentação, e nenhuma
linha de código adiante vai consertar isso. Escrever `0x3C` fixo no código faz
você perder essa informação e transformar um erro óbvio num mistério.

## Antes de começar: o framebuffer e a grade de 16 × 8

### Nada aparece até você mandar

Desenhar no OLED tem dois tempos. Quando você chama `oled.text(...)`, nada
acontece na tela: o desenho vai para o **framebuffer**, uma cópia da imagem que
vive na memória da placa. A tela só recebe tudo quando você chama
**`oled.show()`**.

É o erro número um deste projeto: desenhar o painel inteiro, esquecer o `show()`
e ficar olhando para uma tela preta procurando bug no lugar errado.

A separação existe por eficiência: montar a tela pedaço por pedaço na memória e
enviar tudo de uma vez é muito mais rápido que mandar cada letra pelo
barramento.

### A conta da grade

A área útil é **128 × 64 pixels**. A fonte embutida ocupa **8 × 8 pixels por
caractere**. Divida:

- 128 ÷ 8 = **16 caracteres por linha**
- 64 ÷ 8 = **8 linhas de texto**

Confira esses números no driver que você for usar, não aceite de cabeça.

O `oled.text(texto, x, y)` posiciona em **pixels**, não em linhas e colunas. A
linha `N` começa em `y = N * 8`. Vale definir constantes com os `y` de cada
campo, em vez de espalhar números soltos pelo código.

### O texto que não cabe é cortado

Dezesseis caracteres acabam rápido. `"Temperatura: 23.4 C"` tem 19 — o final
some fora da tela, sem aviso.

E o perigo não é o caso que você testou: é o que aparece depois. O uptime em
`9s` cabe; em `86400s` não. O contador de leituras em `5` cabe; em `142000` não.
O requisito 5 cobra que **nenhum estado** estoure a tela, e é por isso que a
tabela de testes pede que você force os valores extremos.

Uma saída melhor que contar caracteres na mão: escrever **uma função que monta a
linha** e corta o que passar do limite. Aí a garantia vale para todos os campos
de uma vez, inclusive os que você ainda não imaginou.

## O que montar

Obrigatórios:

- 1 display OLED SSD1306 128 × 64 I2C (`board-ssd1306`);
- 1 sensor DHT22 (`wokwi-dht22`) como fonte de dados.

Opcional (usado no gabarito):

- 1 push-button (`wokwi-pushbutton`) para alternar entre telas.

> **O módulo do display.** O driver do SSD1306 pode vir embarcado no firmware
> MicroPython ou precisar ser adicionado como arquivo no projeto — isso varia
> entre versões. **Confirme no editor do Wokwi** e registre o resultado, com a
> data, na seção Dependências do seu README. Se precisar adicionar, o arquivo
> está em `gabarito/ssd1306.py`.

## Requisitos funcionais

1. **Scan no boot:** fazer o scan do barramento e imprimir os endereços
   encontrados. Se nada responder, exibir um diagnóstico útil e **encerrar de
   forma controlada** — não travar, nem deixar o MicroPython despejar a
   mensagem de erro padrão (o *traceback*) na tela.
   Atenção a um detalhe: aqui **não há exceção para capturar**. Quando ninguém
   responde, o `i2c.scan()` não dá erro — ele devolve uma **lista vazia**.
   Encerrar de forma controlada é testar essa lista e sair do programa por
   conta própria. O `try` aparece no requisito 4, na leitura do sensor, que aí
   sim levanta exceção de verdade.
2. **Painel** com header fixo de identificação e de dois a três campos de dados
   atualizados periodicamente.
3. **Indicador de atividade** — um caractere que gira, um contador ou um pixel
   piscando — comprovando que o loop não travou.
4. **Tela de erro dedicada** quando a leitura do sensor falha, **visualmente
   distinta** da tela normal.
5. **Layout inteiramente contido na área útil**, sem texto cortado em nenhum dos
   estados. A grade de posicionamento vai no seu README.
6. **A função que desenha a tela recebe os dados por parâmetro** — não lê sensor,
   não usa variável global. E a **taxa de refresh é independente da taxa de
   leitura**.

## Parâmetros e limites

### Ajustáveis (arbitrários)

| Constante | Sugestão | Observação |
|---|---|---|
| `PERIODO_REFRESH_MS` | 500 | com que frequência a tela é redesenhada |
| `PERIODO_LEITURA_MS` | 2500 | nunca abaixo do mínimo do DHT22 |
| `DEBOUNCE_MS` | 50 | se você usar o botão |
| a grade de posicionamento | — | desde que caiba na tela |

### Determinados (não arbitrários)

Estes você **descobre e cita a fonte**:

- **área útil = 128 × 64 pixels**, imposta pelo módulo;
- a **fonte embutida ocupa 8 × 8 pixels** por caractere, o que dá 16 colunas por
  8 linhas — confirmar no driver efetivamente usado;
- **endereço I2C = `0x3C` ou `0x3D`**, conforme a configuração do módulo.
  Descobrir **por scan**, não presumir;
- **clock do barramento I2C** = 100 kHz no modo *standard* ou 400 kHz no *fast*,
  definido pela especificação I2C;
- **o framebuffer só chega à tela após o comando explícito de atualização**;
- **intervalo mínimo entre leituras do DHT22 ≈ 2 s** (datasheet). Ler antes
  disso devolve erro, e esse erro não é defeito do seu código.

## O que entregar

- `main.py` com os `# TODO:` resolvidos e os dois blocos de constantes separados;
- o `diagram.json` do seu circuito;
- no README: a **grade de posicionamento** (qual campo em qual linha) e a
  justificativa do recurso visual que você usou na tela de erro;
- o roteiro de teste preenchido, com evidências em `evidencias/`.

## Roteiro de teste

| # | Ação | Resultado esperado |
|---|---|---|
| 1 | Rodar a simulação | O log lista os endereços encontrados no scan |
| 2 | Desconectar o fio SDA e rodar | Diagnóstico no log e encerramento controlado, sem traceback |
| 3 | Observar o painel em regime | Header fixo, campos atualizando, indicador de atividade girando |
| 4 | Observar por 30 s sem tocar em nada | O indicador de atividade nunca para |
| 5 | Forçar falha do sensor | A tela de erro aparece e é inconfundível à distância |
| 6 | Restaurar o sensor | O painel volta sozinho ao normal |
| 7 | Forçar valores extremos (temperatura mínima e máxima, contadores grandes) | Nenhum texto cortado, em nenhuma linha |
| 8 | Alternar as telas pelo botão | A tela troca no instante do toque, sem toque perdido |

## Perguntas para o relatório

1. O que o scan devolveu? Se você tivesse escrito o endereço fixo no código e o
   módulo viesse configurado em `0x3D`, como o erro apareceria para você?
2. A taxa de refresh e a taxa de leitura são diferentes. O que aconteceria com
   o indicador de atividade se as duas fossem iguais?
3. Cada `show()` envia 1024 bytes pelo barramento. Quanto tempo isso leva a
   100 kHz? E a 400 kHz? O que o loop deixa de fazer enquanto isso acontece?
