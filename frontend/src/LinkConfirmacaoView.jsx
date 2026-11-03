import { useEffect, useState } from "react";
import QRCode from "qrcode";

export default function LinkConfirmacaoView() {
  const link = `${window.location.origin}/confirmar`;
  const [imagem, setImagem] = useState("");
  const [copiado, setCopiado] = useState(false);

  useEffect(() => { QRCode.toDataURL(link, { width: 360, margin: 2 }).then(setImagem); }, [link]);

  async function copiar() {
    try { await navigator.clipboard.writeText(link); setCopiado(true); setTimeout(() => setCopiado(false), 2000); } catch { /* o link está visível para copiar à mão */ }
  }

  return (
    <>
      <header className="cabecalho"><h1>Link de confirmação</h1></header>
      <p className="ajuda">
        Este QR code (ou link) abre a tela em que o presidente de prédio confirma o recebimento das urnas.
        É o mesmo para todos os locais e não pede login.
      </p>
      <section className="link-conf">
        {imagem && <img src={imagem} alt="QR code do link de confirmação" width="220" height="220" />}
        <div>
          <p className="mono link-texto">{link}</p>
          <div className="carga-acoes">
            <button className="botao-pri" onClick={copiar}>{copiado ? "Link copiado" : "Copiar link"}</button>
            <a className="botao-sec" href="/confirmar" target="_blank" rel="noreferrer">Abrir a tela</a>
            <button className="botao-sec" onClick={() => window.print()}>Imprimir</button>
          </div>
          <p className="ajuda">O endereço depende de onde o sistema está rodando. Quando ele for publicado, gere o QR de novo com o endereço definitivo.</p>
        </div>
      </section>
    </>
  );
}
