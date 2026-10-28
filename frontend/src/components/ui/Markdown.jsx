import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { missionApi } from "../../missionApi";

// Resolve an image src from agent output to something the browser can load.
// The agent often emits a bare filename or a relative "/charts/x.png" path for
// a generated chart; rewrite those to the backend's served URL.
function resolveImgSrc(src) {
  if (!src) return src;
  if (/^(https?:|data:)/i.test(src)) return src;        // already absolute
  if (src.startsWith("/charts/")) return `${missionApi.base}${src}`;
  // bare chart filename (e.g. "abc123_0.png" or "charts/abc.png")
  const name = src.replace(/^\.?\/*/, "");
  if (/\.(png|jpe?g|svg)$/i.test(name)) {
    return `${missionApi.base}/charts/${name.replace(/^charts\//, "")}`;
  }
  return src;
}

// Renders AI output as proper Markdown: headings (sized by #/##/###), bold,
// italics, bullet + numbered lists, tables (GFM), code, blockquotes, links.
// Styled to match Orion's neumorphic ink palette. `compact` tightens spacing
// for inline result blocks.
export function Markdown({ children, compact = false }) {
  if (!children) return null;
  // The LLM sometimes emits literal <br> HTML. react-markdown doesn't render
  // raw HTML, so convert line-break tags to real newlines, and strip any other
  // stray simple HTML tags so nothing shows as raw text.
  const text = String(children)
    .replace(/<br\s*\/?>/gi, "\n")
    .replace(/<\/?(p|div|span)>/gi, "\n");
  return (
    <div className={`om-md text-[#334155] ${compact ? "om-md-compact" : ""}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ node, ...p }) => <h1 className="text-[18px] font-bold text-[#1e293b] mt-3 mb-1.5 first:mt-0" {...p} />,
          h2: ({ node, ...p }) => <h2 className="text-[16px] font-bold text-[#1e293b] mt-3 mb-1.5 first:mt-0" {...p} />,
          h3: ({ node, ...p }) => <h3 className="text-[14.5px] font-semibold text-[#334155] mt-2.5 mb-1 first:mt-0" {...p} />,
          h4: ({ node, ...p }) => <h4 className="text-[13.5px] font-semibold text-[#334155] mt-2 mb-1 first:mt-0" {...p} />,
          p: ({ node, ...p }) => <p className="text-[14px] leading-relaxed my-1.5 first:mt-0 last:mb-0" {...p} />,
          strong: ({ node, ...p }) => <strong className="font-semibold text-[#1e293b]" {...p} />,
          em: ({ node, ...p }) => <em className="italic" {...p} />,
          ul: ({ node, ...p }) => <ul className="list-disc pl-5 my-1.5 space-y-1 text-[14px] leading-relaxed marker:text-[#94a3b8]" {...p} />,
          ol: ({ node, ...p }) => <ol className="list-decimal pl-5 my-1.5 space-y-1 text-[14px] leading-relaxed marker:text-[#94a3b8]" {...p} />,
          li: ({ node, ...p }) => <li className="pl-0.5" {...p} />,
          a: ({ node, ...p }) => <a className="text-[#4f46e5] font-medium underline underline-offset-2 hover:text-[#4338ca]" target="_blank" rel="noreferrer" {...p} />,
          img: ({ node, src, alt, ...p }) => {
            const resolved = resolveImgSrc(src);
            return (
              <a href={resolved} target="_blank" rel="noreferrer" className="block my-2 neu-inset rounded-xl p-2 w-fit max-w-full">
                <img src={resolved} alt={alt || "chart"} loading="lazy"
                  className="max-w-[520px] w-full rounded-lg bg-white" {...p} />
              </a>
            );
          },
          blockquote: ({ node, ...p }) => <blockquote className="border-l-3 border-[#c7cede] pl-3 my-2 text-[#64748b] italic" {...p} />,
          hr: () => <hr className="my-3 border-[#e2e6ee]" />,
          code: ({ node, inline, className, children, ...p }) =>
            inline ? (
              <code className="bg-[#e9edf4] text-[#be185d] rounded px-1.5 py-0.5 text-[12.5px] font-mono" {...p}>{children}</code>
            ) : (
              <code className="block bg-[#1e293b] text-[#e2e8f0] rounded-lg p-3 my-2 text-[12.5px] font-mono overflow-x-auto whitespace-pre" {...p}>{children}</code>
            ),
          pre: ({ node, children }) => <pre className="my-2">{children}</pre>,
          table: ({ node, ...p }) => (
            <div className="my-2 overflow-x-auto">
              <table className="w-full text-[13px] border-collapse" {...p} />
            </div>
          ),
          thead: ({ node, ...p }) => <thead className="bg-[#eef1f6]" {...p} />,
          th: ({ node, ...p }) => <th className="border border-[#e2e6ee] px-3 py-2 text-left font-semibold text-[#334155]" {...p} />,
          td: ({ node, ...p }) => <td className="border border-[#e2e6ee] px-3 py-2 text-[#4a5568] align-top" {...p} />,
        }}
      >
        {text}
      </ReactMarkdown>
    </div>
  );
}
