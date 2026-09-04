export default function JusticaEleitoralLogo({ size = 160 }) {
  return (
    <div className="logo-bloco" style={{ width: size }}>
      <svg
        viewBox="0 0 200 200"
        width={size}
        height={size}
        role="img"
        aria-label="Símbolo da Justiça Eleitoral"
      >
        {/* Quadrante amarelo (fundo) */}
        <rect x="100" y="0" width="100" height="100" fill="#F0B429" />
        {/* Quadrante verde (fundo) */}
        <rect x="100" y="100" width="100" height="100" fill="#2E4E3F" />
        {/* Globo azul sobrepondo os dois quadrantes */}
        <circle cx="95" cy="100" r="95" fill="#3E4C82" />
        {/* Estrelas do Cruzeiro do Sul, estilizadas */}
        <g fill="#FFFFFF">
          <circle cx="70" cy="55" r="2.6" />
          <circle cx="82" cy="75" r="2" />
          <circle cx="95" cy="95" r="3.2" />
          <circle cx="105" cy="118" r="2.2" />
          <circle cx="60" cy="90" r="1.6" />
          <circle cx="120" cy="70" r="1.6" />
          <circle cx="50" cy="120" r="1.4" />
          <circle cx="130" cy="105" r="1.4" />
          <circle cx="78" cy="130" r="1.4" />
        </g>
      </svg>
      <div className="logo-texto">
        <span>Justiça</span>
        <span>Eleitoral</span>
      </div>
    </div>
  );
}
