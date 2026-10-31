import { useEffect, useRef, useState } from "react";
import jsQR from "jsqr";

/** Abre a câmera e chama onLer(texto) assim que reconhece um QR code. */
export default function QrScanner({ onLer, onFechar }) {
  const videoRef = useRef(null);
  const [erro, setErro] = useState("");

  useEffect(() => {
    let parar = false;
    let stream;
    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d", { willReadFrequently: true });

    function varrer() {
      const v = videoRef.current;
      if (parar || !v) return;
      if (v.readyState === v.HAVE_ENOUGH_DATA) {
        canvas.width = v.videoWidth;
        canvas.height = v.videoHeight;
        ctx.drawImage(v, 0, 0);
        const img = ctx.getImageData(0, 0, canvas.width, canvas.height);
        const achou = jsQR(img.data, img.width, img.height);
        if (achou && achou.data) {
          onLer(achou.data.trim());
          return;
        }
      }
      requestAnimationFrame(varrer);
    }

    if (!navigator.mediaDevices?.getUserMedia) {
      setErro("A câmera só funciona em endereço seguro (https ou localhost). Digite o patrimônio.");
      return;
    }
    navigator.mediaDevices
      .getUserMedia({ video: { facingMode: "environment" } })
      .then((s) => {
        stream = s;
        if (parar) return s.getTracks().forEach((t) => t.stop());
        videoRef.current.srcObject = s;
        videoRef.current.play();
        requestAnimationFrame(varrer);
      })
      .catch(() => setErro("Não foi possível abrir a câmera. Permita o acesso ou digite o patrimônio."));

    return () => {
      parar = true;
      stream?.getTracks().forEach((t) => t.stop());
    };
  }, [onLer]);

  return (
    <div className="scanner">
      {erro ? <p className="scanner-erro">{erro}</p> : <video ref={videoRef} muted playsInline />}
      <button type="button" className="botao-sec" onClick={onFechar}>Fechar câmera</button>
    </div>
  );
}
