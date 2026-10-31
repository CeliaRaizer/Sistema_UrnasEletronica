import { useCallback, useEffect, useState } from "react";
import { getLocais, getPainel } from "./api";

const STATUS = {
  entregue: "Entregue",
  em_transito: "Em trânsito",
  pendencia: "Pendência",
};

const formatarData = (iso) =>
  iso
    ? new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" })
    : "—";

export default function AcompanhamentoView({ token, onIrImportar }) {
  const [municipios, setMunicipios] = useState([]);
  const [filtros, setFiltros] = useState({ municipio: "", local: "", rota: "", status: "" });
  const [dados, setDados] = useState(null);
  const [erro, setErro] = useState("");
  const [atualizadoEm, setAtualizadoEm] = useState(null);

  useEffect(() => {
    getLocais().then(setMunicipios).catch(() => {});
  }, []);

  const carregar = useCallback(() => {
    getPainel(token, filtros)
      .then((d) => {
        setDados(d);
        setErro("");
        setAtualizadoEm(new Date());
      })
      .catch((e) => setErro(e.message));
  }, [token, filtros]);

  // Carrega ao abrir/filtrar e atualiza sozinho a cada 15 s (acompanhamento em tempo real)
  useEffect(() => {
    carregar();
    const t = setInterval(carregar, 15000);
    return () => clearInterval(t);
  }, [carregar]);

  const locais = municipios.find((m) => String(m.id) === filtros.municipio)?.locais || [];
  const mudar = (campo) => (e) =>
    setFiltros((f) => ({
      ...f,
      [campo]: e.target.value,
      ...(campo === "municipio" ? { local: "" } : {}),
    }));

  const r = dados?.resumo;
  const pct = (n) => (r && r.total ? (n / r.total) * 100 : 0);
  const semFiltro = !filtros.municipio && !filtros.local && !filtros.rota && !filtros.status;

  return (
    <>
      <header className="cabecalho">
        <h1>Acompanhamento das entregas</h1>
        <div className="atualizacao">
          {atualizadoEm && <span>Atualizado às {atualizadoEm.toLocaleTimeString("pt-BR")}</span>}
          <button className="botao-sec" onClick={carregar}>Atualizar agora</button>
        </div>
      </header>

      {erro && <div className="alerta-erro-claro" role="alert">{erro}</div>}

      {r && (
        <section className="resumo" aria-label="Resumo das entregas">
          <div className="resumo-numeros">
            <div><strong>{r.total}</strong> urnas</div>
            <div className="n-entregue"><strong>{r.entregue}</strong> entregues</div>
            <div className="n-transito"><strong>{r.em_transito}</strong> em trânsito</div>
            <div className="n-pendencia"><strong>{r.pendencia}</strong> com pendência</div>
          </div>
          <div className="barra" role="img"
               aria-label={`${r.entregue} entregues, ${r.em_transito} em trânsito, ${r.pendencia} com pendência`}>
            <span className="b-entregue" style={{ width: `${pct(r.entregue)}%` }} />
            <span className="b-transito" style={{ width: `${pct(r.em_transito)}%` }} />
            <span className="b-pendencia" style={{ width: `${pct(r.pendencia)}%` }} />
          </div>
        </section>
      )}

      <div className="filtros">
        <label>Município
          <select value={filtros.municipio} onChange={mudar("municipio")}>
            <option value="">Todos</option>
            {municipios.map((m) => <option key={m.id} value={m.id}>{m.nome}</option>)}
          </select>
        </label>
        <label>Local de votação
          <select value={filtros.local} onChange={mudar("local")} disabled={!filtros.municipio}>
            <option value="">Todos</option>
            {locais.map((l) => <option key={l.id} value={l.id}>{l.nome}</option>)}
          </select>
        </label>
        <label>Rota
          <select value={filtros.rota} onChange={mudar("rota")}>
            <option value="">Todas</option>
            {(dados?.rotas || []).map((n) => <option key={n} value={n}>Rota {n}</option>)}
          </select>
        </label>
        <label>Situação
          <select value={filtros.status} onChange={mudar("status")}>
            <option value="">Todas</option>
            {Object.entries(STATUS).map(([v, n]) => <option key={v} value={v}>{n}</option>)}
          </select>
        </label>
      </div>

      {dados && dados.entregas.length === 0 ? (
        <div className="vazio">
          {semFiltro ? (
            <>
              <p>Nenhuma urna cadastrada ainda.</p>
              <button className="botao-pri" onClick={onIrImportar}>Importar planilha de locais e rotas</button>
            </>
          ) : (
            <p>Nenhuma urna encontrada com esses filtros.</p>
          )}
        </div>
      ) : (
        dados && (
          <div className="tabela-rolagem">
            <table>
              <thead>
                <tr>
                  <th>Patrimônio</th><th>Local de votação</th><th>Seção</th><th>Rota</th>
                  <th>Distribuição</th><th>Recebimento</th><th>Situação</th>
                </tr>
              </thead>
              <tbody>
                {dados.entregas.map((e) => (
                  <tr key={e.patrimonio}>
                    <td className="mono">{e.patrimonio}</td>
                    <td>
                      {e.local ? e.local.nome : <em>Contingência</em>}
                      <small>{e.municipio}</small>
                    </td>
                    <td>{e.secao ? `${e.secao} (zona ${e.zona})` : "—"}</td>
                    <td>{e.rota ?? "—"}</td>
                    <td>{e.responsavel_distribuicao || "—"}</td>
                    <td>
                      {e.recebido_por || "—"}
                      {e.confirmado_em && <small>{formatarData(e.confirmado_em)}</small>}
                    </td>
                    <td>
                      <span className={`selo selo-${e.status}`}>{STATUS[e.status] || "—"}</span>
                      {e.ocorrencias > 0 && <small>{e.ocorrencias} ocorrência(s)</small>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      )}
    </>
  );
}
