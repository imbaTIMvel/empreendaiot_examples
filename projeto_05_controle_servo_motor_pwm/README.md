# 05 — Controle de servo motor por PWM

## Objetivo

Controlar a abertura de uma persiana didática com um potenciômetro e um servo.
Relacionar leitura analógica, ângulo e largura de pulso; suavizar o movimento,
filtrar pequenas variações e executar um encerramento controlado.

## Ambiente

- **Placa:** Raspberry Pi Pico original, RP2040 (`wokwi-pi-pico`). Mantém a
  plataforma do projeto 03, com ADC e PWM nativos do MicroPython.
- **Firmware / versão:** MicroPython 1.27.0; UF2 incluído em
  `gabarito/firmware/`, com origem, SHA-256 e licença. Não requer PlatformIO.
- **Link da simulação publicada:** PENDENTE — publicar após testar.
- **Estado:** código e verificações locais preparados; execução interativa,
  calibração observada e evidências do Wokwi ainda PENDENTES.

| Caminho | Conteúdo |
|---|---|
| `aluno/main.py` | Exercício com `# TODO:` e bloqueio explícito antes de ativar PWM |
| `gabarito/main.py` | Controle completo e modo de calibração |
| `gabarito/diagram.json` | Pico, potenciômetro, servo e botão de encerramento |
| `gabarito/wokwi.toml` | Configuração local com porta serial 4000 |
| `gabarito/firmware/` | Firmware e avisos de redistribuição |
| `evidencias/` | Reservada para registros reais; `.gitkeep` mantém a pasta no Git |
| `enunciado.md` | Tarefa e perguntas do aluno |

## Componentes

| Componente (nome no Wokwi) | Qtd | Obrigatório / Opcional | Observação |
|---|---|---|---|
| `wokwi-pi-pico` | 1 | Obrigatório | Pico original, RP2040 |
| `wokwi-servo` | 1 | Obrigatório | Servo de posição, curso 0°–180° |
| `wokwi-potentiometer` | 1 | Obrigatório | Referência de abertura |
| `wokwi-pushbutton` | 1 | Opcional, incluído | Botão vermelho ENCERRAR; não é comando abre/fecha |
| `board-ssd1306` | — | Opcional, não incluído | Extensão para exibir ângulo |
| Dois `wokwi-pushbutton` | — | Opcional, não incluído | Extensão para modo alternativo abre/fecha |

O botão ENCERRAR permite testar a finalização dentro do programa antes de
interromper o simulador. Os repiques não alteram a decisão: a primeira leitura
pressionada encerra definitivamente o laço, sem alternância de estado.

## Pinagem

| Componente | Pino do componente | Pino da placa | Observação |
|---|---|---|---|
| Potenciômetro | VCC | 3V3, físico 36 | Entrada analógica limitada à alimentação de 3,3 V |
| Potenciômetro | GND | GND, físico 38 (`GND.8`) | Terra comum |
| Potenciômetro | SIG | GP26 / ADC0, físico 31 | `ADC(Pin(26))` |
| Servo | V+ | VBUS, físico 40 | 5 V na montagem simulada |
| Servo | GND | GND, físico 38 (`GND.8`) | Mesmo terra do Pico |
| Servo | PWM | GP15, físico 20 | Sinal de controle; não é alimentação |
| Botão ENCERRAR | 1.l | GP14, físico 19 | Entrada com pull-up interno |
| Botão ENCERRAR | 2.l | GND, físico 18 (`GND.4`) | Pressionado = nível baixo |

No hardware físico, dimensione a alimentação de 5 V do servo para sua corrente
de partida/bloqueio e compartilhe o GND. Não alimente o motor pelo GPIO ou pelo
3V3. O circuito simulado não valida capacidade de corrente do USB/VBUS.

## Parâmetros ajustáveis (arbitrários)

| Constante | Valor adotado | Faixa aceitável | Por que esse valor |
|---|---|---|---|
| `PIN_POT` | 26 | GP26, GP27 ou GP28; atualizar circuito | ADC0 disponível |
| `PIN_SERVO` / `PIN_ENCERRAR` | 15 / 14 | GPIO distintos e coerentes com circuito | Facilita montagem |
| `PERIODO_COMANDO_MS` | 20 ms | Inteiro ≥ 20 | Uma atualização no máximo por período nominal PWM |
| `PASSO_MAX_GRAUS` | 2° | > 0 e ≤ 180°; usar passo pequeno | No máximo 100°/s nominalmente |
| `DEADBAND_PCT` | 1,5 ponto percentual | 0 ≤ valor < 100; usual 1–2 | Reduz comandos por pequenas oscilações |
| `ANGULO_SEGURO` | 0° | 0° a 180° | Persiana didática fechada |
| `TEMPO_ACOMODACAO_MS` | 500 ms | ≥ período de comando; validar com atuador | Mantém pulsos antes de desligar |
| `MODO_CALIBRACAO` | `False` | `False` / `True` | Operação pelo potenciômetro por padrão |
| `TEMPO_CALIBRACAO_MS` | 3000 ms | ≥ período de comando | Tempo de observação em cada ponto |
| `PULSO_MIN_US` / `PULSO_MAX_US` | 500 / 2500 µs, nominais | Inteiros, 0 < mínimo < máximo < 20000; validar no servo | Referência inicial da especificação; não calibração concluída |

Os pulsos de extremidade são parâmetros de **calibração do atuador**, não
escolhas livres de velocidade. A condição matemática acima só valida a forma
do pulso; não autoriza qualquer valor no hardware real.

### Conversão, deadband e movimento

`percentual = raw × 100 / 65535`; `ângulo_alvo = percentual × 180 / 100`.
A deadband compara a leitura com a **última referência aceita**. Se a diferença
for menor que 1,5 ponto percentual, mantém o alvo anterior. No limiar ou acima,
aceita o novo alvo. Leituras exatas de 0% e 100% são sempre aceitas para alcançar
os extremos. Assim uma variação lenta acumulada não é perdida.

Mesmo com o alvo estável, a rampa continua até ele: cada ciclo avança no máximo
2°, nos dois sentidos, sem ultrapassagem. A espera de 20 ms é mínima e inclui-se
ainda o tempo de execução/impressão; não há comandos em rajada para compensar
atraso. De 0° a 180° são 90 passos, pelo menos 1,8 s após a inicialização.

O log `ref` mostra o percentual aceito; `ang_cmd` mostra o ângulo comandado,
que durante a rampa pode ser diferente do alvo. Só uma mudança efetiva no duty
gera nova linha de movimento. Mensagens de início, calibração e fim são eventos
separados. O programa não mede a posição real do eixo.

## Limites determinados (não arbitrários)

| Constante | Valor | Fonte (datasheet / especificação / placa) | Verificado em |
|---|---|---|---|
| `PWM_FREQ_HZ` | 50 Hz | Especificação do projeto 05, p. 4; exemplo Wokwi | 15.10.2026, documental |
| `PERIODO_PWM_US` | 20000 µs | 1000000 / 50; relação matemática | 15.10.2026, cálculo |
| `ANGULO_MIN` / `ANGULO_MAX` | 0° / 180° | Referência oficial `wokwi-servo` | 15.10.2026, documental |
| `ADC_MAX_U16` | 65535 | API `machine.ADC.read_u16()` | 15.10.2026, documental |
| `PWM_MAX_U16` | 65535 | API `machine.PWM.duty_u16()` | 15.10.2026, documental |
| `US_POR_SEGUNDO` / `PCT_TOTAL` | 1000000 / 100 | Conversão de unidades / definição percentual | 15.10.2026, cálculo |
| Alimentação do servo simulado | 5 V | Referência `wokwi-servo`, V+ | 15.10.2026, documental |
| Referência de pulsos da ficha | ≈ 0,5 a 2,5 ms | Especificação do projeto; depende da calibração | PENDENTE — calibração nesta montagem |

**Relação:** `pulso_us = mínimo + (ângulo / 180) × (máximo − mínimo)`;
`duty = pulso_us / 20000`; `duty_u16 ≈ duty × 65535`.
O arredondamento final é limitado para dentro da faixa de pulsos configurada.
A escala u16 não significa resolução física de 16 bits: ADC e PWM têm sua
própria quantização. Frequência, duty e pulsos efetivos precisam ser medidos.

### Registro de calibração — preencher após executar

O gabarito usa a referência nominal da ficha. Não foi registrada uma calibração
interativa deste circuito. O exemplo oficial Wokwi mostra pulsos aproximados de
0,5 / 1,5 / 2,4 ms; portanto, não trate 500/2500 µs como universais nem como
valores já medidos. O curso e a faixa efetivos devem ser confirmados no roteiro.

| Alvo | Pulso calculado na escala u16, nominal | Duty u16 | Ângulo observado | Pulso medido / evidência |
|---|---|---|---|---|
| 0° | ≈ 500,19 µs | 1639 | PENDENTE | PENDENTE |
| 90° | ≈ 1500,11 µs | 4915 | PENDENTE | PENDENTE |
| 180° | ≈ 2499,73 µs | 8191 | PENDENTE | PENDENTE |

1. Altere `MODO_CALIBRACAO = True` e envie novamente `main.py`.
2. Observe os três pontos: há rampa e pausa de 3 s em cada um. O potenciômetro
   fica ignorado nesse modo. Ao terminar, retorna à posição segura e desliga.
3. Registre ângulo visual e pulso medido. Para medir pulsos, adicione um
   `wokwi-logic-analyzer`, conecte D0 a GP15 e GND ao terra, e examine o VCD.
4. Se necessário, ajuste os dois limites e repita; registre valores realmente
   observados. Não estenda o curso além de 0°–180° para compensar erro.
5. Volte `MODO_CALIBRACAO = False` e repita os testes funcionais.

### Encerramento e posição segura

Pressione o botão vermelho **ENCERRAR**. O programa deixa de ler o potenciômetro,
retorna gradualmente a 0°, mantém os pulsos por 500 ms, chama `PWM.deinit()` e
força GP15 a nível baixo. Aguarde `PWM desligado` antes de clicar Stop.
Há também tratamento de `KeyboardInterrupt` recebido pelo MicroPython.

O primeiro comando após o boot é a posição segura; sem feedback não há como
conhecer a posição inicial real para suavizar esse primeiro deslocamento.
Depois disso a rampa é aplicada também ao retorno seguro. Sem pulsos, não há
garantia de torque de retenção nem de posição sob carga. Stop, falta de energia,
reset abrupto ou uma segunda interrupção durante o retorno podem impedir a
sequência: um `finally` não executa quando o simulador já foi interrompido.

## Dependências

| Módulo | Origem (embarcado no firmware / arquivo no projeto) | Verificado em |
|---|---|---|
| `machine.Pin`, `machine.ADC`, `machine.PWM` | Firmware MicroPython Pico | 15.10.2026, API oficial; execução simulada pendente |
| `time` | Firmware MicroPython | 15.10.2026, API oficial; execução simulada pendente |
| `mpremote` 1.27.0 | Python do computador, apenas VS Code | Versão correspondente ao firmware |

Não há biblioteca externa do servo: o código converte ângulo em duty. O
firmware incluído é o mesmo Pico 1.27.0 usado no projeto 03.

## Como executar

### No navegador

1. Abra <https://wokwi.com/projects/new/micropython-pi-pico>.
2. Substitua `main.py` por `gabarito/main.py` e `diagram.json` pelo arquivo
   correspondente. O firmware e `wokwi.toml` são apenas para o VS Code.
3. Clique Play. O programa imprime o cabeçalho e inicializa a posição segura.
4. Clique no potenciômetro e mova o controle. Home/End levam aos extremos;
   setas fazem ajustes finos. Observe servo e log.
5. Para encerrar corretamente, pressione ENCERRAR e aguarde a mensagem final.
6. Publique o projeto e registre link e versão de firmware efetivamente usada.

### No VS Code / Windows

1. Extraia o ZIP e abra **a pasta `gabarito`** com Arquivo → Abrir Pasta.
   O UF2 já está incluído no caminho configurado em `wokwi.toml`.
2. Use Wokwi for VS Code com licença configurada. Abra um terminal PowerShell
   na pasta `gabarito` e confirme o Python:

   ```powershell
   python --version
   python -m pip install mpremote==1.27.0
   ```

   Se `python` não existir, instale Python pelo site oficial, habilite sua
   inclusão no PATH quando oferecida e reabra o VS Code. Se apenas `py` estiver
   disponível, substitua `python` por `py` nos comandos.

3. Execute **Wokwi: Start Simulator** pela paleta `Ctrl+Shift+P`.
4. Com o circuito visível, execute no terminal:

   ```powershell
   python -m mpremote connect port:rfc2217://localhost:4000 run main.py
   ```

5. **As leituras aparecem nesse terminal.** Abra o painel com Ctrl+J. Play
   carrega o MicroPython; esse comando envia e executa o código. Não use Build
   do PlatformIO nem `python main.py` no computador.
6. Mova o potenciômetro e teste. Use ENCERRAR para devolver o controle ao terminal.
   Para repetir, solte o botão e execute novamente o comando do passo 4.
7. Repita o envio após alterar o código ou reiniciar a simulação. O filesystem
   do simulador não persiste ao parar. Mantenha sua aba visível.

Para testar o exercício resolvido, use no mesmo terminal e circuito:

```powershell
python -m mpremote connect port:rfc2217://localhost:4000 run ../aluno/main.py
```

No arquivo original do aluno, `NotImplementedError` é intencional até concluir
os TODOs. Conexão recusada: confira Play e porta 4000. Falha de raw REPL:
encerre outras conexões mpremote e mantenha o simulador visível; se persistir,
reinicie a simulação e repita o envio. Não é necessário selecionar uma COM física.

### Preparar o commit

Coloque `05-controle-servo-pwm` na raiz do repositório. A numeração e o kebab-case
seguem a especificação anexada; a organização interna mantém o formato anterior.

```powershell
git add -- 05-controle-servo-pwm
git diff --cached --stat
git diff --cached
git commit -m "feat(05-servo): adiciona controle de servo por PWM"
```

O firmware e sua licença acompanham o pacote para reproduzir a execução local.
Revise todo o conteúdo staged antes do commit. A especificação pede PR revisado
por outra pessoa da monitoria e aprovação da coordenação antes da branch principal.
Nenhum commit ou publicação foi executado automaticamente.

## Roteiro de teste

| # | Ação | Resultado esperado | Resultado obtido |
|---|---|---|---|
| 1 | RF1: comandar 0%, cerca de 50% e 100%; aguardar estabilizar | Alvos 0°, cerca de 90°, 180°; sem ultrapassar curso | PENDENTE — Wokwi |
| 2 | RF2: executar modo de calibração e medir pulsos / ângulos | Tabela de calibração preenchida; limites ajustados se necessário; 50 Hz | PENDENTE — Wokwi |
| 3 | RF3: partir de 0% e mudar bruscamente para 100%, depois voltar | Passos ≤ 2°, sem salto; ida completa em pelo menos 1,8 s | PENDENTE — Wokwi |
| 4 | RF4: estabilizar perto de 50%, variar < 1,5 ponto percentual e depois ≥ 1,5 em relação à referência aceita | Sem novo alvo abaixo do limiar; nova rampa ao atingir; testar também 0% e 100% | PENDENTE — Wokwi |
| 5 | RF5: observar rampa e depois manter o potenciômetro parado | Uma linha por mudança efetiva de duty, com percentual e ângulo; silêncio em repouso | PENDENTE — Wokwi |
| 6 | RF6: estabilizar perto de 180° e pressionar ENCERRAR | Rampa até 0°, manutenção por 500 ms e PWM desligado; nenhum comando fora da faixa | PENDENTE — Wokwi |

Arquivos sugeridos **a coletar**: `circuito-montado.PNG`, `calibracao-0.PNG`,
`calibracao-90.PNG`, `calibracao-180.PNG`, `calibracao.vcd`, `rampa.PNG`,
`deadband.PNG`, `encerramento.PNG` e `log-serial-completo.txt` em `evidencias/`.
Não confunda tabela de valores esperados ou logs de testes locais com evidência
de simulação. A pasta não contém capturas inventadas.

**Verificação local: 12 testes passaram.** Conversões, deadband, rampa, faixa do PWM, validação de
configuração e ordem do encerramento exercitadas em CPython com substitutos
de hardware. Esses testes não comprovam ângulo visual, tempo mecânico ou pulsos
efetivos no Wokwi. Os testes de aceitação acima continuam pendentes.

## Limitações da simulação

- A corrente do motor, carga, torque, inércia, folgas, alimentação e ruído do
  potenciômetro real não são validados por esta montagem.
- O log apresenta ângulo comandado. O servo de três fios não devolve medição
  de posição ao Pico; não podemos comprovar por software que o eixo chegou.
- Os pulsos nominais precisam de calibração para a montagem e para cada modelo
  físico. A especificação não identifica um fabricante/modelo real de servo.
- A deadband reduz mudanças do comando; não elimina toda fonte de jitter físico.
- A espera é bloqueante neste projeto de uma tarefa; o projeto 06 introduz
  temporização não bloqueante. Período de software e frequência PWM são distintos.
- Stop encerra a simulação imediatamente; use ENCERRAR para testar retorno seguro.

## Referências

- Especificação dos Projetos de Simulação — Wokwi + MicroPython, EmpreendAIoT,
  versão 1.2, fornecida com a tarefa: estrutura pp. 1–2, projeto 05 p. 4;
  consulta em 15.10.2026.
- Wokwi, servo: <https://docs.wokwi.com/parts/wokwi-servo> — 15.10.2026.
- Wokwi, pulsos e calibração (exemplo, não datasheet universal):
  <https://blog.wokwi.com/learn-servo-motor-using-wokwi-logic-analyzer/> — 15.10.2026.
- Wokwi, potenciômetro: <https://docs.wokwi.com/parts/wokwi-potentiometer> — 15.10.2026.
- Wokwi, Pico: <https://docs.wokwi.com/parts/wokwi-pi-pico> — 15.10.2026.
- MicroPython, PWM: <https://docs.micropython.org/en/v1.27.0/library/machine.PWM.html> — 15.10.2026.
- MicroPython, ADC: <https://docs.micropython.org/en/v1.27.0/library/machine.ADC.html> — 15.10.2026.
- Wokwi, execução local: <https://docs.wokwi.com/vscode/vscode-micropython> e
  <https://docs.wokwi.com/vscode/project-config> — 15.10.2026.
- Firmware: <https://micropython.org/download/RPI_PICO/>; versão 1.27.0 fixa;
  origem e hash em `gabarito/firmware/ORIGEM.txt`.
- Python para Windows: <https://www.python.org/downloads/windows/>.

## Controle

- Elaboração (função): Monitoria — Trilha IoT
- Revisão por par (função): PENDENTE — Data: PENDENTE
- Aprovação (coordenação): PENDENTE — Data: PENDENTE
- Calibração observada e evidências: PENDENTES
- Respostas às perguntas do enunciado: preencher nesta seção antes da revisão.
