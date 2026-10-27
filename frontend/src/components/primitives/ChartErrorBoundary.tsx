import { Component, type ErrorInfo, type ReactNode } from 'react';
import { CHART_ERROR_COPY } from '../../lib/i18n-keys';

interface ChartErrorBoundaryProps {
  children: ReactNode;
  height?: number;
  fallbackMessage?: string;
}

interface ChartErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/**
 * Phase 15 — UI Resilience (CORR-10).
 * Per-chart-area class-component ErrorBoundary. Sized to match parent chart
 * container via `style={{ width: '100%', height }}`. Fallback is chart-scoped,
 * NOT full-page (D-15.06: distinct from the global ErrorBoundary which uses
 * full-viewport sizing for App-level catastrophic crashes).
 *
 * Anti-pattern guards (D-15.04):
 *   - NO auto-reload button — auto-reload masks repeat failures.
 *   - NO try/catch inside chart render functions (a sibling anti-pattern, see
 *     UI-SPEC AC #14). The boundary catches throws at the React tree boundary;
 *     internal try/catch would suppress the error from this boundary.
 *
 * Diagnostic logging: componentDidCatch logs to console.error with the
 * `[ChartErrorBoundary]` prefix so devtools surfaces the failure (logging is
 * additive — error is still caught and fallback renders).
 *
 * Usage (parent composition layer, D-15.02):
 *   <ChartErrorBoundary height={280}>
 *     <RevenueTrendChart data={trendData} />
 *   </ChartErrorBoundary>
 */
export class ChartErrorBoundary extends Component<
  ChartErrorBoundaryProps,
  ChartErrorBoundaryState
> {
  constructor(props: ChartErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ChartErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error('[ChartErrorBoundary]', error, info);
  }

  render(): ReactNode {
    if (this.state.hasError) {
      const height = this.props.height ?? 280;
      const message = this.props.fallbackMessage ?? CHART_ERROR_COPY.generic;
      return (
        <div
          style={{ width: '100%', height }}
          className="flex items-center justify-center rounded-md border border-gray-200 bg-gray-50"
        >
          <p className="text-sm text-gray-500">{message}</p>
        </div>
      );
    }
    return this.props.children;
  }
}
