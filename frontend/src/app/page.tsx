'use client';

import { useState } from 'react';
import { StockSelector } from '@/components/stock/StockSelector';
import { ChatPanel } from '@/components/chat/ChatPanel';

export default function Home() {
  const [selectedStock, setSelectedStock] = useState<string | null>(null);

  return (
    <div className="flex gap-4 h-[calc(100vh-8rem)]">
      {/* Left panel */}
      <div className="flex-1 flex flex-col gap-4 overflow-hidden">
        {/* Top: Stock selector (40% height) */}
        <div className="h-[40%] overflow-y-auto">
          <StockSelector
            selectedStock={selectedStock}
            onStockSelect={setSelectedStock}
          />
        </div>

        {/* Bottom: K-line chart placeholder (60% height) */}
        <div className="flex-1 border rounded-lg flex items-center justify-center text-muted-foreground text-sm">
          {selectedStock
            ? `${selectedStock} K-Line Chart (coming soon)`
            : 'Select a stock to view chart'}
        </div>
      </div>

      {/* Right panel: Chat */}
      <div className="w-[35%] border-l overflow-hidden flex flex-col">
        <ChatPanel selectedStock={selectedStock} />
      </div>
    </div>
  );
}
