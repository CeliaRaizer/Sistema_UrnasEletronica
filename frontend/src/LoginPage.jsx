import { useState } from "react";
import { login } from "./api";
import JusticaEleitoralLogo from "./JusticaEleitoralLogo";

export default function LoginPage({ onLoginSuccess }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setErro("");
    setCarregando(true);

    try {
      const data = await login(username, password);
      onLoginSuccess(data);
    } catch (err) {
      setErro(err.message);
    } finally {
      setCarregando(false);
    }
  }

  return (
    <div className="tela">
      <aside className="lado-claro">
        <JusticaEleitoralLogo size={190} />
      </aside>

      <main className="lado-escuro">
        <div className="form-container">
          <h2>
            Sistema de Controlamento
            <br />
            Urnas Eletrônicas
          </h2>

          {erro && <div className="alerta-erro">{erro}</div>}

          <form onSubmit={handleSubmit} noValidate>
            <div className="campo">
              <label htmlFor="username">Usuário</label>
              <input
                type="text"
                id="username"
                placeholder="Digite nome de usuário"
                autoComplete="username"
                required
                autoFocus
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </div>

            <div className="campo">
              <label htmlFor="password">Senha</label>
              <input
                type="password"
                id="password"
                placeholder="Digite Senha"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>

            <div className="botao-wrapper">
              <button type="submit" className="botao-entrar" disabled={carregando}>
                {carregando ? "Entrando..." : "Entrar"}
              </button>
            </div>
          </form>
        </div>
      </main>
    </div>
  );
}

