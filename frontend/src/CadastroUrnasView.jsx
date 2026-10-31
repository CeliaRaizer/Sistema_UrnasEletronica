import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { associarUrna, getSecoes } from "./api";
import QrScanner from "./QrScanner";

export default function CadastroUrnasView({ token, onIrImportar }) {
  const [secoes, setSecoes] = useState(null);
  const [municipioId, setMunicipioId] = useState("");
  const [selecionada, setSelecionada] = useState(null); // id da seção
  const [patrimonio, setPatrimonio] = useState("");
  const [camera, setCamera] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [msg, setMsg] = useState(null); // { tipo: "ok" | "erro" | "conflito", texto }
  const inputRef = useRef(null);

  const carregar = useCallback(
    () => getSecoes(token).then(setSecoes).catch((e) => setMsg({ tipo: "erro", texto: e.message })),
    [token]
  );
  useEffect(() => { carregar(); }, [carregar]);

  const municipios = useMemo(() => {
    const m = new Map();
    (secoes || []).forEach((s) => m.set(s.municipio_id, s.municipio));
    return [...m].map(([id, nome]) => ({ id, nome }));
  }, [secoes]);

  useEffect(() => {
    if (!municipioId && municipios.length) setMunicipioId(String(municipios[0].id));
  }, [municipios, municipioId]);

  const doMunicipio = (secoes || []).filter((s) => String(s.municipio_id) === municipioId);
  const feitas = doMunicipio.filter((s) => s.patrimonio).length;
  const proxima = doMunicipio.find((s) => !s.patrimonio);
  const atual = doMunicipio.find((s) => s.id === selecionada) || proxima;

  useEffect(() => { setPatrimonio(""); inputRef.current?.focus(); }, [atual?.id]);

  async function salvar(substituir = false, valor = patrimonio) {
    if (!atual || !valor.trim()) return;
    setSalvando(true);
    setMsg(null);
    try {
      await associarUrna(token, { patrimonio: valor, zona: atual.zona, secao: atual.numero, substituir });
      const texto = `Urna ${valor.trim().toUpperCase()} vinculada à seção ${atual.numero}.`;
      await carregar(); // primeiro atualiza a lista, depois avisa e passa para a próxima seção
      setSelecionada(null);
      setPatrimonio("");
      setMsg({ tipo: "ok", texto });
    } catch (e) {
      const conflito = /já (está|tem)/.test(e.message);
      setMsg({ tipo: conflito ? "conflito" : "erro", texto: e.message });
    } finally {
      setSalvando(false);
    }
  }

  const aoLerQr = useCallback((texto) => {
    setCamera(false);
    setPatrimonio(texto);
    inputRef.current?.focus();
  }, []);

  if (secoes && secoes.length === 0) {
    return (
      <>
        <header className="cabecalho"><h1>Cadastro de urnas</h1></header>
        <div className="vazio">
          <p>Ainda não há seções cadastradas. Importe a planilha de locais e rotas primeiro.</p>
          <button className="botao-pri" onClick={onIrImportar}>Importar planilha</button>
        </div>
      </>
    );
  }

  return (
    <>
      <header className="cabecalho"><h1>Cadastro de urnas</h1></header>
      <p className="ajuda">
        Na carga da urna, leia o QR code (ou digite o patrimônio) para vincular a urna à seção.
        A rota da seção aparece automaticamente. Depois de salvar, o sistema passa para a próxima seção sem urna.
      </p>

      <div className="filtros">
        <label>Município
          <select value={municipioId} onChange={(e) => { setMunicipioId(e.target.value); setSelecionada(null); setMsg(null); }}>
            {municipios.map((m) => <option key={m.id} value={m.id}>{m.nome}</option>)}
          </select>
        </label>
        <div className="progresso" aria-live="polite">
          <strong>{feitas} de {doMunicipio.length}</strong> seções com urna
          <div className="barra"><span className="b-entregue" style={{ width: `${doMunicipio.length ? (feitas / doMunicipio.length) * 100 : 0}%` }} /></div>
        </div>
      </div>

      {msg && (
        <div className={msg.tipo === "ok" ? "alerta-ok" : "alerta-erro-claro"} role={msg.tipo === "ok" ? "status" : "alert"}>
          {msg.texto}
          {msg.tipo === "conflito" && (
            <> <button className="botao-sec" onClick={() => salvar(true)}>Trocar mesmo assim</button></>
          )}
        </div>
      )}

      {atual ? (
        <section className="carga">
          <div className="carga-seção">
            <span>Seção</span>
            <strong>{atual.numero}</strong>
            <small>zona {atual.zona}</small>
          </div>
          <dl>
            <div><dt>Local de votação</dt><dd>{atual.local}</dd></div>
            <div><dt>Rota</dt><dd>{atual.rota ? `Rota ${atual.rota}` : "Sem rota"}</dd></div>
            {atual.patrimonio && <div><dt>Urna atual</dt><dd className="mono">{atual.patrimonio}</dd></div>}
          </dl>
          <form onSubmit={(e) => { e.preventDefault(); salvar(); }} className="carga-form">
            <label>Patrimônio da urna
              <input ref={inputRef} value={patrimonio} onChange={(e) => setPatrimonio(e.target.value)}
                     placeholder="Leia o QR ou digite" autoComplete="off" />
            </label>
            <div className="carga-acoes">
              <button type="button" className="botao-sec" onClick={() => setCamera((c) => !c)}>
                {camera ? "Fechar câmera" : "Ler QR code"}
              </button>
              <button className="botao-pri" disabled={!patrimonio.trim() || salvando}>
                {salvando ? "Salvando…" : "Salvar e ir para a próxima"}
              </button>
            </div>
          </form>
          {camera && <QrScanner onLer={aoLerQr} onFechar={() => setCamera(false)} />}
        </section>
      ) : (
        secoes && doMunicipio.length > 0 && (
          <div className="alerta-ok">Todas as seções deste município já têm urna. Escolha outro município.</div>
        )
      )}

      <div className="tabela-rolagem lista-secoes">
        <table>
          <thead><tr><th>Seção</th><th>Local de votação</th><th>Rota</th><th>Urna</th><th></th></tr></thead>
          <tbody>
            {doMunicipio.map((s) => (
              <tr key={s.id} className={s.id === atual?.id ? "linha-atual" : ""}>
                <td className="mono">{s.numero}</td>
                <td>{s.local}</td>
                <td>{s.rota ?? "—"}</td>
                <td>{s.patrimonio ? <span className="mono">{s.patrimonio}</span> : <span className="selo selo-em_transito">Sem urna</span>}</td>
                <td><button className="botao-link" onClick={() => { setSelecionada(s.id); setMsg(null); }}>
                  {s.patrimonio ? "Trocar urna" : "Cadastrar"}
                </button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
