// Peças compartilhadas pelas telas de Rotas e de Locais de votação.

export const semAcento = (t) =>
  String(t ?? "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();

/** Aplica os filtros às seções (município, rota, área, situação da urna e busca livre). */
export function filtrarSecoes(secoes, f) {
  const termo = semAcento(f.busca).trim();
  return secoes.filter((s) => {
    if (f.municipio && String(s.municipio_id) !== f.municipio) return false;
    if (f.rota && String(s.rota) !== f.rota) return false;
    if (f.area && s.area !== f.area) return false;
    if (f.urna === "sem" && s.patrimonio) return false;
    if (f.urna === "com" && !s.patrimonio) return false;
    if (termo) {
      const texto = semAcento(`${s.local} ${s.presidente} ${s.numero} ${s.patrimonio ?? ""} ${s.municipio} ${s.endereco}`);
      if (!termo.split(/\s+/).every((p) => texto.includes(p))) return false;
    }
    return true;
  });
}

export function agrupar(lista, chave) {
  const mapa = new Map();
  lista.forEach((x) => {
    const k = chave(x);
    if (!mapa.has(k)) mapa.set(k, []);
    mapa.get(k).push(x);
  });
  return [...mapa.values()];
}

export const contar = (secoes) => ({
  total: secoes.length,
  comUrna: secoes.filter((s) => s.patrimonio).length,
});

export const quando = (s) =>
  s.hora_prevista
    ? `${s.data_entrega ? s.data_entrega.slice(8, 10) + "/" + s.data_entrega.slice(5, 7) + " " : ""}${s.hora_prevista}`
    : null;

export function Chips({ secoes }) {
  return (
    <ul className="chips">
      {secoes.map((s) => (
        <li key={s.id} className={`chip ${s.patrimonio ? "chip-ok" : "chip-vazio"}`}>
          <strong>{s.numero}</strong>
          <small>{s.patrimonio ? `urna ${s.patrimonio}` : "sem urna"}</small>
        </li>
      ))}
    </ul>
  );
}

export function Presidente({ s }) {
  return s.presidente ? (
    <>
      {s.presidente}
      {s.presidente_telefone && <small>{s.presidente_telefone}</small>}
    </>
  ) : (
    <span className="apagado">não informado</span>
  );
}

/** Barra de filtros; `campos` diz quais mostrar. */
export function Filtros({ secoes, filtros, setFiltros, campos }) {
  const unicos = (chave, rotulo) =>
    [...new Map(secoes.filter((s) => s[chave] != null).map((s) => [String(s[chave]), s[rotulo ?? chave]])).entries()];
  const rotas = unicos("rota").sort((a, b) => a[0] - b[0]);
  const municipios = unicos("municipio_id", "municipio");
  const muda = (c) => (e) => setFiltros({ ...filtros, [c]: e.target.value });
  const limpo = Object.values(filtros).every((v) => !v);
  return (
    <div className="filtros">
      <label>Buscar
        <input type="search" value={filtros.busca} onChange={muda("busca")} placeholder="Local, presidente, seção ou urna" />
      </label>
      {campos.includes("municipio") && (
        <label>Município
          <select value={filtros.municipio} onChange={muda("municipio")}>
            <option value="">Todos</option>
            {municipios.map(([id, nome]) => <option key={id} value={id}>{nome}</option>)}
          </select>
        </label>
      )}
      {campos.includes("rota") && (
        <label>Rota
          <select value={filtros.rota} onChange={muda("rota")}>
            <option value="">Todas</option>
            {rotas.map(([n]) => <option key={n} value={n}>Rota {n}</option>)}
          </select>
        </label>
      )}
      {campos.includes("area") && (
        <label>Área
          <select value={filtros.area} onChange={muda("area")}>
            <option value="">Todas</option>
            <option value="urbano">Urbana</option>
            <option value="interior">Interior</option>
          </select>
        </label>
      )}
      <label>Urna
        <select value={filtros.urna} onChange={muda("urna")}>
          <option value="">Todas as seções</option>
          <option value="sem">Sem urna vinculada</option>
          <option value="com">Com urna vinculada</option>
        </select>
      </label>
      {!limpo && (
        <button className="botao-sec filtros-limpar" onClick={() => setFiltros({ busca: "", municipio: "", rota: "", area: "", urna: "" })}>
          Limpar filtros
        </button>
      )}
    </div>
  );
}

export const FILTROS_VAZIOS = { busca: "", municipio: "", rota: "", area: "", urna: "" };
