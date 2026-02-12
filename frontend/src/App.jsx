import { useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import './App.css'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeSanitize from 'rehype-sanitize'
import MessageInput from './components/MessageInput' 

function App() {

  const [question, setQuestion] = useState("")
  const [messages, setMessages] = useState([])
  const [conversationId, setConversationId] = useState(null)

  async function runConversation() {
    const trimmed = question.trim()
    if (!trimmed) return

    const newMessages = [...messages, { role: 'user', content: trimmed }]
    // Append user message and a loading assistant placeholder
    setMessages([...newMessages, { role: 'assistant', content: 'Enviando...' }])
    setQuestion('')

    try {
      const res = await fetch('/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: newMessages, conversation_id: conversationId }),
      })
      const data = await res.json()
      if (!data.ok) throw new Error(data.error || 'Erro desconhecido')

      const assistantContent = data.final_message
      setMessages(prev => [...prev.slice(0, -1), { role: 'assistant', content: assistantContent }])
      setConversationId(data.conversation_id)
    } catch (err) {
      setMessages(prev => [...prev.slice(0, -1), { role: 'assistant', content: 'Erro: ' + err.message }])
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

      <h1>Lingora</h1>

      {messages.length === 0 ? (
        <MessageInput
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onSend={runConversation}
          placeholder="Digite sua pergunta aqui..."
          buttonLabel="Iniciar conversa"
          className="centered"
          containerStyle={{ marginBottom: 16 }}
        />
      ) : null} 
      <h2>Chat 💬</h2>
      <div className="chat">
        {messages.length === 0 && <div className="empty">Nenhuma mensagem ainda. Envie algo para começar.</div>}
        {messages.map((m, i) => (
          <div key={i} className={`message ${m.role}`}>
            <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSanitize]}>
              {m.content}
            </ReactMarkdown>
          </div>
        ))}
        {conversationId && <div className='idConversation'>ID da conversa: {conversationId}</div>} 
        {messages.length > 0 && (
          <div>
            <MessageInput
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onSend={runConversation}
              placeholder="Digite sua próxima mensagem..."
              buttonLabel="Enviar"
              className="chat-input"
              containerStyle={{ marginTop: 0 }}
            />
          </div>
        )}
      </div>

      <p className="read-the-docs">Click on the Vite and React logos to learn more</p>
    </>
  )
}

export default App
