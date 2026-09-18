# Histórias de Usuário e Requisitos do Sistema
## Sistema de Controle de Urnas Eletrônicas — Projeto Aplicado II

---

## 1. Pessoas (perfis de usuário que interagem com o sistema)

| Persona | Descrição |
|---|---|
| **Servidor do Cartório Eleitoral** | Administra o sistema: importa a planilha de rotas exportada do Sistema Rotas; realiza cadastro/ajuste manual de urnas quando necessário; acompanha o status geral das entregas. |
| **Presidente de Prédio** | Coordenador responsável pelo local de votação; recebe todas as urnas destinadas àquele prédio (que pode conter várias seções eleitorais) e confirma o recebimento de cada uma. |

### Entidades referenciadas (não realizam login no sistema)

| Entidade | Papel |
|---|---|
| **Empresa Terceirizada / Motorista** | Realiza o transporte físico das urnas até os locais de votação. É apenas **registrada como responsável** no cadastro da rota (vinda da planilha importada) — não acessa o sistema diretamente. |

---

## 2. Histórias de Usuário

### Módulo — Autenticação

- **US01** — Como *servidor do cartório*, quero fazer login com usuário e senha, para acessar o sistema com segurança e garantir que só pessoal autorizado use as funcionalidades administrativas.
- **US02** — Como *servidor do cartório*, quero poder encerrar minha sessão (logout), para proteger o acesso ao sistema quando terminar de usá-lo.

### Módulo — Cadastros administrativos

> Observação: os municípios atendidos (Ibiam, Tangará, Pinheiro Preto, Ibicaré e Treze Tílias) são um conjunto fixo e conhecido — por isso não há uma história de usuário de "cadastrar município" como funcionalidade dinâmica; os municípios já vêm pré-carregados no sistema.

- **US03** — Como *servidor do cartório*, quero importar a planilha de rotas exportada do Sistema Rotas (contendo patrimônio da urna, seção, zona, local de votação e responsável pela distribuição), para carregar essas informações no sistema sem precisar recadastrá-las manualmente.
- **US04** — Como *servidor do cartório*, quero associar manualmente uma urna a uma seção lendo o QR code (ou digitando o patrimônio) da urna, para cadastrar ou ajustar associações que não vieram corretamente na planilha importada, ou quando houver substituição de urna de última hora.
- **US05** — Como *servidor do cartório*, quero que o sistema disponibilize um QR code/link genérico e fixo de acesso à tela de confirmação, para que qualquer presidente de prédio consiga abri-la sem precisar de login, independentemente do local.
- **US06** — Como *servidor do cartório*, quero registrar as urnas de contingência disponíveis por município, para tê-las disponíveis caso uma urna titular apresente falha no dia da eleição.
- **US07** — Como *servidor do cartório*, quero exportar um PDF com o resumo das rotas cadastradas no sistema (locais, seções, urnas, responsável pela entrega e QR/link genérico de acesso à confirmação), para ter um documento de apoio em campo.

### Módulo — Confirmação de entrega (campo)

- **US08** — Como *presidente de prédio*, quero acessar a tela de confirmação escaneando um QR code (ou abrindo um link) genérico, para não precisar de login nem instalar nenhum aplicativo.
- **US09** — Como *presidente de prédio*, quero escanear o QR code da urna ao recebê-la, para confirmar a entrega sem precisar preencher formulários manuais.
- **US09.1** — Como *presidente de prédio*, quero digitar o número de patrimônio da urna como alternativa à leitura do QR code, para conseguir confirmar o recebimento mesmo se o QR estiver danificado ou a câmera falhar.
- **US09.2** — Como *presidente de prédio*, quero informar meu nome ao confirmar o recebimento da urna, para que o cartório saiba quem foi o responsável por aquela confirmação.
- **US10** — Como *presidente de prédio*, quero que o sistema confirme automaticamente se a urna escaneada (ou o patrimônio digitado) é a que deveria estar naquela seção/local, para evitar erro de entrega sem depender de conferência manual.
- **US11** — Como *presidente de prédio*, quero ser alertado imediatamente se a urna não corresponder ao esperado para aquele local, para poder resolver o problema ainda no momento da entrega.
- **US12** — Como *presidente de prédio*, quero registrar uma ocorrência (atraso, avaria, urna incorreta) quando necessário, para que o cartório tenha visibilidade do problema.
- **US13** — Como *presidente de prédio em local sem internet*, quero que minha confirmação seja salva no aparelho e sincronizada depois, para não perder o registro por falta de conexão.

### Módulo — Acompanhamento (painel administrativo)

- **US14** — Como *servidor do cartório*, quero visualizar um painel com o status de todas as urnas (em trânsito, entregue, pendência), incluindo quem é o responsável pela distribuição e quem confirmou o recebimento de cada uma, para acompanhar a logística em tempo real com rastreabilidade de ponta a ponta.
- **US15** — Como *servidor do cartório*, quero filtrar o painel por município ou local de votação, para focar em áreas específicas quando necessário.
- **US16** — Como *servidor do cartório*, quero visualizar a lista de ocorrências registradas, para agir rapidamente sobre problemas reportados.

---

## 3. Requisitos Funcionais (RF)

| Código | Descrição |
|---|---|
| RF01 | O sistema deve permitir a importação de uma planilha (.xlsx/.csv) exportada do Sistema Rotas, contendo no mínimo: patrimônio da urna, seção, zona, local de votação e responsável pela distribuição. |
| RF02 | O sistema deve armazenar o número de patrimônio de cada urna cadastrada — valor que corresponde ao conteúdo codificado no QR code físico já afixado na urna. |
| RF02.1 | O sistema deve disponibilizar um QR code/link genérico e fixo, que dá acesso direto à tela de confirmação, sem exigir login. |
| RF03 | O sistema deve permitir o cadastro/ajuste manual de uma urna e seu vínculo com a seção/local, por meio da leitura do QR code ou da digitação do patrimônio, para os casos não cobertos pela planilha importada. |
| RF04 | O sistema deve permitir a leitura do QR code da urna via câmera (celular/tablet), decodificando-o para obter o número de patrimônio, que será usado na validação (RF06). |
| RF04.1 | O sistema deve permitir identificar a urna por meio da digitação do número de patrimônio, como alternativa à leitura do QR code. |
| RF05 | O sistema deve permitir o cadastro de urnas de contingência, associadas a um município. |
| RF06 | O sistema deve validar automaticamente se a urna identificada (por QR ou patrimônio) corresponde à seção/local esperado. |
| RF07 | O sistema deve registrar a confirmação de entrega com data e hora. |
| RF07.1 | O sistema deve solicitar e registrar o nome da pessoa que confirma o recebimento de cada urna. |
| RF08 | O sistema deve permitir o registro de ocorrências vinculadas a uma entrega específica. |
| RF09 | O sistema deve exibir um painel com o status consolidado das entregas (entregue, em trânsito, pendência), incluindo o responsável pela distribuição e o responsável pela confirmação de recebimento de cada urna. |
| RF10 | O sistema deve permitir filtrar informações do painel por município e/ou local de votação. |
| RF11 | O aplicativo de campo deve funcionar sem conexão à internet, armazenando dados localmente até a sincronização. |
| RF12 | O sistema deve sincronizar automaticamente os dados salvos offline assim que houver conexão disponível. |
| RF13 | O sistema deve permitir a exportação em PDF do resumo de uma rota cadastrada (locais, seções, urnas, responsável e o QR/link genérico de acesso à confirmação). |

---

## 4. Requisitos Não Funcionais (RNF)

| Código | Descrição |
|---|---|
| RNF01 | **Segurança** — O sistema deve permitir login com usuário e senha, validando as credenciais no backend. |
| RNF02 | **Segurança** — O sistema deve impedir o acesso a qualquer funcionalidade sem autenticação válida. |
| RNF03 | **Segurança** — As senhas dos usuários devem ser armazenadas de forma criptografada (hash), nunca em texto puro. |
| RNF04 | **Segurança** — O acesso às funcionalidades deve respeitar o perfil do usuário (ex: apenas o cartório pode importar/cadastrar urnas). |
| RNF05 | **Usabilidade** — A tela de confirmação de entrega deve ser simples o suficiente para uso rápido em campo, sem necessidade de treinamento extenso. |
| RNF06 | **Confiabilidade** — O sistema não deve perder nenhum registro de confirmação, mesmo em caso de falha de conexão. |
| RNF07 | **Desempenho** — A leitura do QR code e a confirmação devem ocorrer em poucos segundos, mesmo em conexão instável. |
| RNF08 | **Compatibilidade** — O módulo de campo deve funcionar em navegadores de celulares comuns, sem exigir instalação complexa. |
| RNF09 | **Auditabilidade** — O sistema deve manter um histórico de quem confirmou cada entrega e quando, para rastreabilidade. |

---
