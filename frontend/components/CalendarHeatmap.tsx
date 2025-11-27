'use client';

import { useMemo, useState, useCallback, useRef } from 'react';

interface DayData {
  date: string;
  count: number;
  accuracy?: number;
}

interface CalendarHeatmapProps {
  data: DayData[];
  startDate?: Date;
  endDate?: Date;
  colorScheme?: 'green' | 'blue' | 'purple';
  showMonthLabels?: boolean;
  showWeekdayLabels?: boolean;
  onClick?: (date: string, data: DayData | null) => void;
}

const DAYS_OF_WEEK = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

export default function CalendarHeatmap({
  data,
  startDate,
  endDate,
  colorScheme = 'green',
  showMonthLabels = true,
  showWeekdayLabels = true,
  onClick,
}: CalendarHeatmapProps) {
  const [focusedDate, setFocusedDate] = useState<string | null>(null);
  const gridRef = useRef<HTMLDivElement>(null);

  // Color schemes
  const colorSchemes = {
    green: {
      empty: 'bg-gray-800',
      level1: 'bg-emerald-900',
      level2: 'bg-emerald-700',
      level3: 'bg-emerald-500',
      level4: 'bg-emerald-400',
    },
    blue: {
      empty: 'bg-gray-800',
      level1: 'bg-blue-900',
      level2: 'bg-blue-700',
      level3: 'bg-blue-500',
      level4: 'bg-blue-400',
    },
    purple: {
      empty: 'bg-gray-800',
      level1: 'bg-purple-900',
      level2: 'bg-purple-700',
      level3: 'bg-purple-500',
      level4: 'bg-purple-400',
    },
  };

  const colors = colorSchemes[colorScheme];

  // Calculate date range (default: last 365 days)
  const { start, end } = useMemo(() => {
    const e = endDate || new Date();
    const s = startDate || new Date(e.getTime() - 365 * 24 * 60 * 60 * 1000);
    return { start: s, end: e };
  }, [startDate, endDate]);

  // Build data map for quick lookup
  const dataMap = useMemo(() => {
    const map = new Map<string, DayData>();
    data.forEach((d) => {
      map.set(d.date, d);
    });
    return map;
  }, [data]);

  // Calculate max count for color intensity
  const maxCount = useMemo(() => {
    if (data.length === 0) return 10;
    return Math.max(...data.map((d) => d.count), 1);
  }, [data]);

  // Get color class based on count (memoized to prevent recreation)
  const getColorClass = useCallback((count: number): string => {
    if (count === 0) return colors.empty;
    const intensity = count / maxCount;
    if (intensity <= 0.25) return colors.level1;
    if (intensity <= 0.5) return colors.level2;
    if (intensity <= 0.75) return colors.level3;
    return colors.level4;
  }, [colors, maxCount]);

  // Generate calendar grid
  const { weeks, monthLabels } = useMemo(() => {
    const weeks: { date: Date; data: DayData | null }[][] = [];
    const monthLabels: { month: string; weekIndex: number }[] = [];

    // Start from the beginning of the week containing start date
    const current = new Date(start);
    current.setDate(current.getDate() - current.getDay());

    let currentWeek: { date: Date; data: DayData | null }[] = [];
    let lastMonth = -1;

    while (current <= end) {
      const dateStr = current.toISOString().split('T')[0];
      const dayData = dataMap.get(dateStr) || null;

      // Track month changes for labels
      if (current.getMonth() !== lastMonth && current >= start) {
        monthLabels.push({
          month: MONTHS[current.getMonth()],
          weekIndex: weeks.length,
        });
        lastMonth = current.getMonth();
      }

      currentWeek.push({
        date: new Date(current),
        data: dayData,
      });

      // Move to next day
      current.setDate(current.getDate() + 1);

      // Start new week on Sunday
      if (current.getDay() === 0) {
        weeks.push(currentWeek);
        currentWeek = [];
      }
    }

    // Add remaining days
    if (currentWeek.length > 0) {
      weeks.push(currentWeek);
    }

    return { weeks, monthLabels };
  }, [start, end, dataMap]);

  // Format tooltip content (memoized to prevent recreation)
  const formatTooltip = useCallback((date: Date, data: DayData | null): string => {
    const dateStr = date.toLocaleDateString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });

    if (!data || data.count === 0) {
      return `${dateStr}\nNo activity`;
    }

    let tooltip = `${dateStr}\n${data.count} question${data.count !== 1 ? 's' : ''}`;
    if (data.accuracy !== undefined) {
      tooltip += `\n${Math.round(data.accuracy)}% accuracy`;
    }
    return tooltip;
  }, []);

  // Get accessible label for a day cell (memoized to prevent recreation)
  const getAccessibleLabel = useCallback((date: Date, dayData: DayData | null): string => {
    const dateStr = date.toLocaleDateString('en-US', {
      weekday: 'long',
      month: 'long',
      day: 'numeric',
      year: 'numeric',
    });

    if (!dayData || dayData.count === 0) {
      return `${dateStr}, No activity`;
    }

    let label = `${dateStr}, ${dayData.count} question${dayData.count !== 1 ? 's' : ''} answered`;
    if (dayData.accuracy !== undefined) {
      label += `, ${Math.round(dayData.accuracy)}% accuracy`;
    }
    return label;
  }, []);

  // Handle keyboard navigation
  const handleKeyDown = useCallback((e: React.KeyboardEvent, weekIndex: number, dayIndex: number, dateStr: string) => {
    const totalWeeks = weeks.length;
    let newWeekIndex = weekIndex;
    let newDayIndex = dayIndex;

    switch (e.key) {
      case 'ArrowRight':
        e.preventDefault();
        newWeekIndex = weekIndex + 1;
        if (newWeekIndex >= totalWeeks) {
          newWeekIndex = 0;
        }
        break;
      case 'ArrowLeft':
        e.preventDefault();
        newWeekIndex = weekIndex - 1;
        if (newWeekIndex < 0) {
          newWeekIndex = totalWeeks - 1;
        }
        break;
      case 'ArrowDown':
        e.preventDefault();
        newDayIndex = dayIndex + 1;
        if (newDayIndex >= 7) {
          newDayIndex = 0;
          newWeekIndex = weekIndex + 1;
          if (newWeekIndex >= totalWeeks) {
            newWeekIndex = 0;
          }
        }
        break;
      case 'ArrowUp':
        e.preventDefault();
        newDayIndex = dayIndex - 1;
        if (newDayIndex < 0) {
          newDayIndex = 6;
          newWeekIndex = weekIndex - 1;
          if (newWeekIndex < 0) {
            newWeekIndex = totalWeeks - 1;
          }
        }
        break;
      case 'Enter':
      case ' ':
        e.preventDefault();
        const day = weeks[weekIndex]?.[dayIndex];
        if (day && day.date >= start && day.date <= end) {
          onClick?.(dateStr, day.data);
        }
        return;
      case 'Home':
        e.preventDefault();
        newWeekIndex = 0;
        newDayIndex = 0;
        break;
      case 'End':
        e.preventDefault();
        newWeekIndex = totalWeeks - 1;
        newDayIndex = (weeks[totalWeeks - 1]?.length || 1) - 1;
        break;
      default:
        return;
    }

    // Find the new cell and focus it
    const newCell = gridRef.current?.querySelector(
      `[data-week="${newWeekIndex}"][data-day="${newDayIndex}"]`
    ) as HTMLElement;
    if (newCell) {
      newCell.focus();
      const newDateStr = newCell.getAttribute('data-date');
      if (newDateStr) {
        setFocusedDate(newDateStr);
      }
    }
  }, [weeks, start, end, onClick]);

  return (
    <div className="overflow-x-auto">
      <div className="inline-block min-w-max">
        {/* Month labels */}
        {showMonthLabels && (
          <div className="flex mb-2 ml-8">
            {monthLabels.map((label, i) => (
              <div
                key={i}
                className="text-xs text-gray-500"
                style={{
                  marginLeft: i === 0 ? 0 : `${(label.weekIndex - (monthLabels[i - 1]?.weekIndex || 0)) * 14 - 20}px`,
                }}
              >
                {label.month}
              </div>
            ))}
          </div>
        )}

        <div className="flex">
          {/* Weekday labels */}
          {showWeekdayLabels && (
            <div className="flex flex-col mr-2 justify-around">
              {[0, 1, 2, 3, 4, 5, 6].map((day) => (
                <div
                  key={day}
                  className="text-xs text-gray-500 h-3 flex items-center"
                  style={{ visibility: day % 2 === 1 ? 'visible' : 'hidden' }}
                >
                  {DAYS_OF_WEEK[day]}
                </div>
              ))}
            </div>
          )}

          {/* Calendar grid */}
          <div
            ref={gridRef}
            className="flex gap-1"
            role="grid"
            aria-label="Activity calendar"
          >
            {weeks.map((week, weekIndex) => (
              <div key={weekIndex} className="flex flex-col gap-1" role="row">
                {week.map((day, dayIndex) => {
                  const count = day.data?.count || 0;
                  const dateStr = day.date.toISOString().split('T')[0];
                  const isInRange = day.date >= start && day.date <= end;
                  const isFocused = focusedDate === dateStr;

                  return (
                    <div
                      key={dayIndex}
                      role="gridcell"
                      tabIndex={isInRange ? (isFocused || (!focusedDate && weekIndex === 0 && dayIndex === 0) ? 0 : -1) : -1}
                      data-week={weekIndex}
                      data-day={dayIndex}
                      data-date={dateStr}
                      className={`w-3 h-3 rounded-sm cursor-pointer transition-all hover:ring-1 hover:ring-white/30 focus:outline-none focus:ring-2 focus:ring-[#4169E1] focus:ring-offset-1 focus:ring-offset-gray-900 ${
                        isInRange ? getColorClass(count) : 'bg-transparent'
                      }`}
                      title={isInRange ? formatTooltip(day.date, day.data) : ''}
                      aria-label={isInRange ? getAccessibleLabel(day.date, day.data) : undefined}
                      onClick={() => isInRange && onClick?.(dateStr, day.data)}
                      onKeyDown={(e) => isInRange && handleKeyDown(e, weekIndex, dayIndex, dateStr)}
                      onFocus={() => setFocusedDate(dateStr)}
                    />
                  );
                })}
              </div>
            ))}
          </div>
        </div>

        {/* Legend */}
        <div className="flex items-center justify-end gap-2 mt-4 text-xs text-gray-500" aria-hidden="true">
          <span>Less</span>
          <div className={`w-3 h-3 rounded-sm ${colors.empty}`} />
          <div className={`w-3 h-3 rounded-sm ${colors.level1}`} />
          <div className={`w-3 h-3 rounded-sm ${colors.level2}`} />
          <div className={`w-3 h-3 rounded-sm ${colors.level3}`} />
          <div className={`w-3 h-3 rounded-sm ${colors.level4}`} />
          <span>More</span>
        </div>
        <p className="sr-only">
          Use arrow keys to navigate between days, Enter or Space to select a day.
        </p>
      </div>
    </div>
  );
}
