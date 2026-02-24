import { Component, type ErrorInfo, type ReactNode } from 'react';
import { ChunkLoadError } from './ChunkLoadError';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

/** 청크 로드 실패 등 런타임 오류 시 폴백 UI 표시 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary:', error, errorInfo);
  }

  isChunkLoadError(error: Error | null): boolean {
    if (!error) return false;
    const msg = error.message || '';
    return (
      msg.includes('Failed to fetch dynamically imported module') ||
      msg.includes('Loading chunk') ||
      msg.includes('ChunkLoadError') ||
      msg.includes('text/html')
    );
  }

  render() {
    if (this.state.hasError && this.state.error) {
      if (this.isChunkLoadError(this.state.error)) {
        return <ChunkLoadError error={this.state.error} onRetry={() => window.location.reload()} />;
      }
      return (
        <div className="min-h-[50vh] flex flex-col items-center justify-center gap-4 p-6 bg-slate-950 text-slate-200">
          <p className="text-lg font-medium text-slate-300">오류가 발생했습니다.</p>
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-medium"
          >
            새로고침
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
