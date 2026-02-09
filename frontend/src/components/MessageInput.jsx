export default function MessageInput({ value, onChange, onSend, placeholder = '', buttonLabel = 'Enviar', containerStyle = {}, className = '' }) {
  const classes = `message-input ${className}`.trim()
  return (
    <div className={classes} style={containerStyle}>
      <input
        className="input-field"
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        onKeyDown={(e) => { if (e.key === 'Enter') onSend() }}
      />
      <button className="send-button" onClick={onSend}>
        {buttonLabel}
      </button>
    </div>
  )
}
