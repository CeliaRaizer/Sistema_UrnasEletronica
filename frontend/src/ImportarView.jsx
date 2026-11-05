import { useRef, useState } from "react";
import { importarLocais, importarPresidentes } from "./api";
import ApagarDados from "./ApagarDados";

/** Cartão genérico: escolhe o arquivo, envia e mostra o resultado de cada importação. */
function Importador({ titulo, ajuda, enviar, resultado }) {
  const [arquivo, setArquivo] = useState(null);
  const [enviando, setEnviando] = useState(false);
  const [dados, setDados] = useState(null);
  const [erro, setErro] = useState("");
  const inputRef = useRef(null);

  async function submeter(e) {
    e.preventDefault();
    if (!arquivo) return;
    setEnviando(true); setErro(""); setDados(null);
    try {
      setDados(await enviar(arquivo));
      setArquivo(null);
      if (inputRef.current) inputRef.current.value = "";
    } catch (err) {
      setErro(err.message);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <section className="bloco-importar">
      <h2>{titulo}</h2>
      <p className="ajuda">{ajuda}</p>
      <form className="importar" onSubmit={submeter}>
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
      {dados && <div className="resultado" aria-live="polite">{resultado(dados)}</div>}
    </section>
  );
}

export default function ImportarView({ token, onIrCadastro }) {
  return (
    <>
      <header className="cabecalho"><h1>Importar planilhas</h1></header>

      <Importador
        titulo="1. Locais de votação e rotas"
        ajuda="Planilha .xlsx com os locais de votação e uma aba por rota. O sistema lê os municípios, os locais, as seções de cada local e a rota de cada seção. Se ela tiver uma coluna “Presidente de prédio” (ou “Administrador de prédio”), os nomes também são lidos. Importar de novo atualiza sem duplicar."
        enviar={(arq) => importarLocais(token, arq)}
        resultado={(r) => (
          <>
            <h3>Importação concluída</h3>
            <p>
              <strong>{r.locais}</strong> locais de votação, <strong>{r.secoes}</strong> seções e{" "}
              <strong>{r.rotas}</strong> rotas.{r.avisos.length === 0 && " Nenhum problema encontrado."}
            </p>
            {r.avisos.length > 0 && (
              <ul className="avisos">{r.avisos.map((a, i) => <li key={i}>{a}</li>)}</ul>
            )}
            <button className="botao-pri" onClick={onIrCadastro}>Cadastrar as urnas</button>
          </>
        )}
      />

      <Importador
        titulo="2. Presidentes de prédio (opcional)"
        ajuda="Planilha só com os presidentes: uma coluna “Presidente” (ou “Administrador de prédio”) e uma coluna “Local de votação” (pode estar abreviado, como nas abas de rota) ou “Seção”. Se houver, também são lidos telefone, data de entrega, horário de saída e horário previsto de entrega. Faça antes a importação do passo 1."
        enviar={(arq) => importarPresidentes(token, arq)}
        resultado={(r) => (
          <>
            <h3>Importação concluída</h3>
            <p><strong>{r.atualizados}</strong> locais com presidente informado.
              {r.erros.length > 0 && <> <strong>{r.erros.length}</strong> linhas não foram importadas:</>}</p>
            {r.colunas.length > 0 && <p>Também lidos: {r.colunas.map((c) => ({ telefone: "telefone", data: "data de entrega", saida: "horário de saída", previsto: "horário previsto" }[c])).join(", ")}.</p>}
            {r.erros.length > 0 && (
              <ul className="avisos">{r.erros.map((e) => <li key={e.linha}>Linha {e.linha}: {e.motivo}</li>)}</ul>
            )}
            {r.avisos.length > 0 && <ul className="avisos">{r.avisos.map((a, i) => <li key={i}>{a}</li>)}</ul>}
            {r.locais_sem_presidente.length > 0 ? (
              <details>
                <summary>{r.locais_sem_presidente.length} locais ainda sem presidente</summary>
                <ul className="avisos">{r.locais_sem_presidente.map((n) => <li key={n}>{n}</li>)}</ul>
              </details>
            ) : <p>Todos os locais têm presidente.</p>}
          </>
        )}
      />

      <ApagarDados token={token} />
    </>
  );
}
