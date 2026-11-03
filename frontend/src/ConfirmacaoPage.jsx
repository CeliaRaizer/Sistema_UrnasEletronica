import { useCallback, useEffect, useRef, useState } from "react";
import { confirmarEntrega, consultarUrna, getLocais, registrarOcorrencia } from "./api";
import JusticaEleitoralLogo from "./JusticaEleitoralLogo";
import QrScanner from "./QrScanner";
import "./confirmacao.css";

const lembrar = (chave, valor) => { try { localStorage.setItem(chave, valor); } catch { /* sem armazenamento */ } };
const recordar = (chave) => { try { return localStorage.getItem(chave) || ""; } catch { return ""; } };

const PROBLEMAS = [
  ["avaria", "Urna com avaria"],
  ["atraso", "Atraso na entrega"],
  ["urna_incorreta", "Urna incorreta"],
  ["outro", "Outro problema"],
];

export default function ConfirmacaoPage() {
  const [municipios, setMunicipios] = useState([]);
  const [municipioId, setMunicipioId] = useState(recordar("conf_municipio"));
  const [localId, setLocalId] = useState(recordar("conf_local"));
  const [patrimonio, setPatrimonio] = useState("");
  const [urna, setUrna] = useState(null);
  const [nome, setNome] = useState(recordar("conf_nome"));
  const [camera, setCamera] = useState(false);
  const [ocupado, setOcupado] = useState(false);
  const [aviso, setAviso] = useState(null); // { tipo: "ok" | "erro" | "alerta", texto }
  const [feitas, setFeitas] = useState([]);
  const [problema, setProblema] = useState(null); // { tipo, descricao } quando aberto
  const campoRef = useRef(null);

  useEffect(() => {
    getLocais().then(setMunicipios).catch((e) => setAviso({ tipo: "erro", texto: e.message }));
  }, []);

  const locais = municipios.find((m) => String(m.id) === municipioId)?.locais || [];
  const local = locais.find((l) => String(l.id) === localId);

  const escolherMunicipio = (id) => { setMunicipioId(id); setLocalId(""); lembrar("conf_municipio", id); lembrar("conf_local", ""); };
  const escolherLocal = (id) => { setLocalId(id); lembrar("conf_local", id); };
  const trocarLocal = () => { escolherLocal(""); setUrna(null); setAviso(null); };

  const buscar = useCallback(async (valor) => {
    const p = (valor ?? "").trim();
    if (!p) return;
    setOcupado(true); setAviso(null); setUrna(null); setProblema(null);
    try {
      setUrna(await consultarUrna(p));
    } catch (e) {
      setAviso({ tipo: "erro", texto: e.message });
    } finally {
      setOcupado(false);
    }
  }, []);

  const aoLerQr = useCallback((texto) => {
    setCamera(false);
    setPatrimonio(texto);
    buscar(texto);
  }, [buscar]);

  function proxima() {
    setUrna(null); setPatrimonio(""); setProblema(null);
    setTimeout(() => campoRef.current?.focus(), 50);
  }

  async function confirmar() {
    if (!nome.trim()) { setAviso({ tipo: "erro", texto: "Informe o nome de quem está recebendo." }); return; }
    setOcupado(true); setAviso(null);
    try {
      const r = await confirmarEntrega({
        patrimonio: urna.patrimonio, nome: nome.trim(), local_id: Number(localId),
        confirmado_em: new Date().toISOString(),
      });
      lembrar("conf_nome", nome.trim());
      if (r.resultado === "divergente") {
        setAviso({ tipo: "alerta", texto: "O cartório foi avisado de que esta urna não é deste local. Não use esta urna." });
      } else {
        setFeitas((f) => [{ patrimonio: r.patrimonio, secao: r.secao }, ...f]);
        setAviso({ tipo: "ok", texto: r.resultado === "ja_confirmada"
          ? `A urna ${r.patrimonio} já estava confirmada.`
          : `Recebimento confirmado: urna ${r.patrimonio}, seção ${r.secao ?? "—"}.` });
      }
      proxima();
    } catch (e) {
      setAviso({ tipo: "erro", texto: e.message });
    } finally {
      setOcupado(false);
    }
  }

  async function enviarProblema(e) {
    e.preventDefault();
    setOcupado(true);
    try {
      await registrarOcorrencia({ patrimonio: urna.patrimonio, tipo: problema.tipo, descricao: problema.descricao, nome });
      setProblema(null);
      setAviso({ tipo: "ok", texto: "Problema informado ao cartório." });
    } catch (err) {
      setAviso({ tipo: "erro", texto: err.message });
    } finally {
      setOcupado(false);
    }
  }

  const divergente = urna?.local && String(urna.local.id) !== localId;
  const jaConfirmada = urna?.status === "entregue";

  return (
    <div className="conf">
      <header className="conf-topo">
        <JusticaEleitoralLogo size={40} />
        <div><strong>Recebimento de urnas</strong><span>Justiça Eleitoral</span></div>
      </header>

      <main className="conf-corpo">
        {aviso && <div className={`conf-aviso conf-${aviso.tipo}`} role={aviso.tipo === "ok" ? "status" : "alert"}>{aviso.texto}</div>}

        {!local ? (
          <section className="conf-cartao">
            <h1>Onde você está?</h1>
            <label>Município
              <select value={municipioId} onChange={(e) => escolherMunicipio(e.target.value)}>
                <option value="">Escolha o município</option>
                {municipios.map((m) => <option key={m.id} value={m.id}>{m.nome}</option>)}
              </select>
            </label>
            <label>Local de votação
              <select value={localId} onChange={(e) => escolherLocal(e.target.value)} disabled={!municipioId}>
                <option value="">Escolha o local</option>
                {locais.map((l) => <option key={l.id} value={l.id}>{l.nome}</option>)}
              </select>
            </label>
          </section>
        ) : (
          <>
            <section className="conf-local">
              <div><span>Local de votação</span><strong>{local.nome}</strong></div>
              <button className="conf-link" onClick={trocarLocal}>Trocar</button>
            </section>

            {!urna && (
              <section className="conf-cartao">
                <h1>Identifique a urna</h1>
                <form onSubmit={(e) => { e.preventDefault(); buscar(patrimonio); }}>
                  <label>Número do patrimônio
                    <input ref={campoRef} value={patrimonio} onChange={(e) => setPatrimonio(e.target.value)}
                           inputMode="text" autoComplete="off" placeholder="Digite ou leia o QR code" />
                  </label>
                  <div className="conf-acoes">
                    <button type="button" className="conf-sec" onClick={() => setCamera((c) => !c)}>
                      {camera ? "Fechar câmera" : "Ler QR code da urna"}
                    </button>
                    <button className="conf-pri" disabled={!patrimonio.trim() || ocupado}>
                      {ocupado ? "Buscando…" : "Buscar urna"}
                    </button>
                  </div>
                </form>
                {camera && <QrScanner onLer={aoLerQr} onFechar={() => setCamera(false)} />}
              </section>
            )}

            {urna && (
              <section className="conf-cartao">
                <div className="conf-urna">
                  <div className="conf-secao"><span>Seção</span><strong>{urna.secao ?? "—"}</strong></div>
                  <dl>
                    <div><dt>Urna</dt><dd>{urna.patrimonio}</dd></div>
                    <div><dt>Local da urna</dt><dd>{urna.local ? urna.local.nome : "Urna de contingência"}</dd></div>
                  </dl>
                </div>

                {divergente ? (
                  <>
                    <div className="conf-aviso conf-erro" role="alert">
                      <strong>Esta urna não é deste local.</strong> Ela pertence a {urna.local.nome}. Não confirme o recebimento.
                    </div>
                    <div className="conf-acoes">
                      <button className="conf-sec" onClick={proxima}>Voltar</button>
                      <button className="conf-pri conf-perigo" onClick={confirmar} disabled={ocupado || !nome.trim()}>Avisar o cartório</button>
                    </div>
                    <label>Seu nome
                      <input value={nome} onChange={(e) => setNome(e.target.value)} autoComplete="name" />
                    </label>
                  </>
                ) : jaConfirmada ? (
                  <>
                    <div className="conf-aviso conf-alerta">Esta urna já foi confirmada{urna.recebido_por && ` por ${urna.recebido_por}`}.</div>
                    <button className="conf-sec" onClick={proxima}>Ler outra urna</button>
                  </>
                ) : (
                  <>
                    <label>Nome de quem está recebendo
                      <input value={nome} onChange={(e) => setNome(e.target.value)} autoComplete="name" placeholder="Nome completo" />
                    </label>
                    <div className="conf-acoes">
                      <button className="conf-sec" onClick={proxima}>Cancelar</button>
                      <button className="conf-pri" onClick={confirmar} disabled={ocupado}>
                        {ocupado ? "Enviando…" : "Confirmar recebimento"}
                      </button>
                    </div>
                  </>
                )}

                {!problema ? (
                  <button className="conf-link" onClick={() => setProblema({ tipo: "avaria", descricao: "" })}>Informar um problema com esta urna</button>
                ) : (
                  <form className="conf-problema" onSubmit={enviarProblema}>
                    <label>Tipo de problema
                      <select value={problema.tipo} onChange={(e) => setProblema({ ...problema, tipo: e.target.value })}>
                        {PROBLEMAS.map(([v, n]) => <option key={v} value={v}>{n}</option>)}
                      </select>
                    </label>
                    <label>Descreva (opcional)
                      <textarea rows={3} value={problema.descricao} onChange={(e) => setProblema({ ...problema, descricao: e.target.value })} />
                    </label>
                    <div className="conf-acoes">
                      <button type="button" className="conf-sec" onClick={() => setProblema(null)}>Cancelar</button>
                      <button className="conf-pri" disabled={ocupado}>Enviar ao cartório</button>
                    </div>
                  </form>
                )}
              </section>
            )}

            {feitas.length > 0 && (
              <section className="conf-feitas">
                <h2>Confirmadas neste aparelho ({feitas.length})</h2>
                <ul>{feitas.map((f) => <li key={f.patrimonio}>Urna {f.patrimonio} · seção {f.secao ?? "—"}</li>)}</ul>
              </section>
            )}
          </>
        )}
      </main>
    </div>
  );
}
