const API_URL = import.meta.env.VITE_API_URL || "/api";

/**
 * Faz login na API e retorna o token de autenticacao.
 * Lanca um erro com mensagem legivel se as credenciais forem invalidas.
 */
export async function login(username, password) {
  const response = await fetch(`${API_URL}/login/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || "Não foi possível entrar.");
  }

  return data; // { token, username }
}

/** Busca os dados do usuario logado, usando o token salvo. */
export async function getMe(token) {
  const response = await fetch(`${API_URL}/me/`, {
    headers: { Authorization: `Token ${token}` },
  });

  if (!response.ok) {
    throw new Error("Sessão expirada. Faça login novamente.");
  }

  return response.json();
}

export async function logout(token) {
  await fetch(`${API_URL}/logout/`, {
    method: "POST",
    headers: { Authorization: `Token ${token}` },
  });
}

/** Chamada autenticada genérica; lança Error com a mensagem da API. */
async function chamar(token, caminho, opcoes = {}) {
  const resposta = await fetch(`${API_URL}${caminho}`, {
    ...opcoes,
    headers: { Authorization: `Token ${token}`, ...(opcoes.headers || {}) },
  });
  const dados = await resposta.json().catch(() => ({}));
  if (!resposta.ok) throw new Error(dados.detail || "Não foi possível concluir a operação.");
  return dados;
}

/** Municípios e locais (endpoint público, usado nos filtros). */
export async function getLocais() {
  const resposta = await fetch(`${API_URL}/locais/`);
  if (!resposta.ok) throw new Error("Não foi possível carregar os locais.");
  return resposta.json();
}

/** Painel de acompanhamento. filtros: { municipio, local, status } */
export function getPainel(token, filtros = {}) {
  const params = new URLSearchParams(
    Object.entries(filtros).filter(([, v]) => v)
  ).toString();
  return chamar(token, `/painel/${params ? `?${params}` : ""}`);
}

/** Envia a planilha de rotas (.xlsx/.csv). municipio é opcional. */
export function importarPlanilha(token, arquivo, municipio) {
  const form = new FormData();
  form.append("arquivo", arquivo);
  if (municipio) form.append("municipio", municipio);
  return chamar(token, "/importar/", { method: "POST", body: form });
}

export const importarLocais = (token, arquivo) => {
  const form = new FormData();
  form.append("arquivo", arquivo);
  return chamar(token, "/importar-locais/", { method: "POST", body: form });
};

export const getSecoes = (token) => chamar(token, "/secoes/");

/** Carga da urna: vincula o patrimônio a uma seção (ou marca como contingência). */
export const associarUrna = (token, corpo) =>
  chamar(token, "/urnas/associar/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(corpo),
  });
