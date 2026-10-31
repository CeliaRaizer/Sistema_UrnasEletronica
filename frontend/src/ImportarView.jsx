import { useRef, useState } from "react";
import { importarLocais } from "./api";

export default function ImportarView({ token, onIrCadastro }) {
  const [arquivo, setArquivo] = useState(null);
  const [enviando, setEnviando] = useState(false);
  const [resultado, setResultado] = useState(null);
  const [erro, setErro] = useState("");
  const inputRef = useRef(null);

  async function enviar(e) {
    e.preventDefault();
    if (!arquivo) return;
    setEnviando(true); setErro(""); setResultado(null);
    try {
      setResultado(await importarLocais(token, arquivo));
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
      <header className="cabecalho"><h1>Importar planilha de locais e rotas</h1></header>
      <p className="ajuda">
        Envie a planilha .xlsx com os locais de votação e uma aba por rota. O sistema lê os municípios,
        os locais, as seções de cada local e a rota de cada seção. Importar de novo atualiza os dados sem duplicar.
      </p>

      <form className="importar" onSubmit={enviar}>
        <label className="arquivo">
          <span>Arquivo da planilha</span>
          <input ref={inputRef} type="file" accept=".xlsx,.xlsm"
                 onChange={(e) => setArquivo(e.target.files[0] || null)} />
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
            <strong>{resultado.locais}</strong> locais de votação, <strong>{resultado.secoes}</strong> seções
            e <strong>{resultado.rotas}</strong> rotas.
            {resultado.avisos.length === 0 && " Nenhum problema encontrado."}
          </p>
          {resultado.avisos.length > 0 && (
            <>
              <p><strong>{resultado.avisos.length}</strong> avisos para conferir na planilha:</p>
              <ul className="avisos">{resultado.avisos.map((a, i) => <li key={i}>{a}</li>)}</ul>
            </>
          )}
          <button className="botao-pri" onClick={onIrCadastro}>Cadastrar as urnas</button>
        </section>
      )}
    </>
  );
}
