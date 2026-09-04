# Sistema de Controle de Urnas — Justiça Eleitoral

Projeto com backend em **Django REST Framework** (API) e front-end em
**React** (Vite), implementando a tela de login com autenticação real
por token.

## Estrutura

```
├── manage.py                 # backend Django
├── requirements.txt          # dependências Python
├── sistema_urnas/            # configurações do projeto Django
├── api/                      # app da API (login, logout, endpoint protegido)
└── frontend/                 # projeto React (Vite)
    └── src/
        ├── api.js            # funções que chamam a API (fetch)
        ├── App.jsx           # controla sessão (login/painel)
        ├── LoginPage.jsx     # tela de login
        └── PainelPage.jsx    # painel pós-login (placeholder)
```

## Como rodar o BACKEND (API Django)

1. Crie um ambiente virtual (recomendado):
   ```
   python -m venv venv
   venv\Scripts\activate      (Windows)
   source venv/bin/activate   (Mac/Linux)
   ```

2. Instale as dependências:
   ```
   pip install -r requirements.txt
   ```

3. Crie o banco de dados:
   ```
   python manage.py migrate
   ```

4. Crie um usuário para testar o login:
   ```
   python manage.py createsuperuser
   ```

5. Rode o servidor:
   ```
   python manage.py runserver
   ```
   A API fica em http://localhost:8000/api/

## Como rodar o FRONT-END (React)

Em outro terminal, dentro da pasta `frontend`:

1. Instale as dependências:
   ```
   cd frontend
   npm install
   ```

2. Rode o projeto:
   ```
   npm run dev
   ```
   Acesse http://localhost:5173/ — a tela de login vai aparecer.

**Importante:** o backend (porta 8000) e o front-end (porta 5173) precisam
estar rodando **ao mesmo tempo**, em terminais separados.

## Endpoints da API

- `POST /api/login/` — recebe `{ username, password }`, retorna `{ token, username }`.
- `POST /api/logout/` — invalida o token atual (precisa enviar o token no header `Authorization: Token <token>`).
- `GET /api/me/` — retorna dados do usuário logado (endpoint protegido, exemplo de como proteger as próximas telas).

## Próximos passos sugeridos

- Criar app `urnas` no backend com os models: Municipio, LocalDeVotacao, Secao, Urna, Entrega, Ocorrencia.
- Expor esses models como endpoints da API (usando DRF Serializers + ViewSets) para o React consumir.
- Cadastros administrativos podem começar pelo Django Admin (`/admin/`) enquanto as telas em React não ficam prontas.
- Criar o app/tela de leitura de QR code em React, com suporte a funcionamento offline (PWA) para os locais no interior.
