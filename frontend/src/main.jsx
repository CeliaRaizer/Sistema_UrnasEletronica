import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import ConfirmacaoPage from './ConfirmacaoPage.jsx'
import './index.css'

// /confirmar é a tela pública do campo (sem login); o resto é o sistema do cartório.
const Raiz = window.location.pathname.startsWith('/confirmar') ? ConfirmacaoPage : App

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <Raiz />
  </React.StrictMode>,
)
