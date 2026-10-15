# 03 — Sensor de temperatura e umidade DHT22

## Objetivo

Operar um sensor digital com protocolo próprio, respeitar seu intervalo mínimo
de leitura e tratar falhas como parte do funcionamento. Medir temperatura e
umidade, converter Celsius para Fahrenheit, manter extremos e sinalizar falhas
consecutivas e recuperação.

## Ambiente

- **Placa:** Raspberry Pi Pico original, RP2040 (`wokwi-pi-pico`).
- **Linguagem:** MicroPython, com o módulo `dht` do firmware.
- **Firmware de referência no VS Code:** `RPI_PICO-20251209-v1.27.0.uf2`.
  O binário é preparado localmente, conforme a seção Como executar.
- **Firmware no navegador:** fornecido pelo template do Wokwi; registrar a
  versão efetivamente exibida no console ao coletar as evidências.
- **Link da simulação publicada:** `PENDENTE` — o link do projeto 02 não se aplica.

Organização igual à referência do curso:

| Caminho | Conteúdo |
|---|---|
| `aluno/main.py` | Estrutura didática com `# TODO:` |
| `gabarito/main.py` | Implementação completa |
| `gabarito/diagram.json` | Pico, DHT22, pull-up, LED e chave de falha |
| `gabarito/wokwi.toml` | Configuração da extensão Wokwi |
| `evidencias/` | Capturas e logs reais a coletar; inicialmente contém `.gitkeep` |
| `enunciado.md` | Contexto, explicações, requisitos e entrega do aluno |
| `README.md` | Ambiente, parâmetros, execução e roteiro de verificação |

## Componentes

| Componente (nome no Wokwi) | Qtd | Obrigatório / Opcional | Observação |
|---|---|---|---|
| `wokwi-pi-pico` | 1 | Obrigatório | Pico RP2040 |
| `wokwi-dht22` | 1 | Obrigatório | Temperatura e umidade relativa |
| `wokwi-resistor` | 1 | Obrigatório nesta montagem | Pull-up de 5,1 kΩ |
| `wokwi-led` | 1 | Opcional, incluído | Vermelho, indicador de erro |
| `wokwi-resistor` | 1 | Com o LED | 330 Ω em série |
| `wokwi-slide-switch` | 1 | Opcional, incluído | Interrompe a linha de dados |
| `wokwi-ntc-temperature-sensor` | — | Opcional, não incluído | Extensão para comparação analógica/digital |

## Pinagem

| Componente | Pino do componente | Pino da placa | Observação |
|---|---|---|---|
| DHT22 | VCC | 3V3, físico 36 | Alimentação a 3,3 V |
| DHT22 | GND | GND, físico 38 | `GND.8` no Wokwi |
| DHT22 | SDA | GP27, físico 32, através da chave | Protocolo DHT; não é I²C |
| DHT22 | NC | Sem conexão | Não ligar |
| Chave | 2 (central) | GP27 | Nó também ligado ao pull-up |
| Chave | 1 | — | Ligado ao SDA do DHT22 |
| Chave | 3 | Sem conexão | Posição de falha |
| Pull-up 5,1 kΩ | Extremidades | 3V3 e GP27 | Fica no lado do Pico na chave |
| LED | A (ânodo) | GP26, físico 31, via 330 Ω | Aceso quando GPIO está alto |
| LED | C (cátodo) | GND | Terra comum |

No código, `Pin(27)` significa **GP27**, não o pino físico 27.
Chave à esquerda: conectado. À direita: linha de dados aberta, sensor ainda
alimentado. O atributo `bounce: 0` desativa repiques nesse teste.

## Parâmetros ajustáveis (arbitrários)

| Constante | Valor adotado | Faixa aceitável | Por que esse valor |
|---|---|---|---|
| `PERIODO_LEITURA_MS` | 2500 | Inteiro ≥ 2000; preferir margem acima do mínimo | Respeita o tempo do sensor |
| `FALHAS_PARA_ERRO` | 3 | Inteiro ≥ 1 | Tolera falhas isoladas antes de acender o LED |
| `PINO_DHT` | 27 | GPIO compatível com a montagem | Dados no GP27 |
| `PINO_LED_ERRO` | 26 | GPIO de saída disponível | Indicador no GP26 |

## Limites determinados (não arbitrários)

| Constante / característica | Valor | Fonte (datasheet / especificação / placa) | Verificado em |
|---|---|---|---|
| `INTERVALO_MINIMO_MS` | 2000 ms | MicroPython DHT; datasheet Aosong recomenda > 2 s | 14.10.2026, documental |
| `TEMPERATURA_MIN_C` / `TEMPERATURA_MAX_C` | −40 / +80 °C | Datasheet DHT22, seção 3 | 14.10.2026, documental |
| `UMIDADE_MIN_PCT` / `UMIDADE_MAX_PCT` | 0 / 100 % UR | Datasheet DHT22, seção 3 | 14.10.2026, documental |
| `RESOLUCAO_C` / `RESOLUCAO_UR_PCT` | 0,1 / 0,1 | Datasheet DHT22, seção 3 | 14.10.2026, documental |
| Comunicação | Linha única com pull-up | Datasheet DHT22, seções 5 e 6 | 14.10.2026, documental |
| Exceções | `OSError`; checksum: `Exception("checksum error")` | Implementação de `dht` / rotina nativa | 14.10.2026, documental |

### Resolução, intervalo e exatidão não são a mesma coisa

Uma casa decimal descreve o formato e a resolução. Não significa que a medição
seja exata dentro de 0,1 unidade. A frequência de leitura também não muda a
resolução: pedir mais leituras não torna o sensor mais preciso.

A espera é feita antes de cada tentativa. O período efetivo inclui ainda o
tempo de medição e impressão; não há tentativas rápidas para compensar atrasos.
A primeira leitura também espera 2500 ms para estabilização após ligar.

### Conversão e estatísticas

`celsius_para_fahrenheit()` implementa **°F = °C × 9/5 + 32**, conforme NIST.
É uma função pura: 0 °C → 32 °F; −40 °C → −40 °F.

Cada leitura válida exibe °C, % UR e °F com uma casa decimal e os respectivos
mínimos e máximos. Os extremos começam na primeira amostra válida, permanecem
durante falhas e reiniciam com o programa. Não se mantém histórico crescente.

### Falha e recuperação

O `try` envolve somente `sensor.measure()`. `OSError` é registrado como falha
de leitura. O tratamento de `Exception` aceita somente a classe e a mensagem
exatas de checksum do driver; qualquer outra exceção é relançada. Dados fora da
faixa são rejeitados separadamente pela aplicação.

As falhas 1 e 2 geram AVISO; da terceira em diante, ERRO e LED aceso. A primeira
leitura válida registra recuperação, zera o contador e apaga o LED. Nenhuma
falha entra nos extremos nem reapresenta dados antigos como uma nova amostra.

## Dependências

| Módulo | Origem (embarcado no firmware / arquivo no projeto) | Verificado em |
|---|---|---|
| `machine.Pin` | Firmware MicroPython do Pico | 14.10.2026, documental |
| `dht.DHT22` | Firmware MicroPython do Pico | 14.10.2026, documental |
| `time.sleep_ms` | Firmware MicroPython | 14.10.2026, documental |
| `mpremote` 1.27.0 | Python do computador; somente para VS Code | Versão de referência |

Não há biblioteca Arduino, DHTesp ou build do PlatformIO.

## Como executar

### No navegador

1. Abra <https://wokwi.com/projects/new/micropython-pi-pico>.
2. Copie `gabarito/diagram.json` para o `diagram.json` do projeto.
3. Copie `gabarito/main.py` para `main.py`. Para trabalhar como aluno, use
   `aluno/main.py` depois de resolver os TODOs.
4. Clique em **Play**, com a chave à esquerda. Aguarde cerca de 2,5 s para
   a primeira leitura e observe o monitor serial.
5. Altere os controles do DHT22 e execute o roteiro de teste abaixo.
6. Publique/salve o projeto e registre o link e a versão do firmware neste README.

### No VS Code / Windows

O arquivo `wokwi.toml` aponta para um **firmware UF2**, não para `main.py`.
Para manter a estrutura de referência, o binário não está neste pacote de
fontes; baixe-o uma vez para uso local.

1. Abra a pasta **`gabarito`** no VS Code. Instale/ative a extensão Wokwi e sua
   licença. No terminal PowerShell dessa pasta:

   ```powershell
   py -m pip install mpremote==1.27.0
   Invoke-WebRequest -Uri "https://micropython.org/resources/firmware/RPI_PICO-20251209-v1.27.0.uf2" -OutFile "RPI_PICO-20251209-v1.27.0.uf2"
   ```

2. Execute **Wokwi: Start Simulator** em `Ctrl+Shift+P`.
3. Mantenha a aba do simulador visível e, no terminal, execute:

   ```powershell
   py -m mpremote connect port:rfc2217://localhost:4000 run main.py
   ```

4. Para rodar o exercício do aluno na mesma montagem:

   ```powershell
   py -m mpremote connect port:rfc2217://localhost:4000 run ../aluno/main.py
   ```

Execute um programa por vez. Ctrl+C interrompe; Ctrl+] encerra a conexão do
mpremote. Repita o envio após reiniciar a simulação. Só abrir `main.py` no
computador não o executa no Pico simulado. No Linux/macOS, use `python3` no
lugar de `py` e baixe o UF2 pelo endereço acima.

Se a conexão for recusada, confira se a simulação está iniciada e usando a porta
4000. Em timeout ao entrar no REPL, mantenha o simulador visível, encerre outra
sessão mpremote e tente novamente. Não use o botão Build do PlatformIO.

## Roteiro de teste

| # | Ação | Resultado esperado | Resultado obtido |
|---|---|---|---|
| 1 | Iniciar conectado, DHT22 em 24 °C / 40 % | 75,2 °F; uma casa decimal; extremos iguais à primeira leitura | PENDENTE — Wokwi |
| 2 | Observar cinco ciclos e os intervalos | Intervalo entre tentativas não inferior a 2000 ms; espera configurada de 2500 ms | PENDENTE — Wokwi |
| 3 | Alterar para −10 °C / 20 % e depois 30 °C / 80 % | °C min −10,0 / max 30,0; UR min 20,0 / max 80,0; °F min 14,0 / max 86,0 | PENDENTE — Wokwi |
| 4 | Desconectar com a chave por uma ou duas tentativas | AVISO; LED apagado; programa continua | PENDENTE — Wokwi |
| 5 | Manter desconectado por três ou mais tentativas | ERRO a partir da terceira; LED aceso | PENDENTE — Wokwi |
| 6 | Reconectar | INFO de recuperação, contador 0, LED apagado e extremos preservados | PENDENTE — Wokwi |
| 7 | Desconectar novamente após a recuperação | Nova primeira falha: contador 1 e AVISO | PENDENTE — Wokwi |
| 8 | Reiniciar desconectado, depois reconectar | Sem extremos artificiais antes da primeira amostra válida | PENDENTE — Wokwi |

Preencha somente resultados observados. Para o item 2, use marcas de tempo de
simulação ou instrumentação temporária do log; o ritmo visual na tela não é
uma medição precisa do período.

Sugestões de nomes para arquivos **a coletar** em `evidencias/`:
`circuito-montado.PNG`, `leitura-inicial.PNG`, `extremos.PNG`,
`falha-aviso.PNG`, `falha-erro-led.PNG`, `recuperacao.PNG` e
`log-serial-completo.txt`. Esses arquivos ainda não foram produzidos para o
projeto 03. As evidências do projeto 02 não foram copiadas.

**Verificação local do gabarito:** nove testes de lógica em CPython com sensor
e GPIO substitutos passaram: conversão/extremos; timeout/alarme/recuperação;
falha antes da primeira leitura; checksum; propagação de erros inesperados;
faixas e valores não finitos; limite de alarme; configuração inválida; espera
entre tentativas. Essa verificação não comprova o protocolo elétrico nem
substitui o roteiro de simulação. O esqueleto do aluno foi conferido quanto à
sintaxe e permanece intencionalmente incompleto.

## Limitações da simulação

- A chave permite testar ausência de resposta, mas não comprova falha por
  checksum; esse caso foi exercitado somente nos testes de lógica.
- Ler antes do intervalo mínimo não garante uma exceção em toda combinação
  sensor/driver/simulador. O limite deve ser respeitado mesmo sem erro aparente.
- Não se validam aqui exatidão metrológica, deriva, condensação, ruído de cabo
  ou todas as falhas possíveis de hardware.
- Os valores selecionados no simulador não são medições de um ambiente real.
- A velocidade da simulação na tela pode variar com a carga do computador.
- O filesystem simulado no VS Code não persiste ao parar a simulação.

## Referências

- Aosong — datasheet DHT22, especificações e comunicação:
  <https://download.mikroe.com/documents/datasheets/DHT22_datasheet.pdf> — consulta em 14.10.2026.
- MicroPython — leitura do DHT e intervalo mínimo:
  <https://docs.micropython.org/en/latest/esp8266/tutorial/dht.html> — consulta em 14.10.2026.
- MicroPython — implementação do driver DHT, tratamento de checksum:
  <https://github.com/micropython/micropython-lib/blob/master/micropython/drivers/sensor/dht/dht.py> — consulta em 14.10.2026.
- NIST — conversão Celsius/Fahrenheit:
  <https://www.nist.gov/pml/owm/si-units-temperature>.
- Wokwi — Pico e DHT22:
  <https://docs.wokwi.com/parts/wokwi-pi-pico> e <https://docs.wokwi.com/parts/wokwi-dht22>.
- Wokwi — MicroPython no VS Code:
  <https://docs.wokwi.com/vscode/vscode-micropython> — consulta em 14.10.2026.
- Exemplo oficial de execução com mpremote:
  <https://github.com/wokwi/wokwi-vscode-micropython>.
- Firmware oficial do Pico:
  <https://micropython.org/download/RPI_PICO/>. Versão fixada: 1.27.0;
  SHA-256 do UF2: `7942ec963839ecd827887393020e73e6355647a79bc8737bbed7a1ed77145ce9`.

## Controle

- Elaboração (função): Monitoria — Trilha IoT
- Revisão por par (função): `PENDENTE` — Data: `PENDENTE`
- Aprovação (coordenação): `PENDENTE` — Data: `PENDENTE`
- Evidências de execução no Wokwi: `PENDENTE`
- Perguntas para o relatório: responder aos seis itens do `enunciado.md` nesta
  seção antes da revisão por par.

### Preparar o commit

Coloque `projeto_03_dht22` na raiz do repositório, ao lado dos outros projetos.
Execute na raiz do repositório:

```powershell
git add -- projeto_03_dht22/.gitkeep projeto_03_dht22/README.md projeto_03_dht22/enunciado.md projeto_03_dht22/aluno/main.py projeto_03_dht22/gabarito/main.py projeto_03_dht22/gabarito/diagram.json projeto_03_dht22/gabarito/wokwi.toml projeto_03_dht22/evidencias/.gitkeep
git diff --cached --stat
git diff --cached
git commit -m "feat: adiciona projeto 03 DHT22 com Pico e MicroPython"
```

A seleção explícita mantém o firmware baixado e arquivos temporários fora deste
commit. Confira também se já havia outras mudanças preparadas no repositório,
pois `git commit` inclui todo o conteúdo staged. Acrescente evidências reais em
um próximo commit, preenchendo os resultados correspondentes no README.
