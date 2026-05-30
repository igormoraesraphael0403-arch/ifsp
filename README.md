# Bot do ticket SICA

Esse projeto abre o SICA do restaurante do IFSP Suzano, preenche o prontuário `sz3083179`, tenta extrair o token/ticket gerado e envia o resultado por email. Se ele não conseguir isolar o token sozinho, manda uma screenshot e o HTML da página para conferência.

## 1. Instalar Python

Use Python 3.11 ou mais recente.

## 2. Criar ambiente virtual

No PowerShell, dentro desta pasta:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install chromium
```

## 3. Configurar email

Copie `.env.example` para `.env` e preencha:

- `SMTP_USER`
- `SMTP_PASS`
- `EMAIL_FROM`

Se usar Gmail, o jeito grátis e estável é:

1. ativar verificação em duas etapas na conta
2. criar uma **senha de app**
3. usar essa senha em `SMTP_PASS`

## 4. Rodar manualmente

No PowerShell:

```powershell
Copy-Item .env.example .env
# edite o arquivo .env com seus dados SMTP
.venv\Scripts\Activate.ps1
python .\generate_ticket.py
```

## 5. Agendar de segunda a sexta às 09:00

Depois que o teste manual funcionar:

```powershell
.venv\Scripts\Activate.ps1
.\install_task.ps1
```

Isso cria uma tarefa no Agendador do Windows chamada `SICA Ticket IFSP`.

## 6. Rodar no GitHub Actions

Se você preferir deixar tudo na nuvem, o workflow já está pronto em `.github/workflows/sica-ticket.yml`.

Ele roda:

- manualmente pela aba **Actions**
- automaticamente de **segunda a sexta às 09:00 no horário de Brasília**

Observação: no GitHub Actions o agendamento usa **UTC**, então o workflow foi configurado para `12:00 UTC`, que corresponde a `09:00` em `America/Sao_Paulo`. Em dias de pico o GitHub pode atrasar alguns minutos.

### Secrets necessários no repositório

Adicione em **Settings > Secrets and variables > Actions**:

- `SICA_PRONTUARIO` = `sz3083179`
- `DEST_EMAIL` = `dujunarezi@gmail.com`
- `SMTP_USER` = seu Gmail
- `SMTP_PASS` = sua senha de app do Gmail
- `EMAIL_FROM` = seu Gmail

### Como publicar no GitHub

1. crie um repositório vazio no GitHub
2. suba esta pasta para esse repositório
3. adicione os secrets acima
4. abra a aba **Actions**
5. rode **SICA Ticket** manualmente uma vez para testar

## Observações

- O email de destino está definido como `dujunarezi@gmail.com`.
- O script salva evidências em `artifacts\`.
- O script lê automaticamente as variáveis do arquivo `.env`.
- Se o site mudar os campos ou bloquear automação, talvez seja preciso ajustar os seletores.
