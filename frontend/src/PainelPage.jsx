export default function PainelPage({ usuario, onLogout }) {
  return (
    <div className="painel-tela">
      <div className="painel-caixa">
        <h1>Bem-vindo(a), {usuario.username}</h1>
        <p>
          Login realizado com sucesso. Este painel é um placeholder — aqui
          entrarão os cadastros de locais de votação, urnas, rotas e o
          acompanhamento de entregas.
        </p>
        <button onClick={onLogout}>Sair</button>
      </div>
    </div>
  );
}
