# Hospedagem: celular, Docker e nginx

O sistema é um Django (API + `/admin/`) mais um site React. Em produção:

```
celular ──https──▶ nginx ──▶ site React (arquivos estáticos)
                      └────▶ gunicorn/Django  (/api, /admin)  ──▶ banco SQLite (volume /dados)
```

## Qual caminho escolher

| Caminho | Custo | Fica no ar sozinho? | Docker/nginx | Quando usar |
|---|---|---|---|---|
| **A. Docker no seu computador + túnel Cloudflare** | grátis, sem cartão | só com o computador ligado | sim | testes, demonstração, ler o QR no celular **já** |
| **B. PythonAnywhere (conta gratuita)** | grátis, sem cartão | sim | não (eles cuidam do servidor) | deixar um endereço fixo `usuario.pythonanywhere.com` |
| **C. VPS com o mesmo docker-compose** | Oracle Always Free (grátis, pede cartão para verificar; nem sempre há vaga) ou VPS barato | sim | sim | uso real, com domínio próprio |

Evite, por enquanto, hospedagens gratuitas que apagam o disco ou "dormem" (como o plano grátis do Render): o banco é um arquivo SQLite e se perderia. Confira as regras de cada plano na página oficial antes de escolher; elas mudam com frequência.

> **Câmera no celular:** o navegador só libera a câmera em endereço **https**. Os caminhos A, B e C entregam https.

---

## A. Docker + túnel (para o celular funcionar agora)

1. Instale o **Docker Desktop** (Windows precisa de virtualização ativada/WSL2).
2. Na pasta do projeto, crie o arquivo de configuração e edite:
   ```
   copy .env.example .env
   ```
   Troque `DJANGO_SECRET_KEY` (gere com `python -c "import secrets; print(secrets.token_urlsafe(50))"`), `DJANGO_SUPERUSER_USERNAME` e **`DJANGO_SUPERUSER_PASSWORD` (use uma senha forte)**.
3. Suba tudo:
   ```
   docker compose up -d --build
   ```
   Abra http://localhost:8080 e entre com o usuário/senha do `.env` (o mesmo vale para http://localhost:8080/admin/).
4. Para o celular, ligue o túnel:
   ```
   docker compose --profile celular up -d
   docker compose logs tunel
   ```
   Procure `https://alguma-coisa.trycloudflare.com` e abra no celular. O endereço muda cada vez que o túnel é recriado. Abra a aba **Link de confirmação** *por esse endereço* para gerar o QR certo.
5. Para desligar: `docker compose down` (os dados ficam no volume `dados`). **Nunca use `docker compose down -v`**: isso apaga o banco.

**Backup do banco** (faça antes de atualizar e depois de cada etapa importante):
```
docker compose cp web:/dados/db.sqlite3 ./backup.sqlite3
```

**Atualizar para uma versão nova:** substitua os arquivos do projeto e rode `docker compose up -d --build`. As migrações rodam sozinhas.

**Levar o banco que você já tem para o Docker (opcional):**
```
docker compose cp db.sqlite3 web:/dados/db.sqlite3
docker compose exec -u root web chown app /dados/db.sqlite3
docker compose restart web
```

## B. PythonAnywhere (grátis, sem Docker)

> Este caminho **não foi testado** aqui (não há acesso à plataforma). O Django em modo de produção foi testado com gunicorn; os passos abaixo seguem o fluxo padrão da PythonAnywhere. Confira os limites atuais da conta gratuita na página deles (há restrições e a hospedagem precisa ser renovada periodicamente).

1. Crie uma conta gratuita em pythonanywhere.com (seu endereço será `USUARIO.pythonanywhere.com`).
2. No seu computador, compile o site: na pasta `frontend`, `npm run build`. Compacte a pasta `dist` em um `.zip`.
3. Na aba **Consoles → Bash**:
   ```
   git clone https://github.com/CeliaRaizer/Sistema_UrnasEletronica.git
   cd Sistema_UrnasEletronica
   python3 -m venv ~/venv-urnas && source ~/venv-urnas/bin/activate
   pip install -r requirements.txt
   ```
4. Na aba **Files**, envie o zip do `dist` para `Sistema_UrnasEletronica/frontend/` e extraia lá (deve existir `frontend/dist/index.html`).
5. Na aba **Web → Add a new web app → Manual configuration**. Informe o virtualenv `/home/USUARIO/venv-urnas`. Abra o arquivo **WSGI** e troque o conteúdo por:
   ```python
   import os, sys
   sys.path.insert(0, '/home/USUARIO/Sistema_UrnasEletronica')
   os.environ['DJANGO_SETTINGS_MODULE'] = 'sistema_urnas.settings'
   os.environ['DJANGO_DEBUG'] = '0'
   os.environ['DJANGO_SECRET_KEY'] = 'GERE-UMA-CHAVE-LONGA-E-ALEATORIA'
   os.environ['DJANGO_ALLOWED_HOSTS'] = 'USUARIO.pythonanywhere.com'
   os.environ['DJANGO_CSRF_TRUSTED_ORIGINS'] = 'https://USUARIO.pythonanywhere.com'
   os.environ['DJANGO_BEHIND_PROXY'] = '1'
   os.environ['DJANGO_DB_PATH'] = '/home/USUARIO/dados-urnas.sqlite3'
   from django.core.wsgi import get_wsgi_application
   application = get_wsgi_application()
   ```
6. Ainda no console (com o virtualenv ativo e as mesmas variáveis exportadas), rode `python manage.py migrate`, `python manage.py collectstatic` e `python manage.py createsuperuser`. Depois clique em **Reload** na aba Web.

O próprio Django serve o site React, a API e o admin (via WhiteNoise); não é preciso mapear arquivos estáticos.

## C. VPS (Oracle Always Free ou outro)

Instale Docker no servidor, copie o projeto, crie o `.env` (com o seu domínio em `DJANGO_ALLOWED_HOSTS` e `DJANGO_CSRF_TRUSTED_ORIGINS`) e rode `docker compose up -d --build`. Para https com domínio próprio, use um túnel Cloudflare nomeado (conta gratuita) ou coloque o Caddy/nginx com Let's Encrypt na frente da porta 8080.

---

## Cópias de segurança automáticas

Quando alguém usa **Importar planilhas → 3. Apagar dados**, o sistema salva antes uma cópia do banco em `/dados/backups/` (as 10 mais recentes ficam). Para trazer uma cópia para o seu computador:
```
docker compose cp web:/dados/backups/NOME-DO-ARQUIVO.sqlite3 .\
```
Para **restaurar** uma cópia (substitui os dados atuais):
```
docker compose cp .\NOME-DO-ARQUIVO.sqlite3 web:/dados/db.sqlite3
docker compose exec -u root web chown app /dados/db.sqlite3
docker compose restart web
```

## Segurança (leia antes de abrir o link na internet)

- Use **senha forte**; o endereço do túnel é público e o `/admin/` também fica acessível por ele.
- O `.env` guarda segredos e **não vai para o Git** (já está no `.gitignore`).
- `DJANGO_DEBUG=0` é obrigatório fora do seu computador (o `docker-compose.yml` já define isso).
- O SQLite é um arquivo: faça backup. Para o uso real no cartório, vale combinar com o professor um plano de cópia dos dados.

## O que foi testado

Fora do Docker (que não existe no ambiente de desenvolvimento usado): Django em produção com gunicorn e **o `frontend/nginx.conf` real do projeto** na frente. Testados: site, `/confirmar`, API, `/admin/` e CSS, cache, login do admin como se viesse de um túnel https, criação automática do administrador e upload da planilha. **Não testados:** `docker build`/`docker compose` em si e a PythonAnywhere. Se o primeiro `docker compose up --build` mostrar algum erro, envie a mensagem para ajuste.
