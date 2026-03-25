import { useState } from 'react'
import ChatInterface from './components/ChatInterface'

function App() {
  const [eegFile, setEegFile] = useState<File | null>(null)

  return (
    <div className="min-h-screen bg-[#0f0f0f] text-white flex flex-col">
      <ChatInterface
        eegFile={eegFile}
        onFileSelect={setEegFile}
      />
    </div>
  )
}

export default App
