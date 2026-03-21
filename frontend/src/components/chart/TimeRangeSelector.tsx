'use client';

import { Button } from '@/components/ui/button';
import type { TimeRange } from '@/lib/types';

interface TimeRangeSelectorProps {
  value: TimeRange;
  onChange: (range: TimeRange) => void;
  disabled?: boolean;
}

const TIME_RANGES: TimeRange[] = ['D', 'W', 'M', 'Y'];

export function TimeRangeSelector({ value, onChange, disabled }: TimeRangeSelectorProps) {
  const labels: Record<TimeRange, string> = {
    'D': 'Day',
    'W': 'Week',
    'M': 'Month',
    'Y': 'Year',
    '15M': '15 Min',
    '1H': '1 Hour',
    '4H': '4 Hour',
    '1D': '1 Day',
    '1W': '1 Week',
    '1M': '1 Month',
    '1Y': '1 Year',
  };

  return (
    <div className="flex gap-1">
      {TIME_RANGES.map((range) => (
        <Button
          key={range}
          variant={value === range ? 'default' : 'outline'}
          size="sm"
          onClick={() => onChange(range)}
          disabled={disabled}
          className="min-w-[60px]"
        >
          {labels[range]}
        </Button>
      ))}
    </div>
  );
}
