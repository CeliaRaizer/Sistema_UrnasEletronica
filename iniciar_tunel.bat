@echo off
echo Gerando endereco https para o celular... (deixe esta janela aberta)
echo Procure na saida abaixo o link https://....trycloudflare.com
cloudflared tunnel --url http://localhost:5173
pause
