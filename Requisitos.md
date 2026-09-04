# Histórias de Usuário e Requisitos do Sistema
## Sistema de Controle de Urnas Eletrônicas — Projeto Aplicado II

---

## 1. Pessoas (perfis de usuário)

| Persona | Descrição |
|---|---|
| **Servidor do Cartório Eleitoral** | Administra o sistema: cadastra municípios, locais, seções, urnas e rotas; acompanha o status geral das entregas. |
| **Empresa Terceirizada / Motorista** | Realiza o transporte físico das urnas até os locais de votação. |
| **TAV (Técnico de Apoio à Votação)** | Auxilia na logística de entrega das urnas, podendo acompanhar ou validar etapas do trajeto. |
| **Presidente de Prédio** | Coordenador responsável pelo local de votação; recebe todas as urnas destinadas àquele prédio (que pode conter várias seções eleitorais) e confirma o recebimento de cada uma. |

---

## 2. Histórias de Usuário

### Módulo — Autenticação

- **US01** — Como *servidor do cartório*, quero fazer login com usuário e senha, para acessar o sistema com segurança e garantir que só pessoal autorizado use as funcionalidades administrativas.
- **US02** — Como *usuário do sistema*, quero receber uma mensagem clara quando digito usuário ou senha errados, para saber que preciso corrigir os dados.
- **US03** — Como *usuário do sistema*, quero permanecer conectado mesmo se atualizar a página, para não precisar logar repetidamente durante o uso.
- **US04** — Como *servidor do cartório*, quero poder encerrar minha sessão (logout), para proteger o acesso ao sistema quando terminar de usá-lo.

### Módulo — Cadastros administrativos

- **US05** — Como *servidor do cartório*, quero cadastrar os municípios atendidos, para organizar os locais de votação por região.
- **US06** — Como *servidor do cartório*, quero cadastrar os locais de votação (incluindo se é área urbana ou interior), para saber onde cada urna deve ser entregue.
- **US07** — Como *servidor do cartório*, quero cadastrar as seções eleitorais de cada local, para vincular corretamente cada urna à seção correspondente.
- **US08** — Como *servidor do cartório*, quero cadastrar cada urna e vinculá-la a uma seção/local específico, para que o sistema saiba onde ela deveria estar.
- **US09** — Como *servidor do cartório*, quero que o sistema gere automaticamente um QR code único para cada urna cadastrada, para permitir a confirmação de entrega por leitura.
- **US10** — Como *servidor do cartório*, quero cadastrar rotas de entrega (quais urnas/locais uma mesma empresa ou TAV vai atender), para organizar a logística de distribuição.

### Módulo — Confirmação de entrega (campo)

- **US11** — Como *presidente de prédio*, quero escanear o QR code da urna ao recebê-la, para confirmar a entrega sem precisar preencher formulários manuais.
- **US11.1** — Como *presidente de prédio*, quero informar meu nome ao confirmar o recebimento da urna, para que o cartório saiba quem foi o responsável por aquela confirmação.
- **US12** — Como *presidente de prédio*, quero que o sistema confirme automaticamente se a urna escaneada é a que deveria estar naquela seção/local, para evitar erro de entrega sem depender de conferência manual.
- **US13** — Como *presidente de prédio*, quero ser alertado imediatamente se a urna escaneada não corresponder ao esperado, para poder resolver o problema ainda no momento da entrega.
- **US14** — Como *presidente de prédio*, quero registrar uma ocorrência (atraso, avaria, urna incorreta) quando necessário, para que o cartório tenha visibilidade do problema.
- **US15** — Como *presidente de prédio em local sem internet*, quero que minha confirmação seja salva no aparelho e sincronizada depois, para não perder o registro por falta de conexão.

### Módulo — Acompanhamento (painel administrativo)

- **US16** — Como *servidor do cartório*, quero visualizar um painel com o status de todas as urnas (em trânsito, entregue, pendência), para acompanhar a logística em tempo real.
- **US17** — Como *servidor do cartório*, quero filtrar o painel por município ou local de votação, para focar em áreas específicas quando necessário.
- **US18** — Como *servidor do cartório*, quero visualizar a lista de ocorrências registradas, para agir rapidamente sobre problemas reportados.

---

## 3. Requisitos Funcionais (RF)

| Código | Descrição |
|---|---|
| RF01 | O sistema deve permitir login com usuário e senha, validando as credenciais no backend. |
| RF02 | O sistema deve impedir o acesso a qualquer funcionalidade sem autenticação válida. |
| RF03 | O sistema deve permitir o cadastro de Município, Local de Votação, Seção Eleitoral, Urna e Rota. |
| RF04 | O sistema deve gerar um QR code único por urna cadastrada, vinculado ao seu registro no banco de dados. |
| RF05 | O sistema deve permitir a leitura do QR code da urna por meio de câmera (celular/tablet). |
| RF06 | O sistema deve validar automaticamente se a urna escaneada corresponde à seção/local esperado. |
| RF07 | O sistema deve registrar a confirmação de entrega com data e hora. |
| RF07.1 | O sistema deve solicitar e registrar o nome da pessoa que confirma o recebimento de cada urna. |
| RF08 | O sistema deve permitir o registro de ocorrências vinculadas a uma entrega específica. |
| RF09 | O sistema deve exibir um painel com o status consolidado das entregas (entregue, em trânsito, pendência). |
| RF10 | O sistema deve permitir filtrar informações do painel por município e/ou local de votação. |
| RF11 | O aplicativo deve funcionar sem conexão à internet, armazenando dados localmente até a sincronização. |
| RF12 | O sistema deve sincronizar automaticamente os dados salvos offline assim que houver conexão disponível. |

---

## 4. Requisitos Não Funcionais (RNF)

| Código | Descrição |
|---|---|
| RNF01 | **Segurança** — As senhas dos usuários devem ser armazenadas de forma criptografada (hash), nunca em texto puro. |
| RNF02 | **Segurança** — O acesso às funcionalidades deve respeitar o perfil do usuário (ex: apenas o cartório pode cadastrar urnas). |
| RNF03 | **Usabilidade** — A tela de confirmação de entrega deve ser simples o suficiente para uso rápido em campo, sem necessidade de treinamento extenso. |
| RNF04 | **Confiabilidade** — O sistema não deve perder nenhum registro de confirmação, mesmo em caso de falha de conexão. |
| RNF05 | **Desempenho** — A leitura do QR code e a confirmação devem ocorrer em poucos segundos, mesmo em conexão instável. |
| RNF06 | **Compatibilidade** — O módulo de campo deve funcionar em navegadores de celulares comuns, sem exigir instalação complexa. |
| RNF07 | **Auditabilidade** — O sistema deve manter um histórico de quem confirmou cada entrega e quando, para rastreabilidade. |
| RNF08 | **Escalabilidade** — O sistema deve suportar o cadastro de múltiplos municípios, locais e urnas sem perda de desempenho perceptível. |

---
