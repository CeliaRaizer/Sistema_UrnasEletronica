import { useState } from "react";
import { editarLocal, editarRota } from "./api";

/** Formulário em linha para editar um local (presidente, telefone, data e horários). */
export function FormLocal({ token, dados, onSalvo, onCancelar }) {
  const [v, setV] = useState({
    presidente: dados.presidente || "",
    presidente_telefone: dados.presidente_telefone || "",
    data_entrega: dados.data_entrega || "",
    hora_saida: dados.hora_saida || "",
    hora_prevista: dados.hora_prevista || "",
  });
  const [erro, setErro] = useState("");
  const [salvando, setSalvando] = useState(false);
  const muda = (c) => (e) => setV({ ...v, [c]: e.target.value });

  async function salvar(e) {
    e.preventDefault();
    setSalvando(true); setErro("");
    try {
      await editarLocal(token, dados.local_id, v);
      await onSalvo();
    } catch (err) {
      setErro(err.message);
      setSalvando(false);
    }
  }

  return (
    <form className="form-edicao" onSubmit={salvar}>
      <label className="larga">Presidente de prédio
        <input value={v.presidente} onChange={muda("presidente")} maxLength={120} autoComplete="off" />
      </label>
      <label>Telefone
        <input value={v.presidente_telefone} onChange={muda("presidente_telefone")} maxLength={40} inputMode="tel" />
      </label>
      <label>Data de entrega
        <input type="date" value={v.data_entrega} onChange={muda("data_entrega")} />
      </label>
      <label>Horário de saída
        <input type="time" value={v.hora_saida} onChange={muda("hora_saida")} />
      </label>
      <label>Previsto de entrega
        <input type="time" value={v.hora_prevista} onChange={muda("hora_prevista")} />
      </label>
      {erro && <div className="alerta-erro-claro larga" role="alert">{erro}</div>}
      <div className="form-acoes larga">
        <button type="button" className="botao-sec" onClick={onCancelar} disabled={salvando}>Cancelar</button>
        <button className="botao-pri" disabled={salvando}>{salvando ? "Salvando…" : "Salvar"}</button>
      </div>
    </form>
  );
}

/** Formulário em linha para editar o responsável pela distribuição de uma rota. */
export function FormRota({ token, dados, onSalvo, onCancelar }) {
  const [v, setV] = useState({
    responsavel: dados.rota_responsavel || "",
    placa: dados.rota_placa || "",
    celular: dados.rota_celular || "",
  });
  const [erro, setErro] = useState("");
  const [salvando, setSalvando] = useState(false);
  const muda = (c) => (e) => setV({ ...v, [c]: e.target.value });

  async function salvar(e) {
    e.preventDefault();
    setSalvando(true); setErro("");
    try {
      await editarRota(token, dados.rota, v);
      await onSalvo();
    } catch (err) {
      setErro(err.message);
      setSalvando(false);
    }
  }

  return (
    <form className="form-edicao" onSubmit={salvar}>
      <label className="larga">Responsável pela distribuição
        <input value={v.responsavel} onChange={muda("responsavel")} maxLength={200} placeholder="Ex.: Celia / Daniel José Cantelli" />
      </label>
      <label>Placa
        <input value={v.placa} onChange={muda("placa")} maxLength={15} />
      </label>
      <label>Celular
        <input value={v.celular} onChange={muda("celular")} maxLength={60} inputMode="tel" />
      </label>
      {erro && <div className="alerta-erro-claro larga" role="alert">{erro}</div>}
      <div className="form-acoes larga">
        <button type="button" className="botao-sec" onClick={onCancelar} disabled={salvando}>Cancelar</button>
        <button className="botao-pri" disabled={salvando}>{salvando ? "Salvando…" : "Salvar"}</button>
      </div>
    </form>
  );
}
