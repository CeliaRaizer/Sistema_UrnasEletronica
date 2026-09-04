const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

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
