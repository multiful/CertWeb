export function CertLogo({ className = "w-8 h-8" }: { className?: string }) {
    return (
        <svg
            viewBox="0 0 100 100"
            className={className}
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
        >
            <defs>
                <linearGradient id="certFinderVibrantGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#3b82f6" />
                    <stop offset="50%" stopColor="#6366f1" />
                    <stop offset="100%" stopColor="#8b5cf6" />
                </linearGradient>
            </defs>

            {/* Background Glow Sphere */}
            <circle cx="50" cy="50" r="42" fill="url(#certFinderVibrantGradient)" opacity="0.2" className="animate-pulse" />

            {/* Stylized Document / Certificate OUTLINE */}
            <rect x="28" y="20" width="44" height="60" rx="6" fill="none" stroke="#818cf8" strokeWidth="3.5" className="drop-shadow-lg" />

            {/* Horizontal Detail Lines inside the document */}
            <line x1="38" y1="35" x2="62" y2="35" stroke="#818cf8" strokeWidth="3" strokeLinecap="round" opacity="0.9" />
            <line x1="38" y1="45" x2="62" y2="45" stroke="#818cf8" strokeWidth="3" strokeLinecap="round" opacity="0.9" />
            <line x1="38" y1="55" x2="52" y2="55" stroke="#818cf8" strokeWidth="3" strokeLinecap="round" opacity="0.9" />

            {/* Central Success Mark (Checkmark) at bottom */}
            <path
                d="M40 64L46 70L60 54"
                stroke="#3b82f6"
                strokeWidth="4.5"
                strokeLinecap="round"
                strokeLinejoin="round"
            />

            {/* Modern Search Glass Overlay (Bottom Right) */}
            <g className="drop-shadow-xl">
                <circle cx="68" cy="68" r="14" fill="#0f172a" stroke="#e2e8f0" strokeWidth="4" />
                <circle cx="68" cy="68" r="7" fill="none" stroke="url(#certFinderVibrantGradient)" strokeWidth="3" />
                <line x1="78" y1="78" x2="88" y2="88" stroke="#e2e8f0" strokeWidth="5" strokeLinecap="round" />
            </g>
        </svg>
    );
}
