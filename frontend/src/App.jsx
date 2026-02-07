import { useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import './App.css'

function App() {

  const [question, setQuestion] = useState("")
  const [response, setResponse] = useState("")
  const [conversationId, setConversationId] = useState(null)

  async function runConversation() {
    setResponse('Enviando...')
    try {
      const res = await fetch('/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: question || undefined }),
      })
      const data = await res.json()
      if (!data.ok) throw new Error(data.error || 'Erro desconhecido')
      setResponse(data.final_message)
      setConversationId(data.conversation_id)
    } catch (err) {
      setResponse('Erro: ' + err.message)
      setConversationId(null)
    }
  }

  return (
    <>
      <div>
        <a href="https://vite.dev" target="_blank">
          <img src={viteLogo} className="logo" alt="Vite logo" />
        </a>
        <a href="https://react.dev" target="_blank">
          <img src={reactLogo} className="logo react" alt="React logo" />
        </a>
      </div>

      <h1>Lingora — Frontend</h1>

      <div style={{ marginBottom: 16 }}>
        <input
          style={{ width: '60%', padding: '8px' }}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Pergunta (opcional) — ex: How many r's are in the word 'strawberry'?"
        />
        <button style={{ marginLeft: 8, padding: '8px 12px' }} onClick={runConversation}>
          Enviar
        </button>
      </div>

      <div className="card">
        <h2>Resposta</h2>
        <pre>{response}</pre>
        {conversationId && <div>ID da conversa: {conversationId}</div>}
      </div>

      <p className="read-the-docs">Click on the Vite and React logos to learn more</p>
    </>
  )
}

export default App
