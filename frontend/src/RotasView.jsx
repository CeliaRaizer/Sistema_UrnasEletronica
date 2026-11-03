import { Fragment, useCallback, useEffect, useState } from "react";
import { getSecoes } from "./api";
import { FormLocal, FormRota } from "./FormEdicao";
import { agrupar, Chips, contar, Filtros, FILTROS_VAZIOS, filtrarSecoes, Presidente, quando } from "./estrutura";

export default function RotasView({ token, onIrImportar }) {
  const [secoes, setSecoes] = useState(null);
  const [erro, setErro] = useState("");
  const [filtros, setFiltros] = useState(FILTROS_VAZIOS);
  const [editando, setEditando] = useState(null); // "local-<id>" ou "rota-<n>"
  const salvo = async () => { await carregar(); setEditando(null); };

  const carregar = useCallback(() => getSecoes(token).then(setSecoes).catch((e) => setErro(e.message)), [token]);
  useEffect(() => { carregar(); }, [carregar]);

  if (secoes && secoes.length === 0) {
    return (
      <>
        <header className="cabecalho"><h1>Rotas</h1></header>
        <div className="vazio">
          <p>Ainda não há rotas. Importe a planilha de locais e rotas.</p>
          <button className="botao-pri" onClick={onIrImportar}>Importar planilhas</button>
        </div>
      </>
    );
  }

  const todas = secoes ?? [];
  const visiveis = filtrarSecoes(todas, filtros);
  const rotas = agrupar([...visiveis].sort((a, b) => (a.rota ?? 999) - (b.rota ?? 999)), (s) => s.rota);

  return (
    <>
      <header className="cabecalho">
        <h1>Rotas</h1>
        <div className="atualizacao">
          <span>{visiveis.length} de {todas.length} seções</span>
          <button className="botao-sec" onClick={carregar}>Atualizar</button>
        </div>
      </header>
      {erro && <div className="alerta-erro-claro" role="alert">{erro}</div>}
      <Filtros secoes={todas} filtros={filtros} setFiltros={setFiltros} campos={["municipio", "rota"]} />

      {secoes && rotas.length === 0 && <div className="vazio"><p>Nenhuma seção encontrada com esses filtros.</p></div>}

      {rotas.map((lista) => {
        const n = lista[0].rota;
        const daRota = todas.filter((s) => s.rota === n);
        const { total, comUrna } = contar(daRota);
        const locais = agrupar(lista, (s) => s.local_id);
        const nLocaisRota = new Set(daRota.map((s) => s.local_id)).size;
        const municipios = [...new Set(daRota.map((s) => s.municipio))].join(", ");
        const r = lista[0];
        return (
          <details className="rota" key={n ?? "sem"} open>
            <summary>
              <strong>{n ? `Rota ${n}` : "Sem rota"}</strong>
              <span className="rota-mun">{municipios}</span>
              <span className="rota-num">{nLocaisRota} {nLocaisRota === 1 ? "local" : "locais"} · {total} seções · <b>{comUrna}</b> com urna</span>
            </summary>
            {n && (editando === `rota-${n}` ? (
              <div className="rota-form"><FormRota token={token} dados={r} onSalvo={salvo} onCancelar={() => setEditando(null)} /></div>
            ) : (
              <p className="rota-resp">
                <span>Responsável:</span> {r.rota_responsavel || <em className="apagado">não informado</em>}
                {r.rota_placa && <> · Placa {r.rota_placa}</>}
                {r.rota_celular && <> · {r.rota_celular}</>}
                <button className="botao-link" onClick={() => setEditando(`rota-${n}`)}>Editar</button>
              </p>
            ))}
            <div className="tabela-rolagem">
              <table>
                <thead><tr><th>Local de votação</th><th>Presidente de prédio</th><th>Previsto</th><th>Seções</th><th></th></tr></thead>
                <tbody>
                  {locais.map((ss) => (
                    <Fragment key={ss[0].local_id}>
                      <tr>
                        <td>{ss[0].local}<small>{ss[0].municipio}</small></td>
                        <td><Presidente s={ss[0]} /></td>
                        <td>{quando(ss[0]) ?? "—"}{ss[0].hora_saida && <small>saída {ss[0].hora_saida}</small>}</td>
                        <td><Chips secoes={ss} /></td>
                        <td><button className="botao-link" onClick={() => setEditando(`local-${ss[0].local_id}`)}>Editar</button></td>
                      </tr>
                      {editando === `local-${ss[0].local_id}` && (
                        <tr className="linha-form"><td colSpan={5}>
                          <FormLocal token={token} dados={ss[0]} onSalvo={salvo} onCancelar={() => setEditando(null)} />
                        </td></tr>
                      )}
                    </Fragment>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
        );
      })}
    </>
  );
}
