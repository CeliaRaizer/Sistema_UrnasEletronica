import { useEffect, useState } from "react";
import LoginPage from "./LoginPage";
import PainelPage from "./PainelPage";
import { getMe, logout as apiLogout } from "./api";

export default function App() {
  const [token, setToken] = useState(() => sessionStorage.getItem("token"));
  const [usuario, setUsuario] = useState(null);
  const [verificando, setVerificando] = useState(true);

  // Ao carregar a pagina, se ja existir um token salvo, valida com a API
  useEffect(() => {
    if (!token) {
      setVerificando(false);
      return;
    }

    getMe(token)
      .then((data) => setUsuario(data))
      .catch(() => {
        sessionStorage.removeItem("token");
        setToken(null);
      })
      .finally(() => setVerificando(false));
  }, [token]);

  function handleLoginSuccess(data) {
    sessionStorage.setItem("token", data.token);
    setToken(data.token);
    setUsuario({ username: data.username });
  }

  async function handleLogout() {
    if (token) {
      await apiLogout(token).catch(() => {});
    }
    sessionStorage.removeItem("token");
    setToken(null);
    setUsuario(null);
  }

  if (verificando) {
    return null; // evita "piscar" a tela de login antes de checar o token salvo
  }

  if (!token || !usuario) {
    return <LoginPage onLoginSuccess={handleLoginSuccess} />;
  }

  return <PainelPage usuario={usuario} onLogout={handleLogout} />;
}
