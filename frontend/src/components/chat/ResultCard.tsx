'use client';

import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface ResultCardProps {
  symbol: string;
  query: string;
  progress: string[];
  result: Record<string, unknown> | null;
  isAnalyzing: boolean;
}

function CollapsibleSection({
  title,
  children,
  defaultOpen = false,
}: {
  title: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border rounded-md overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-3 py-2 text-sm font-medium bg-muted/50 hover:bg-muted transition-colors"
      >
        {title}
        {open ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
      </button>
      {open && <div className="px-3 py-2 text-sm">{children}</div>}
    </div>
  );
}

export function ResultCard({ symbol, query, progress, result, isAnalyzing }: ResultCardProps) {
  return (
    <Card className="flex-1 overflow-hidden flex flex-col">
      <CardHeader className="pb-2">
        <div className="flex items-center gap-2">
          <CardTitle className="text-base">{symbol}</CardTitle>
          {isAnalyzing && (
            <Badge variant="secondary" className="text-xs animate-pulse">
              Analyzing...
            </Badge>
          )}
        </div>
        <p className="text-xs text-muted-foreground truncate">{query}</p>
      </CardHeader>
      <CardContent className="flex-1 overflow-y-auto space-y-2">
        {/* Progress */}
        {progress.length > 0 && (
          <div className="space-y-1">
            {progress.map((msg, i) => (
              <p key={i} className="text-xs text-muted-foreground flex items-start gap-1">
                <span className="text-primary mt-0.5">•</span>
                {msg}
              </p>
            ))}
          </div>
        )}

        {/* Structured result */}
        {result && (
          <div className="space-y-2 pt-1">
            {result.quant_analysis && (
              <CollapsibleSection title="Technical Analysis" defaultOpen>
                <pre className="text-xs whitespace-pre-wrap break-words">
                  {JSON.stringify(result.quant_analysis, null, 2)}
                </pre>
              </CollapsibleSection>
            )}
            {result.news_sentiment && (
              <CollapsibleSection title="News Summary">
                <pre className="text-xs whitespace-pre-wrap break-words">
                  {JSON.stringify(result.news_sentiment, null, 2)}
                </pre>
              </CollapsibleSection>
            )}
            {result.social_sentiment && (
              <CollapsibleSection title="Social Sentiment">
                <pre className="text-xs whitespace-pre-wrap break-words">
                  {JSON.stringify(result.social_sentiment, null, 2)}
                </pre>
              </CollapsibleSection>
            )}
            {result.final_decision && (
              <CollapsibleSection title="Recommendation" defaultOpen>
                <p className="text-sm">{String(result.final_decision)}</p>
              </CollapsibleSection>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
