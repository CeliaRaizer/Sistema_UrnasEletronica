import { useState } from "react";
import JusticaEleitoralLogo from "./JusticaEleitoralLogo";
import AcompanhamentoView from "./AcompanhamentoView";
import ImportarView from "./ImportarView";
import CadastroUrnasView from "./CadastroUrnasView";
import LinkConfirmacaoView from "./LinkConfirmacaoView";
import RotasView from "./RotasView";
import LocaisView from "./LocaisView";
import "./painel.css";

const ABAS = [
  { id: "acompanhamento", rotulo: "Acompanhamento" },
  { id: "rotas", rotulo: "Rotas" },
  { id: "locais", rotulo: "Locais de votação" },
  { id: "cadastro", rotulo: "Cadastro de urnas" },
  { id: "importar", rotulo: "Importar planilhas" },
  { id: "link", rotulo: "Link de confirmação" },
];

export default function PainelPage({ usuario, token, onLogout }) {
  const [aba, setAba] = useState("acompanhamento");

  return (
    <div className="app">
      <aside className="menu">
        <div className="menu-marca">
          <JusticaEleitoralLogo size={44} />
          <span>Controle de Urnas</span>
        </div>
        <nav aria-label="Principal">
          {ABAS.map((a) => (
            <button
              key={a.id}
              className={`menu-item ${aba === a.id ? "ativo" : ""}`}
              aria-current={aba === a.id ? "page" : undefined}
              onClick={() => setAba(a.id)}
            >
              {a.rotulo}
            </button>
          ))}
        </nav>
        <div className="menu-usuario">
          <span>{usuario.username}</span>
          <button onClick={onLogout}>Sair</button>
        </div>
      </aside>

      <main className="conteudo">
        {aba === "acompanhamento" && <AcompanhamentoView token={token} onIrImportar={() => setAba("importar")} />}
        {aba === "rotas" && <RotasView token={token} onIrImportar={() => setAba("importar")} />}
        {aba === "locais" && <LocaisView token={token} onIrImportar={() => setAba("importar")} />}
        {aba === "cadastro" && <CadastroUrnasView token={token} onIrImportar={() => setAba("importar")} />}
        {aba === "link" && <LinkConfirmacaoView />}
        {aba === "importar" && <ImportarView token={token} onIrCadastro={() => setAba("cadastro")} />}
      </main>
    </div>
  );
}
