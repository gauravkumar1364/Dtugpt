import React from 'react';

/**
 * Component to render structured or plain text messages
 * Intelligently displays either:
 * - Structured response with sections, bullet points, etc.
 * - Plain text/markdown message
 */

/**
 * Clean markdown formatting from text (remove **, *, __, _)
 */
const cleanMarkdown = (text) => {
  if (!text) return text;
  // Remove bold **text**
  text = text.replace(/\*\*(.+?)\*\*/g, '$1');
  // Remove italic *text* and _text_
  text = text.replace(/\*(.+?)\*/g, '$1');
  text = text.replace(/_(.+?)_/g, '$1');
  // Remove __text__ formatting
  text = text.replace(/__(.+?)__/g, '$1');
  return text.trim();
};

function MessageDisplay({ message }) {
  // Check if message is a structured response object
  const isStructured = message?.title !== undefined && 
                       message?.sections !== undefined && 
                       typeof message === 'object' && 
                       !Array.isArray(message);

  if (isStructured) {
    return (
      <div className="structured-response space-y-3">
        {/* Title */}
        {message.title && (
          <h3 className="text-base font-semibold text-[#e5e5e5] mb-2">
            {cleanMarkdown(message.title)}
          </h3>
        )}

        {/* Summary */}
        {message.summary && (
          <p className="text-sm text-[#d0d0d0] leading-relaxed">
            {cleanMarkdown(message.summary)}
          </p>
        )}

        {/* Sections */}
        {message.sections && message.sections.length > 0 && (
          <div className="space-y-2">
            {message.sections.map((section, idx) => (
              <div key={idx} className="mb-3">
                {/* Section Header */}
                <h4 className="text-sm font-semibold text-[#f0f0f0] mb-1.5">
                  {cleanMarkdown(section.header)}
                </h4>

                {/* Section Content */}
                {section.content && (
                  <p className="text-xs text-[#c0c0c0] leading-relaxed mb-1.5">
                    {cleanMarkdown(section.content)}
                  </p>
                )}

                {/* Section Bullets */}
                {section.bullets && section.bullets.length > 0 && (
                  <ul className="space-y-1 ml-2">
                    {section.bullets.map((bullet, bIdx) => (
                      <li key={bIdx} className="text-xs text-[#d0d0d0] flex gap-2">
                        <span className="text-[#666666] flex-shrink-0">•</span>
                        <span>{cleanMarkdown(bullet)}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Key Points (if no sections or as additional info) */}
        {message.key_points && message.key_points.length > 0 && (
          <div>
            <h4 className="text-sm font-semibold text-[#f0f0f0] mb-1.5">
              Key Points
            </h4>
            <ul className="space-y-1 ml-2">
              {message.key_points.map((point, idx) => (
                <li key={idx} className="text-xs text-[#d0d0d0] flex gap-2">
                  <span className="text-[#666666] flex-shrink-0">•</span>
                  <span>{cleanMarkdown(point)}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
  }

  // Plain text / markdown display
  if (typeof message === 'string') {
    return (
      <div className="prose-sm text-[#e5e5e5]">
        {/* Simple line breaks and formatting */}
        {message.split('\n').map((line, idx) => {
          // Headers
          if (line.match(/^#{1,3}\s/)) {
            const level = line.match(/^(#{1,3})/)[1].length;
            const text = cleanMarkdown(line.replace(/^#{1,3}\s/, ''));
            const sizeClass = level === 1 ? 'text-base font-bold' : 
                             level === 2 ? 'text-sm font-semibold' : 
                             'text-xs font-semibold';
            return <p key={idx} className={`${sizeClass} text-[#f0f0f0] mt-2 mb-1`}>{text}</p>;
          }
          
          // Bullet points
          if (line.match(/^[-*•]\s/)) {
            const text = cleanMarkdown(line.replace(/^[-*•]\s/, ''));
            return (
              <div key={idx} className="text-xs text-[#d0d0d0] flex gap-2 ml-2">
                <span className="text-[#666666] flex-shrink-0">•</span>
                <span>{text}</span>
              </div>
            );
          }

          // Regular text
          if (line.trim()) {
            return <p key={idx} className="text-xs text-[#d0d0d0] leading-relaxed">{cleanMarkdown(line)}</p>;
          }

          // Empty lines
          return <div key={idx} className="h-1" />;
        })}
      </div>
    );
  }

  // Fallback for unexpected types
  return <p className="text-xs text-[#d0d0d0]">{JSON.stringify(message)}</p>;
}

export default MessageDisplay;
