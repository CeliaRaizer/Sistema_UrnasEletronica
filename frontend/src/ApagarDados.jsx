import { useCallback, useEffect, useState } from "react";
import { apagarDados, getApagar } from "./api";

/** Apagar dados importados, com confirmação digitada e cópia de segurança automática. */
export default function ApagarDados({ token }) {
  const [opcoes, setOpcoes] = useState(null);
  const [aberta, setAberta] = useState(null); // id da opção em confirmação
  const [texto, setTexto] = useState("");
  const [apagando, setApagando] = useState(false);
  const [erro, setErro] = useState("");
  const [aviso, setAviso] = useState("");

  const carregar = useCallback(
    () => getApagar(token).then(setOpcoes).catch((e) => setErro(e.message)), [token]);
  useEffect(() => { carregar(); }, [carregar]);

  const fechar = () => { setAberta(null); setTexto(""); setErro(""); };

  async function confirmar(op) {
    setApagando(true); setErro(""); setAviso("");
    try {
      const r = await apagarDados(token, op.id, texto);
      await carregar();
      fechar();
      setAviso(`${r.detail}${r.backup ? ` Uma cópia de segurança foi salva (${r.backup}).` : ""}`);
    } catch (e) {
      setErro(e.message);
    } finally {
      setApagando(false);
    }
  }

  return (
    <section className="bloco-importar zona-risco">
      <h2>3. Apagar dados</h2>
      <p className="ajuda">
        Remove o que foi importado ou cadastrado, para recomeçar ou limpar um teste. Antes de apagar, o sistema
        salva uma cópia de segurança do banco. Os municípios e os usuários nunca são apagados.
      </p>
      {aviso && <div className="alerta-ok" role="status">{aviso}</div>}

      <ul className="opcoes-apagar">
        {(opcoes ?? []).map((op) => (
          <li key={op.id}>
            <div className="opcao-topo">
              <div>
                <h3>{op.titulo}</h3>
                <p>{op.descricao}</p>
                <p className="opcao-hoje"><span>Hoje:</span> {op.resumo}</p>
              </div>
              {aberta !== op.id && (
                <button className="botao-perigo-sec" onClick={() => { setAberta(op.id); setTexto(""); setErro(""); setAviso(""); }}
                        disabled={op.resumo === "Nada para apagar"}>
                  Apagar…
                </button>
              )}
            </div>
            {aberta === op.id && (
              <form className="confirmar-apagar" onSubmit={(e) => { e.preventDefault(); confirmar(op); }}>
                <label>Para confirmar, digite <strong>APAGAR</strong>
                  <input value={texto} onChange={(e) => setTexto(e.target.value)} autoComplete="off" autoFocus />
                </label>
                {erro && <div className="alerta-erro-claro" role="alert">{erro}</div>}
                <div className="form-acoes">
                  <button type="button" className="botao-sec" onClick={fechar} disabled={apagando}>Cancelar</button>
                  <button className="botao-perigo" disabled={apagando || texto.trim().toUpperCase() !== "APAGAR"}>
                    {apagando ? "Apagando…" : "Apagar definitivamente"}
                  </button>
                </div>
              </form>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
