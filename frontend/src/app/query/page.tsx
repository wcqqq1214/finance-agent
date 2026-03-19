'use client';

import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

export default function QueryPage() {
  const [query, setQuery] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // TODO: Implement analysis request
    console.log('Analyzing:', query);
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Interactive Query</h1>
        <p className="text-muted-foreground mt-2">
          Enter a stock symbol to analyze with the multi-agent system
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Stock Analysis</CardTitle>
          <CardDescription>
            Enter a stock symbol (e.g., AAPL, TSLA, MSFT)
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="flex gap-2">
            <Input
              placeholder="Enter stock symbol..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="flex-1"
            />
            <Button type="submit">Analyze</Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Analysis Progress</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Analysis results will appear here with real-time progress updates
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
