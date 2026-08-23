import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

/**
 * Beautiful markdown renderer — Notion/Odysseus style.
 * Tables with borders, styled headers, code blocks, lists.
 */
export default function MarkdownRenderer({ content }: { content: string }) {
  return (
    <div className="kaihara-md text-sm leading-relaxed">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          // Tables — bordered, striped, scrollable
          table: ({ children }) => (
            <div className="my-3 overflow-x-auto rounded-lg border border-kaihara-border">
              <table className="w-full border-collapse text-xs">{children}</table>
            </div>
          ),
          thead: ({ children }) => (
            <thead className="bg-kaihara-primary/15">{children}</thead>
          ),
          th: ({ children }) => (
            <th className="border-b border-kaihara-border px-3 py-2 text-left font-bold whitespace-nowrap">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="border-b border-kaihara-border/50 px-3 py-1.5 align-top">
              {children}
            </td>
          ),
          tr: ({ children }) => (
            <tr className="hover:bg-kaihara-border/20 transition-colors">{children}</tr>
          ),
          // Headers
          h1: ({ children }) => (
            <h1 className="text-base font-bold mt-4 mb-2 pb-1 border-b border-kaihara-accent/40 flex items-center gap-2">
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-sm font-bold mt-3.5 mb-2 text-kaihara-accent flex items-center gap-1.5">
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-sm font-semibold mt-3 mb-1.5">{children}</h3>
          ),
          // Paragraph
          p: ({ children }) => <p className="mb-2.5 last:mb-0">{children}</p>,
          // Lists
          ul: ({ children }) => (
            <ul className="mb-2.5 ml-1 space-y-1">{children}</ul>
          ),
          ol: ({ children }) => (
            <ol className="mb-2.5 ml-5 space-y-1 list-decimal marker:text-kaihara-accent">
              {children}
            </ol>
          ),
          li: ({ children }) => {
            return (
              <li className="flex items-start gap-2 list-none">
                <span className="text-kaihara-accent mt-0.5 select-none">▸</span>
                <span className="flex-1 min-w-0">{children}</span>
              </li>
            )
          },
          // Code
          code: ({ className, children }) => {
            const isBlock = /language-/.test(className || '')
            if (isBlock) {
              return (
                <code className={`${className} block font-mono`}>{children}</code>
              )
            }
            return (
              <code className="px-1.5 py-0.5 rounded bg-kaihara-border/40 font-mono text-[0.8em] text-kaihara-accent">
                {children}
              </code>
            )
          },
          pre: ({ children }) => (
            <pre className="my-2.5 p-3 rounded-lg bg-black/40 border border-kaihara-border overflow-x-auto text-xs font-mono">
              {children}
            </pre>
          ),
          // Blockquote
          blockquote: ({ children }) => (
            <blockquote className="my-2.5 pl-3 py-1.5 border-l-4 border-kaihara-warning bg-kaihara-warning/10 rounded-r text-kaihara-text/90">
              {children}
            </blockquote>
          ),
          // Horizontal rule
          hr: () => <hr className="my-3 border-kaihara-border" />,
          // Links
          a: ({ href, children }) => (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="text-kaihara-accent underline hover:opacity-80"
            >
              {children}
            </a>
          ),
          // Strong
          strong: ({ children }) => (
            <strong className="font-bold text-white">{children}</strong>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}
