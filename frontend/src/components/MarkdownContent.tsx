import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface MarkdownContentProps {
  content: string
  className?: string
}

export default function MarkdownContent({ content, className = '' }: MarkdownContentProps) {
  return (
    <div className={`markdown-content ${className}`}>
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        h1: ({ children }) => (
          <h1 className="font-heading font-bold text-lg mt-3 mb-1.5 first:mt-0">{children}</h1>
        ),
        h2: ({ children }) => (
          <h2 className="font-heading font-bold text-base mt-3 mb-1 first:mt-0">{children}</h2>
        ),
        h3: ({ children }) => (
          <h3 className="font-heading font-semibold text-sm mt-2 mb-1 first:mt-0">{children}</h3>
        ),
        p: ({ children }) => (
          <p className="mb-2 last:mb-0 leading-relaxed">{children}</p>
        ),
        ul: ({ children }) => (
          <ul className="mb-2 last:mb-0 space-y-1 pl-4 list-disc marker:text-primary">{children}</ul>
        ),
        ol: ({ children }) => (
          <ol className="mb-2 last:mb-0 space-y-1 pl-4 list-decimal marker:text-primary">{children}</ol>
        ),
        li: ({ children }) => (
          <li className="leading-relaxed">{children}</li>
        ),
        strong: ({ children }) => (
          <strong className="font-semibold text-text">{children}</strong>
        ),
        em: ({ children }) => (
          <em className="italic">{children}</em>
        ),
        code: ({ children, className: codeClass }) => {
          const isBlock = codeClass?.includes('language-')
          if (isBlock) {
            return (
              <code className={`block bg-surface-dark rounded-lg p-3 my-2 text-xs font-mono overflow-x-auto ${codeClass || ''}`}>
                {children}
              </code>
            )
          }
          return (
            <code className="bg-surface-dark text-primary-dark px-1.5 py-0.5 rounded text-xs font-mono">
              {children}
            </code>
          )
        },
        pre: ({ children }) => (
          <pre className="mb-2 last:mb-0">{children}</pre>
        ),
        blockquote: ({ children }) => (
          <blockquote className="border-l-4 border-primary pl-3 my-2 text-text-muted italic">
            {children}
          </blockquote>
        ),
        table: ({ children }) => (
          <div className="overflow-x-auto my-2">
            <table className="w-full text-xs border-collapse">{children}</table>
          </div>
        ),
        th: ({ children }) => (
          <th className="text-left font-semibold border-b border-surface-dark px-2 py-1.5 bg-surface">{children}</th>
        ),
        td: ({ children }) => (
          <td className="border-b border-surface-dark px-2 py-1.5">{children}</td>
        ),
        hr: () => <hr className="my-3 border-surface-dark" />,
        a: ({ href, children }) => {
          const safeHref = href && /^https?:\/\//i.test(href) ? href : undefined
          return (
            <a href={safeHref} className="text-primary underline underline-offset-2" target="_blank" rel="noopener noreferrer nofollow">
              {children}
            </a>
          )
        },
      }}
    >
      {content}
    </ReactMarkdown>
    </div>
  )
}
