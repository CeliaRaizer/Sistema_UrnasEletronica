import { useEffect, useRef, useState } from "react";
import { getLocais, importarPlanilha } from "./api";

export default function ImportarView({ token, onVerPainel }) {
  const [municipios, setMunicipios] = useState([]);
  const [municipio, setMunicipio] = useState("");
  const [arquivo, setArquivo] = useState(null);
  const [enviando, setEnviando] = useState(false);
  const [resultado, setResultado] = useState(null);
  const [erro, setErro] = useState("");
  const inputRef = useRef(null);

  useEffect(() => {
    getLocais().then(setMunicipios).catch(() => {});
  }, []);

  async function enviar(e) {
    e.preventDefault();
    if (!arquivo) return;
    setEnviando(true);
    setErro("");
    setResultado(null);
    try {
      setResultado(await importarPlanilha(token, arquivo, municipio));
      setArquivo(null);
      if (inputRef.current) inputRef.current.value = "";
    } catch (err) {
      setErro(err.message);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <>
      <header className="cabecalho"><h1>Importar planilha de rotas</h1></header>
      <p className="ajuda">
        Envie a planilha exportada do Sistema Rotas (.xlsx ou .csv) com patrimônio da urna,
        seção, zona, local de votação e responsável pela distribuição. Importar de novo a
        mesma planilha atualiza os dados sem duplicar urnas.
      </p>

      <form className="importar" onSubmit={enviar}>
        <label className="arquivo">
          <span>Arquivo da planilha</span>
          <input ref={inputRef} type="file" accept=".xlsx,.xlsm,.csv"
                 onChange={(e) => setArquivo(e.target.files[0] || null)} />
        </label>
        <label>
          Município
          <select value={municipio} onChange={(e) => setMunicipio(e.target.value)}>
            <option value="">Usar a coluna de município da planilha</option>
            {municipios.map((m) => <option key={m.id} value={m.id}>{m.nome}</option>)}
          </select>
          <small>Escolha um município só se a planilha não tiver essa coluna.</small>
        </label>
        <button className="botao-pri" disabled={!arquivo || enviando}>
          {enviando ? "Importando…" : "Importar planilha"}
        </button>
      </form>

      {erro && <div className="alerta-erro-claro" role="alert">{erro}</div>}

      {resultado && (
        <section className="resultado" aria-live="polite">
          <h2>Importação concluída</h2>
          <p>
            <strong>{resultado.criadas}</strong> urnas novas e{" "}
            <strong>{resultado.atualizadas}</strong> atualizadas.
            {resultado.erros.length > 0 && <> <strong>{resultado.erros.length}</strong> linhas não foram importadas.</>}
          </p>
          {resultado.erros.length > 0 && (
            <div className="tabela-rolagem">
              <table>
                <thead><tr><th>Linha da planilha</th><th>Problema</th></tr></thead>
                <tbody>
                  {resultado.erros.map((er) => (
                    <tr key={er.linha}><td>{er.linha}</td><td>{er.motivo}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <button className="botao-sec" onClick={onVerPainel}>Ver no acompanhamento</button>
        </section>
      )}
    </>
  );
}
