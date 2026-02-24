import { useEffect } from 'react';

interface ChunkLoadErrorProps {
  error?: unknown;
  onRetry?: () => void;
}

/** 동적 import(청크) 로드 실패 시 표시. 배포 후 캐시된 HTML이 예전 청크를 요청할 때 발생. */
export function ChunkLoadError({ onRetry }: ChunkLoadErrorProps) {
  useEffect(() => {
    console.error('Chunk load failed. Try hard refresh (Ctrl+Shift+R) or clear cache.');
  }, []);

  const handleRetry = () => {
    if (onRetry) onRetry();
    else window.location.reload();
  };

  return (
    <div className="min-h-[50vh] flex flex-col items-center justify-center gap-4 p-6 bg-slate-950 text-slate-200">
      <p className="text-lg font-medium text-slate-300">페이지를 불러오지 못했습니다.</p>
      <p className="text-sm text-slate-500 text-center max-w-md">
        배포 업데이트 후 발생할 수 있습니다. 새로고침 후 다시 시도해 주세요.
      </p>
      <button
        type="button"
        onClick={handleRetry}
        className="px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-medium transition-colors"
      >
        새로고침
      </button>
    </div>
  );
}
