import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface Props {
  children: string
  className?: string
}

function MarkdownContent({ children, className = '' }: Props) {
  return (
    <div className={`markdown-content ${className}`}>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>
        {children}
      </ReactMarkdown>
    </div>
  )
}

export default MarkdownContent
