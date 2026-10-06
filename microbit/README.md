# CicloAuto – micro:bit V2 (luz traseira)

O micro:bit fica na case traseira, com a tela virada para trás. O celular (app CicloAuto) controla tudo por Bluetooth.
Não precisa de solda nem de nada além do micro:bit V2 e do suporte de pilhas.

## Gravar no micro:bit

**Jeito mais rápido: arquivo .hex**

1. Ligue o micro:bit no PC pelo cabo USB. Ele aparece como um pen drive chamado `MICROBIT`.
2. Arraste o arquivo `cicloauto-rear-v2.hex` para esse drive.
3. O LED amarelo pisca e, quando termina, aparece um ponto piscando de leve no centro da tela: o micro:bit está esperando o celular.

**Pelo MakeCode (para editar)**

1. Abra https://makecode.microbit.org → **Novo projeto** → mude para **JavaScript**.
2. **Extensões** → pesquise `bluetooth` → adicione e aceite remover o "radio".
3. Apague o código e cole o conteúdo de `cicloauto-rear-v2/main.ts`.
4. ⚙️ → **Configurações do projeto** → ligue **"O pareamento não é necessário"**. Sem isso o app não conecta.
5. **Baixar** → arraste o `.hex` para o drive `MICROBIT`.

O `pxt.json` desta pasta já vem com o Bluetooth e o "sem pareamento" configurados.

## Conectar ao app

1. Use o Chrome no Android, com o Bluetooth e a localização ligados.
2. No app, toque no ícone do micro:bit → **Connect micro:bit** → escolha `BBC micro:bit [...]`.
3. O micro:bit mostra ✔ e toca um bip. Se cair a conexão, ele mostra ✖ e apaga tudo.

## O que ele faz

| Mensagem do app | Na tela | Som (alto-falante do V2) |
|---|---|---|
| `SR` / `SL` | seta ">" ou "<" correndo para o lado da curva | "tique" a cada ciclo, como num carro |
| `S0` | apaga a seta | – |
| `B1` / `B0` | freio: a tela inteira acesa | – |
| freio + seta | a seta acesa em cima do quadrado fraco, para as duas coisas ficarem visíveis | tique |
| `H1` / `H0` | alerta (queda / SOS): a tela inteira piscando rápido | sirene, para chamar atenção |

**Botões**

- **A** e **B** ligam a seta esquerda e a direita; **A+B** desliga. Servem para teste, e o app também recebe esses comandos.
- **Logo dourado (toque)**: liga ou desliga o som. Um bip confirma quando o som volta.

## Arquivos

- `cicloauto-rear-v2.hex` – pronto para gravar (é só arrastar para o drive MICROBIT; também abre no MakeCode para editar)
- `cicloauto-rear-v2/main.ts` – programa do micro:bit V2 (MakeCode JavaScript)
- `cicloauto-rear-v2/pxt.json` – configuração do projeto MakeCode (Bluetooth e sem pareamento)
- `rear-light-v1.ts` – versão antiga, sem som, que também roda no micro:bit V1
