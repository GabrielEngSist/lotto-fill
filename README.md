# Apostas CSV → Loterias Online da Caixa

Script em Python que lê um CSV com seus jogos, pergunta **em qual concurso você quer participar** e, usando o cookie da sua sessão em [loteriasonline.caixa.gov.br](https://www.loteriasonline.caixa.gov.br), marca as dezenas no volante e coloca cada jogo no carrinho.

O pagamento continua sendo feito por você no site oficial. Este programa não envia cartão, Pix nem senha.

## O que você precisa

- Python 3.10 ou mais novo
- Google Chrome, Edge ou Firefox com login feito no Loterias Online da Caixa
- O Playwright baixa um Chromium só para marcar os números; a sessão sai do **seu** navegador

## Instalação

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

## CSV de entrada

Cabeçalho esperado:

```text
Jogo,D1,D2,…,DN,Numeros
```

| Coluna    | Função                                                                 |
|-----------|------------------------------------------------------------------------|
| `Jogo`    | Identificador da linha (pode ser a concatenação das dezenas)           |
| `D1…DN`   | Cada dezena do volante                                                 |
| `Numeros` | String com todas as dezenas de D1 até DN (com ou sem separador)        |

O delimitador é detectado sozinho (vírgula, ponto e vírgula do Excel brasileiro, tab). `Números` com acento também vale.

Exemplos de `Numeros` para a Mega-Sena:

```text
051223334455
05 12 23 33 44 55
05,12,23,33,44,55
```

Se as colunas `D1…DN` vierem preenchidas, elas têm prioridade. Sem elas, o script quebra a coluna `Numeros` (ou o próprio `Jogo`) em dezenas de 2 dígitos — 1 dígito no Super Sete.

Colunas opcionais:

- `Mes` — Dia de Sorte (`JAN`…`DEZ` ou `1`…`12`)
- `Time` — Timemania (`1`…`80` ou `TM12`)
- `Trevos` — +Milionária (`1 4` ou `T1 T4`)
- `Espelho` — Lotomania (`sim` / `1`)

Há exemplos em `exemplos/megasena.csv`, `exemplos/lotofacil.csv` e `exemplos/dia_de_sorte.csv`.

## Sessão (cookie automático)

Por padrão o script **lê sozinho** o cookie de autenticação mais recente do Chrome, Edge, Brave, Chromium ou Firefox, só do domínio `loteriasonline.caixa.gov.br`. Ele escolhe o perfil em que você entrou por último (o que tiver `JSESSIONID` mais recente). Os valores dos cookies não são impressos.

1. Entre em https://www.loteriasonline.caixa.gov.br no Chrome (ou Firefox) e faça login.
2. Rode o script. Ele copia o banco de cookies (incluindo o WAL, então o navegador pode ficar aberto).

```bash
python apostas.py exemplos/megasena.csv
python apostas.py --listar-sessoes
python apostas.py jogos.csv --navegador firefox
```

Se o Chrome recente no Windows recusar a descriptografia (proteção App-Bound), feche o Chrome e tente de novo, ou use o Firefox — os cookies dele não são criptografados da mesma forma.

Ainda dá para passar o cookie na mão, se quiser:

`--cookie "JSESSIONID=…"`, `--cookie-arquivo cookies.txt`, ou as variáveis `CAIXA_COOKIE` / `CAIXA_COOKIE_FILE`. `--sem-cookie-navegador` desliga a leitura automática.

O cookie é a sua sessão. Não compartilhe e não grave em repositório.

## Uso

```bash
python apostas.py exemplos/megasena.csv
```

O programa pergunta:

```text
Qual concurso você quer participar?

   [ 1] Mega-Sena                    6 a 15 dezenas, de 01 a 60
   [ 2] Lotofácil                    15 a 20 dezenas, de 01 a 25
   [ 3] Quina                        …
```

Digite o número ou o nome (`mega-sena`, `lotofacil`, `quina`, …). Se a API pública da Caixa responder, o resumo do próximo concurso aparece na tela. As apostas entram no concurso **em aberto** no site.

Sem prompt (útil em script):

```bash
python apostas.py exemplos/megasena.csv --modalidade mega-sena
```

Só validar o CSV, sem abrir o navegador:

```bash
python apostas.py exemplos/megasena.csv --modalidade mega-sena --dry-run
```

Outras opções:

| Flag | Efeito |
|------|--------|
| `--navegador chrome` | Lê só esse navegador (`auto`, `edge`, `firefox`, `brave`) |
| `--listar-sessoes` | Mostra os perfis com cookie da Caixa, sem valores |
| `--sem-cookie-navegador` | Não lê o Chrome/Firefox; pede cookie colado |
| `--teimosinha N` | Clica N vezes no `+` da Teimosinha |
| `--delay 1.2` | Pausa entre jogos (segundos) |
| `--inicio 10` | Começa a partir do 10º jogo válido |
| `--limite 5` | Envia só 5 jogos (teste) |
| `--headless` | Navegador invisível (precisa de cookie válido) |
| `--fechar` | Fecha o Chrome ao terminar |
| `--listar` | Lista as modalidades |

Se o cookie estiver vencido e o Chrome estiver visível, o script espera você fazer login na janela e apertar Enter.

## Modalidades

Mega-Sena, Lotofácil, Quina, Lotomania, Dupla Sena, Dia de Sorte, Timemania, +Milionária, Super Sete, Loteca, Mega da Virada, Lotofácil da Independência e Quina de São João.

Concursos especiais só funcionam quando o site da Caixa está com aquela modalidade à venda.

## Testes

```bash
pip install pytest
python -m pytest -q
```

## Avisos

- Use apenas na **sua** conta, com jogos **seus**, no site oficial.
- A Caixa muda o HTML de vez em quando; se o volante mudar, os seletores (`n01`, `colocarnocarrinho`, `limparvolante`) podem precisar de ajuste.
- O site costuma responder só a partir do Brasil. VPN fora do país tende a receber HTTP 403.
- Conferir o carrinho antes de pagar é obrigatório.
