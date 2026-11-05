import { useEffect, useState } from "react";
import { excluirLocal, excluirRota, getImpactoLocal, getImpactoRota } from "./api";

const plural = (n, s, p) => `${n} ${n === 1 ? s : p}`;

function listaImpacto(i) {
  const itens = [plural(i.locais, "local", "locais"), plural(i.secoes, "seção", "seções"), plural(i.urnas, "urna", "urnas")];
  if (i.ocorrencias) itens.push(plural(i.ocorrencias, "ocorrência", "ocorrências"));
  return itens.join(", ");
}

/** Pede o texto APAGAR, mostra erro e dispara a exclusão. */
function Confirmacao({ rotulo, executar, onFechar, desabilitado }) {
  const [texto, setTexto] = useState("");
  const [erro, setErro] = useState("");
  const [apagando, setApagando] = useState(false);

  async function enviar(e) {
    e.preventDefault();
    setApagando(true); setErro("");
    try {
      await executar(texto);
    } catch (err) {
      setErro(err.message);
      setApagando(false);
    }
  }

  return (
    <form onSubmit={enviar} className="confirmar-apagar">
      <label>Para confirmar, digite <strong>APAGAR</strong>
        <input value={texto} onChange={(e) => setTexto(e.target.value)} autoComplete="off" autoFocus />
      </label>
      {erro && <div className="alerta-erro-claro" role="alert">{erro}</div>}
      <div className="form-acoes">
        <button type="button" className="botao-sec" onClick={onFechar} disabled={apagando}>Cancelar</button>
        <button className="botao-perigo" disabled={apagando || desabilitado || texto.trim().toUpperCase() !== "APAGAR"}>
          {apagando ? "Excluindo…" : rotulo}
        </button>
      </div>
    </form>
  );
}

/** Excluir uma rota: só a rota, ou a rota e tudo dela. */
export function ExcluirRota({ token, numero, onExcluida, onFechar }) {
  const [impacto, setImpacto] = useState(null);
  const [modo, setModo] = useState("so_rota");
  const [erro, setErro] = useState("");

  useEffect(() => { getImpactoRota(token, numero).then(setImpacto).catch((e) => setErro(e.message)); }, [token, numero]);

  return (
    <div className="excluir-painel">
      <h3>Excluir a Rota {numero}</h3>
      {erro && <div className="alerta-erro-claro" role="alert">{erro}</div>}
      {impacto && (
        <fieldset className="modos">
          <legend>O que excluir?</legend>
          <label className={modo === "so_rota" ? "modo ativo" : "modo"}>
            <input type="radio" name={`modo-${numero}`} checked={modo === "so_rota"} onChange={() => setModo("so_rota")} />
            <span>
              <strong>Só a rota</strong>
              As {impacto.secoes} seções ficam “sem rota”. Locais, seções e urnas continuam.
            </span>
          </label>
          <label className={modo === "tudo" ? "modo ativo" : "modo"}>
            <input type="radio" name={`modo-${numero}`} checked={modo === "tudo"} onChange={() => setModo("tudo")} />
            <span>
              <strong>A rota e tudo dela</strong>
              Apaga {listaImpacto(impacto)}.
              {impacto.confirmadas > 0 && <b className="aviso-forte"> {plural(impacto.confirmadas, "urna já confirmada será apagada", "urnas já confirmadas serão apagadas")}.</b>}
            </span>
          </label>
        </fieldset>
      )}
      <p className="ajuda-pequena">O sistema salva uma cópia de segurança do banco antes de excluir.</p>
      <Confirmacao rotulo="Excluir definitivamente" desabilitado={!impacto} onFechar={onFechar}
                   executar={async (texto) => onExcluida(await excluirRota(token, numero, modo, texto))} />
    </div>
  );
}

/** Excluir um local de votação com as seções e urnas dele. */
export function ExcluirLocal({ token, local, onExcluido, onFechar }) {
  const [impacto, setImpacto] = useState(null);
  const [erro, setErro] = useState("");

  useEffect(() => { getImpactoLocal(token, local.local_id).then(setImpacto).catch((e) => setErro(e.message)); }, [token, local.local_id]);

  return (
    <div className="excluir-painel">
      <h3>Excluir o local</h3>
      <p>{local.local}</p>
      {erro && <div className="alerta-erro-claro" role="alert">{erro}</div>}
      {impacto && (
        <p>Isso apaga {plural(impacto.secoes, "seção", "seções")} e {plural(impacto.urnas, "urna", "urnas")}
          {impacto.ocorrencias > 0 && <> e {plural(impacto.ocorrencias, "ocorrência", "ocorrências")}</>}.
          {impacto.confirmadas > 0 && <b className="aviso-forte"> {plural(impacto.confirmadas, "urna já confirmada será apagada", "urnas já confirmadas serão apagadas")}.</b>}
        </p>
      )}
      <p className="ajuda-pequena">O sistema salva uma cópia de segurança do banco antes de excluir.</p>
      <Confirmacao rotulo="Excluir definitivamente" desabilitado={!impacto} onFechar={onFechar}
                   executar={async (texto) => onExcluido(await excluirLocal(token, local.local_id, texto))} />
    </div>
  );
}
