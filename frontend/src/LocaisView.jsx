import { useCallback, useEffect, useState } from "react";
import { getSecoes } from "./api";
import { FormLocal } from "./FormEdicao";
import { agrupar, Chips, contar, Filtros, FILTROS_VAZIOS, filtrarSecoes, Presidente, quando } from "./estrutura";

export default function LocaisView({ token, onIrImportar }) {
  const [secoes, setSecoes] = useState(null);
  const [erro, setErro] = useState("");
  const [filtros, setFiltros] = useState(FILTROS_VAZIOS);
  const [editando, setEditando] = useState(null); // id do local em edição

  const carregar = useCallback(() => getSecoes(token).then(setSecoes).catch((e) => setErro(e.message)), [token]);
  useEffect(() => { carregar(); }, [carregar]);

  if (secoes && secoes.length === 0) {
    return (
      <>
        <header className="cabecalho"><h1>Locais de votação</h1></header>
        <div className="vazio">
          <p>Ainda não há locais cadastrados. Importe a planilha de locais e rotas.</p>
          <button className="botao-pri" onClick={onIrImportar}>Importar planilhas</button>
        </div>
      </>
    );
  }

  const todas = secoes ?? [];
  const visiveis = filtrarSecoes(todas, filtros);
  const municipios = agrupar(visiveis, (s) => s.municipio_id);
  const nLocais = new Set(visiveis.map((s) => s.local_id)).size;

  return (
    <>
      <header className="cabecalho">
        <h1>Locais de votação</h1>
        <div className="atualizacao">
          <span>{nLocais} locais · {visiveis.length} seções</span>
          <button className="botao-sec" onClick={carregar}>Atualizar</button>
        </div>
      </header>
      {erro && <div className="alerta-erro-claro" role="alert">{erro}</div>}
      <Filtros secoes={todas} filtros={filtros} setFiltros={setFiltros} campos={["municipio", "rota", "area"]} />

      {secoes && municipios.length === 0 && <div className="vazio"><p>Nenhum local encontrado com esses filtros.</p></div>}

      {municipios.map((doMun) => {
        const locais = agrupar(doMun, (s) => s.local_id);
        const { total, comUrna } = contar(todas.filter((s) => s.municipio_id === doMun[0].municipio_id));
        return (
          <section className="municipio" key={doMun[0].municipio_id}>
            <h2>
              {doMun[0].municipio}
              <small>{locais.length} {locais.length === 1 ? "local" : "locais"} · {total} seções · {comUrna} com urna</small>
            </h2>
            <div className="locais">
              {locais.map((ss) => {
                const l = ss[0];
                const rotas = [...new Set(ss.map((s) => s.rota).filter(Boolean))].sort((a, b) => a - b);
                return (
                  <article className="local" key={l.local_id}>
                    <header>
                      <h3>{l.local}</h3>
                      <div className="selos">
                        {l.area === "interior" && <span className="selo selo-interior">Interior</span>}
                        {rotas.map((n) => <span key={n} className="selo selo-rota">Rota {n}</span>)}
                      </div>
                    </header>
                    {(l.endereco || l.bairro) && <p className="local-end">{[l.endereco, l.bairro].filter(Boolean).join(" · ")}</p>}
                    {editando === l.local_id ? (
                      <FormLocal token={token} dados={l} onCancelar={() => setEditando(null)}
                                 onSalvo={async () => { await carregar(); setEditando(null); }} />
                    ) : (
                      <>
                        <dl>
                          <div><dt>Presidente</dt><dd><Presidente s={l} /></dd></div>
                          {quando(l) && <div><dt>Previsto</dt><dd>{quando(l)}{l.hora_saida && <small>saída {l.hora_saida}</small>}</dd></div>}
                        </dl>
                        <button className="botao-link" onClick={() => setEditando(l.local_id)}>Editar presidente e horários</button>
                      </>
                    )}
                    <Chips secoes={ss} />
                  </article>
                );
              })}
            </div>
          </section>
        );
      })}
    </>
  );
}
